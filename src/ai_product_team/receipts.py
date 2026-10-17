"""Command execution with receipts, and target snapshots.

Single responsibility: run a command under the controller's observation and record *what actually
happened* as an execution receipt (``docs/architecture/controller-contracts.md`` section 9, architecture
sections 5.6, 11.4 and 11.5). This module is the only producer of execution evidence in the package. A
receipt proves exactly one thing, that the recorded command ran in the recorded working directory against
the recorded snapshot and ended with the recorded exit status; the payload says so with
``"proves": "command_exit_status_only"``. Whether the command was the right one, whether the tests it ran
cover anything, or whether a passing exit means a requirement is met is never decided here.

Two public operations:

* :func:`snapshot` describes the target under test either as a git commit plus a hash of the dirty tree
  (tracked changes and untracked files), or, outside git, as a content manifest hash of the given paths.
* :func:`run_command` runs ``argv`` with ``subprocess.run(shell=False, capture_output=True, timeout=...)``
  under an allow-listed environment, writes redacted stdout and stderr under the case store's
  ``receipts/`` directory, and persists the receipt through :meth:`CaseStore.put_receipt`.

Outcomes are kept distinct and none of them is an exception: a nonzero exit is a recorded result; a
timeout is ``timed_out=True`` with ``exit_status=None``; a ``KeyboardInterrupt`` while the child runs is
recorded as ``cancelled=True`` (the receipt is persisted, then the interrupt propagates). Only a process
that cannot be started at all raises :class:`~ai_product_team.errors.ExecutionError`.

Redaction uses the enabled patterns of ``policies/data-handling.json`` plus any caller-supplied regular
expressions. The number of substitutions made across both logs is stored as ``redactions_applied``.
Redaction catches common secret shapes, not every secret; it is a mitigation, not a guarantee.
"""

from __future__ import annotations

import dataclasses
import hashlib
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence

from ai_product_team.errors import ExecutionError, NotFoundError, ValidationError
from ai_product_team.ids import new_id, now, sha256_file, sha256_json
from ai_product_team.policies import Policies

__all__ = [
    "DEFAULT_ENV_ALLOWLIST",
    "OBSERVATION_SOURCE",
    "PROVES",
    "Receipt",
    "compile_redactions",
    "is_sha256",
    "redact_text",
    "run_command",
    "snapshot",
]

#: Repository root this source checkout lives in (``src/ai_product_team/receipts.py`` -> repo). Policies are
#: loaded from here when the caller does not pass a :class:`Policies` instance.
PACKAGE_ROOT: Path = Path(__file__).resolve().parents[2]

#: Environment variables passed to the child when the caller does not narrow or widen the list.
DEFAULT_ENV_ALLOWLIST: tuple[str, ...] = ("PATH", "HOME", "LANG", "LC_ALL", "PYTHONPATH")

#: Every receipt this module writes was observed by the controller itself.
OBSERVATION_SOURCE: str = "controller"

#: What a receipt proves. Nothing in this module can prove more.
PROVES: str = "command_exit_status_only"

#: Name used in the replacement marker for caller-supplied redaction patterns.
CUSTOM_REDACTION_NAME: str = "custom"

#: Directory names skipped while building a content manifest.
_MANIFEST_SKIP_DIRS: frozenset[str] = frozenset({".git"})

#: Upper bound for each ``git`` helper call during a snapshot.
_GIT_TIMEOUT_S: float = 60.0

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


# --------------------------------------------------------------------------------------------------
# Receipt record
# --------------------------------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class Receipt:
    """One execution receipt, exactly as validated by ``schemas/receipt.schema.json`` and stored.

    ``exit_status`` is ``None`` when the process did not end on its own (timeout or cancellation);
    ``timed_out`` and ``cancelled`` say which. ``stdout_path`` and ``stderr_path`` are relative to the case
    directory so an exported case keeps working. Supports ``receipt["field"]`` for dict-style access.
    """

    id: str
    task_id: str
    command: list[str]
    cwd: str
    snapshot: dict[str, Any]
    started_at: str
    ended_at: str | None
    exit_status: int | None
    timed_out: bool
    cancelled: bool
    stdout_path: str
    stderr_path: str
    observation_source: str
    test_ids: list[str]
    redactions_applied: int
    proves: str = PROVES
    input_hashes: dict[str, str] = dataclasses.field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return the receipt as the JSON object stored in the ``receipts`` table."""
        data = dataclasses.asdict(self)
        data["command"] = list(self.command)
        data["test_ids"] = list(self.test_ids)
        return data

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "Receipt":
        """Rebuild a receipt from a stored payload. Unknown keys raise :class:`ValidationError`."""
        if not isinstance(payload, Mapping):
            raise ValidationError("receipt payload must be a JSON object", errors=["/: not an object"])
        names = {f.name for f in dataclasses.fields(cls)}
        unknown = sorted(set(payload) - names)
        if unknown:
            raise ValidationError(
                f"receipt payload has unknown keys: {unknown}", errors=[f"/{k}: unknown key" for k in unknown]
            )
        missing = sorted(name for name in names - {"proves", "input_hashes"} if name not in payload)
        if missing:
            raise ValidationError(
                f"receipt payload is missing keys: {missing}", errors=[f"/{k}: missing" for k in missing]
            )
        data = dict(payload)
        command = data["command"]
        data["command"] = list(command) if isinstance(command, (list, tuple)) else [str(command)]
        data["test_ids"] = list(data.get("test_ids") or [])
        data["input_hashes"] = dict(data.get("input_hashes") or {})
        data.setdefault("proves", PROVES)
        return cls(**data)

    def __getitem__(self, key: str) -> Any:
        return self.to_dict()[key]

    @property
    def ok(self) -> bool:
        """True only for a clean exit: status 0, not timed out, not cancelled. Says nothing about coverage."""
        return self.exit_status == 0 and not self.timed_out and not self.cancelled


# --------------------------------------------------------------------------------------------------
# Snapshots
# --------------------------------------------------------------------------------------------------


def snapshot(root: Path, paths: list[Path] | None = None) -> dict[str, Any]:
    """Describe the content of ``root`` (or of ``paths`` under it) as a receipt ``snapshot`` object.

    Inside a git work tree with at least one commit the result is
    ``{"kind": "git", "commit", "dirty_diff_sha256", "paths"}`` where ``commit`` is ``HEAD`` and
    ``dirty_diff_sha256`` hashes ``git diff HEAD --binary`` for the paths plus the content hashes of
    untracked, non-ignored files; it is ``None`` when the tree is clean. Anywhere else (no ``git``
    executable, not a repository, unborn branch, or a git failure) the result is
    ``{"kind": "manifest", "manifest_sha256", "paths"}``: a hash over ``<relative path>\\t<sha256>`` lines
    of every regular file under the paths, walked in sorted order and skipping ``.git`` directories.

    ``paths`` are files or directories, absolute or relative to ``root``; ``None`` means the whole root
    and is recorded as ``["."]``. A path outside ``root`` raises :class:`ValidationError`; a missing root
    (or, for a manifest, a missing path) raises :class:`NotFoundError`. Nothing here judges whether the
    snapshot covers what a test needed; it only records what was there.
    """
    root = Path(root)
    if not root.is_dir():
        raise NotFoundError(f"snapshot root is not a directory: {root}", details={"root": str(root)})
    root_resolved = root.resolve()
    rel_paths = _normalise_paths(root_resolved, paths)

    git_result = _git_snapshot(root_resolved, rel_paths)
    if git_result is not None:
        return git_result
    return {
        "kind": "manifest",
        "manifest_sha256": _manifest_sha256(root_resolved, rel_paths),
        "paths": list(rel_paths),
    }


def _normalise_paths(root: Path, paths: Sequence[Path | str] | None) -> list[str]:
    """Return POSIX paths relative to ``root`` (``["."]`` for the whole root), refusing escapes."""
    if paths is None:
        return ["."]
    if isinstance(paths, (str, bytes, os.PathLike)):
        raise ValidationError("snapshot paths must be a list of paths", errors=["/paths: not a list"])
    out: list[str] = []
    for index, item in enumerate(paths):
        if not isinstance(item, (str, os.PathLike)):
            raise ValidationError(
                f"snapshot path {index} is not a path", errors=[f"/paths/{index}: not a string or PathLike"]
            )
        candidate = Path(item)
        if not candidate.is_absolute():
            candidate = root / candidate
        # resolve() is non-strict, so a missing leaf still yields a clean relative path; escapes are refused.
        try:
            relative = candidate.resolve().relative_to(root)
        except ValueError as exc:
            raise ValidationError(
                f"snapshot path escapes root: {item}",
                errors=[f"/paths/{index}: outside snapshot root"],
                details={"root": str(root), "path": str(item)},
            ) from exc
        text = relative.as_posix()
        out.append(text if text else ".")
    if not out:
        return ["."]
    return sorted(dict.fromkeys(out))


def _git_env() -> dict[str, str]:
    env = dict(os.environ)
    # Never write the index while merely observing; never prompt or page.
    env["GIT_OPTIONAL_LOCKS"] = "0"
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_PAGER"] = "cat"
    env["PAGER"] = "cat"
    return env


def _git(root: Path, git: str, *args: str) -> bytes | None:
    """Run one git command; ``None`` on any failure (nonzero, timeout, cannot start)."""
    try:
        proc = subprocess.run(
            [git, "-C", str(root), *args],
            shell=False,
            capture_output=True,
            timeout=_GIT_TIMEOUT_S,
            env=_git_env(),
            check=False,
        )
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout


def _git_snapshot(root: Path, rel_paths: list[str]) -> dict[str, Any] | None:
    """Git snapshot of ``root`` or ``None`` when git cannot describe it."""
    git = shutil.which("git")
    if git is None:
        return None
    if _git(root, git, "rev-parse", "--is-inside-work-tree") is None:
        return None
    head = _git(root, git, "rev-parse", "--verify", "--quiet", "HEAD")
    if head is None:
        return None
    commit = head.decode("ascii", "replace").strip()
    if not re.fullmatch(r"[0-9a-f]{40,64}", commit):
        return None

    diff = _git(root, git, "diff", "HEAD", "--binary", "--no-color", "--no-ext-diff", "--", *rel_paths)
    if diff is None:
        return None
    untracked = _git(root, git, "ls-files", "--others", "--exclude-standard", "-z", "--", *rel_paths)
    if untracked is None:
        return None

    hasher = hashlib.sha256()
    dirty = bool(diff)
    hasher.update(diff)
    for raw in sorted(entry for entry in untracked.split(b"\0") if entry):
        file_path = root / os.fsdecode(raw)
        if not file_path.is_file():
            continue
        dirty = True
        hasher.update(b"untracked\t" + raw + b"\t" + sha256_file(file_path).encode("ascii") + b"\n")
    return {
        "kind": "git",
        "commit": commit,
        "dirty_diff_sha256": hasher.hexdigest() if dirty else None,
        "paths": list(rel_paths),
    }


def _manifest_sha256(root: Path, rel_paths: list[str]) -> str:
    """Hash ``<relpath>\\t<sha256>\\n`` lines for every regular file under the paths, in sorted order."""
    files: set[Path] = set()
    for rel in rel_paths:
        target = root if rel == "." else root / rel
        if target.is_file():
            files.add(target)
            continue
        if not target.is_dir():
            raise NotFoundError(
                f"snapshot path does not exist: {rel}", details={"root": str(root), "path": rel}
            )
        for dirpath, dirnames, filenames in os.walk(target):
            dirnames[:] = sorted(d for d in dirnames if d not in _MANIFEST_SKIP_DIRS)
            base = Path(dirpath)
            for name in filenames:
                candidate = base / name
                if candidate.is_file():
                    files.add(candidate)
    hasher = hashlib.sha256()
    for file_path in sorted(files, key=lambda p: p.relative_to(root).as_posix()):
        rel = file_path.relative_to(root).as_posix()
        hasher.update(f"{rel}\t{sha256_file(file_path)}\n".encode("utf-8", "surrogateescape"))
    return hasher.hexdigest()


# --------------------------------------------------------------------------------------------------
# Redaction
# --------------------------------------------------------------------------------------------------


def compile_redactions(
    policies: Policies | None, extra: Sequence[str] = ()
) -> list[tuple[re.Pattern[str], str]]:
    """Return ``(pattern, replacement)`` pairs: the enabled policy rules first, then ``extra`` regexes.

    The replacement is the policy template (``[REDACTED:<name>]`` by default) with ``<name>`` set to the
    rule name, or to ``custom`` for caller-supplied patterns. A pattern that does not compile raises
    :class:`ValidationError`.
    """
    template = policies.redaction_replacement() if policies is not None else "[REDACTED:<name>]"
    rules: list[tuple[str, str]] = []
    if policies is not None:
        for rule in policies.redaction_rules():
            rules.append((str(rule.get("name") or CUSTOM_REDACTION_NAME), str(rule["pattern"])))
    if isinstance(extra, (str, bytes)):
        raise ValidationError("redact must be a list of regex strings", errors=["/redact: not a list"])
    for index, pattern in enumerate(extra):
        if not isinstance(pattern, str) or not pattern:
            raise ValidationError(
                f"redact pattern {index} is not a non-empty string", errors=[f"/redact/{index}: not a string"]
            )
        rules.append((CUSTOM_REDACTION_NAME, pattern))
    compiled: list[tuple[re.Pattern[str], str]] = []
    for name, pattern in rules:
        try:
            regex = re.compile(pattern)
        except re.error as exc:
            raise ValidationError(
                f"redaction pattern {name!r} does not compile: {exc}",
                errors=[f"/redaction/{name}: invalid regex"],
                details={"name": name, "pattern": pattern},
            ) from exc
        compiled.append((regex, template.replace("<name>", name)))
    return compiled


def redact_text(text: str, redactions: Sequence[tuple[re.Pattern[str], str]]) -> tuple[str, int]:
    """Apply every ``(pattern, replacement)`` in order; return the redacted text and the substitution count."""
    total = 0
    for regex, replacement in redactions:
        text, count = regex.subn(lambda _m, r=replacement: r, text)
        total += count
    return text, total


def _redact_bytes(data: bytes, redactions: Sequence[tuple[re.Pattern[str], str]]) -> tuple[bytes, int]:
    """Redact raw log bytes, preserving undecodable bytes through ``surrogateescape``."""
    if not redactions or not data:
        return data, 0
    text = data.decode("utf-8", "surrogateescape")
    redacted, count = redact_text(text, redactions)
    if count == 0:
        return data, 0
    return redacted.encode("utf-8", "surrogateescape"), count


# --------------------------------------------------------------------------------------------------
# Command execution
# --------------------------------------------------------------------------------------------------


def run_command(
    store: Any,
    *,
    task_id: str,
    argv: list[str],
    cwd: Path,
    timeout_s: int,
    env_allowlist: Sequence[str] = DEFAULT_ENV_ALLOWLIST,
    test_ids: Sequence[str] = (),
    redact: Sequence[str] = (),
    policies: Policies | None = None,
) -> Receipt:
    """Run ``argv`` under controller observation and persist the receipt in ``store``.

    The child runs with ``subprocess.run(argv, shell=False, capture_output=True, timeout=timeout_s)`` in
    ``cwd`` with only the ``env_allowlist`` variables of the current environment. Its stdout and stderr,
    redacted with the enabled ``policies/data-handling.json`` patterns plus ``redact``, are written to
    ``<case_dir>/receipts/<receipt_id>.out`` and ``.err``; the receipt records those paths relative to the
    case directory, the :func:`snapshot` of ``cwd`` taken before the run, ``observation_source`` of
    ``controller`` and ``"proves": "command_exit_status_only"``.

    Results are never exceptions: a nonzero exit is recorded as ``exit_status``; expiry of ``timeout_s``
    gives ``timed_out=True`` with ``exit_status=None``; a ``KeyboardInterrupt`` while the child runs kills
    it, persists the receipt with ``cancelled=True`` and then re-raises the interrupt so the caller's
    flow stops too. :class:`ExecutionError` is raised only when the process cannot be started (missing
    executable, permission refused, missing ``cwd``), and then nothing is persisted. Bad arguments raise
    :class:`ValidationError`. ``policies`` defaults to the policy set of this source checkout.

    ``store`` is a :class:`~ai_product_team.storage.CaseStore` (anything exposing ``case_dir`` and
    ``put_receipt(payload) -> id``).
    """
    _check_str(task_id, "task_id")
    command = _check_argv(argv)
    timeout = _check_timeout(timeout_s)
    allowlist = _check_str_list(env_allowlist, "env_allowlist")
    tests = _check_str_list(test_ids, "test_ids")
    case_dir = getattr(store, "case_dir", None)
    if case_dir is None:
        raise ValidationError("store must expose case_dir", errors=["/store: no case_dir"])
    work_dir = Path(cwd)
    if not work_dir.is_dir():
        raise ExecutionError(
            f"working directory does not exist: {work_dir}",
            details={"reason": "cwd_missing", "cwd": str(work_dir), "argv": command},
        )

    if policies is None:
        policies = Policies.load(PACKAGE_ROOT)
    redactions = compile_redactions(policies, redact)
    env = {key: os.environ[key] for key in allowlist if key in os.environ}

    receipt_id = new_id("rcpt")
    receipts_dir = Path(case_dir) / "receipts"
    receipts_dir.mkdir(parents=True, exist_ok=True)
    stdout_rel = f"receipts/{receipt_id}.out"
    stderr_rel = f"receipts/{receipt_id}.err"
    target = snapshot(work_dir)

    started_at = now()
    exit_status: int | None
    timed_out = False
    cancelled = False
    interrupt: KeyboardInterrupt | None = None
    try:
        completed = subprocess.run(
            command,
            shell=False,
            capture_output=True,
            timeout=timeout,
            cwd=str(work_dir),
            env=env,
            check=False,
        )
        stdout, stderr, exit_status = completed.stdout, completed.stderr, completed.returncode
    except subprocess.TimeoutExpired as exc:
        stdout, stderr, exit_status, timed_out = exc.stdout or b"", exc.stderr or b"", None, True
    except KeyboardInterrupt as exc:
        # subprocess.run has already killed the child; record the cancellation before propagating.
        stdout, stderr, exit_status, cancelled, interrupt = b"", b"", None, True, exc
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        reason = "executable_not_found" if isinstance(exc, FileNotFoundError) else "cannot_start"
        if isinstance(exc, PermissionError):
            reason = "permission_denied"
        raise ExecutionError(
            f"command could not start: {exc}",
            details={"reason": reason, "argv": command, "cwd": str(work_dir), "error": str(exc)},
        ) from exc
    ended_at = now()

    stdout_bytes, out_count = _redact_bytes(stdout, redactions)
    stderr_bytes, err_count = _redact_bytes(stderr, redactions)
    _write_log(receipts_dir / f"{receipt_id}.out", stdout_bytes)
    _write_log(receipts_dir / f"{receipt_id}.err", stderr_bytes)

    receipt = Receipt(
        id=receipt_id,
        task_id=task_id,
        command=command,
        cwd=str(work_dir),
        snapshot=target,
        started_at=started_at,
        ended_at=ended_at,
        exit_status=exit_status,
        timed_out=timed_out,
        cancelled=cancelled,
        stdout_path=stdout_rel,
        stderr_path=stderr_rel,
        observation_source=OBSERVATION_SOURCE,
        test_ids=tests,
        redactions_applied=out_count + err_count,
        proves=PROVES,
        input_hashes={"argv": sha256_json(command), "env_keys": sha256_json(sorted(env))},
    )
    store.put_receipt(receipt.to_dict())
    if interrupt is not None:
        raise interrupt
    return receipt


# --------------------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------------------


def _check_str(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValidationError(f"{name} must be a non-empty string", errors=[f"/{name}: not a non-empty string"])
    return value


def _check_argv(argv: Any) -> list[str]:
    if isinstance(argv, (str, bytes)) or not isinstance(argv, Sequence):
        raise ValidationError("argv must be a list of strings", errors=["/argv: not a list"])
    command = list(argv)
    if not command:
        raise ValidationError("argv must not be empty", errors=["/argv: empty"])
    for index, item in enumerate(command):
        if not isinstance(item, str):
            raise ValidationError(f"argv[{index}] is not a string", errors=[f"/argv/{index}: not a string"])
    if not command[0]:
        raise ValidationError("argv[0] must name an executable", errors=["/argv/0: empty"])
    return command


def _check_timeout(timeout_s: Any) -> float:
    if isinstance(timeout_s, bool) or not isinstance(timeout_s, (int, float)) or not timeout_s > 0:
        raise ValidationError("timeout_s must be a positive number", errors=["/timeout_s: not a positive number"])
    return float(timeout_s)


def _check_str_list(values: Any, name: str) -> list[str]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise ValidationError(f"{name} must be a list of strings", errors=[f"/{name}: not a list"])
    out = list(values)
    for index, item in enumerate(out):
        if not isinstance(item, str):
            raise ValidationError(f"{name}[{index}] is not a string", errors=[f"/{name}/{index}: not a string"])
    return out


def _write_log(path: Path, data: bytes) -> None:
    """Write a log file atomically (temp file + ``os.replace``)."""
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with open(tmp, "wb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def is_sha256(value: Any) -> bool:
    """True when ``value`` is a 64-character lowercase hex digest (used by tests and reports)."""
    return isinstance(value, str) and bool(_SHA256_RE.match(value))
