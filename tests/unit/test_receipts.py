"""Unit tests for ai_product_team.receipts.

Covers: a real ``python3 -c`` command producing a schema-valid receipt stored in a real CaseStore with its
logs under ``receipts/``; a nonzero exit recorded as a result, not an exception; a timeout distinguished
from a failure (``timed_out=True``, ``exit_status=None``); a KeyboardInterrupt recorded as ``cancelled``
before it propagates; redaction from the shipped data-handling policy plus caller patterns, counted in
``redactions_applied``; the environment allow-list; git snapshots in a temporary repository and manifest
snapshots in a plain directory; ExecutionError only when the process cannot start; argument validation.
Every test works inside tempfile.TemporaryDirectory(); nothing writes into the repository tree.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ai_product_team import receipts as R
from ai_product_team import validation as V
from ai_product_team.errors import ExecutionError, NotFoundError, ValidationError
from ai_product_team.ids import parse_time
from ai_product_team.policies import Policies
from ai_product_team.registry import Registry
from ai_product_team.storage import CaseStore

REPO = Path(__file__).resolve().parents[2]
PYTHON = sys.executable
GIT = shutil.which("git")

# A token shaped like the policy's ``openai_style_key`` rule; never a real credential.
FAKE_SK_TOKEN = "sk-" + "a" * 24
# A token only the caller-supplied pattern knows about.
FAKE_CUSTOM_TOKEN = "FAKE_SECRET_12345"
CUSTOM_PATTERN = r"FAKE_SECRET_\d+"


def _git(repo: Path, home: Path, *args: str) -> str:
    """Run git in ``repo`` isolated from the developer's global configuration."""
    env = {
        **os.environ,
        "HOME": str(home),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": str(home / "no-such-gitconfig"),
        "GIT_AUTHOR_NAME": "test",
        "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_COMMITTER_NAME": "test",
        "GIT_COMMITTER_EMAIL": "test@example.com",
    }
    proc = subprocess.run([GIT or "git", *args], cwd=repo, env=env, capture_output=True, text=True, check=True)
    return proc.stdout.strip()


class ReceiptCase(unittest.TestCase):
    """Base: one temporary directory, one real CaseStore, the real Policies and Registry."""

    policies: Policies
    registry: Registry

    @classmethod
    def setUpClass(cls) -> None:
        cls.policies = Policies.load(REPO)
        cls.registry = Registry.load(REPO)

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.store = CaseStore.create(
            self.tmp / "case", {"objective": "Receipts test", "owner": "human-owner", "source_scope": []}
        )
        self.work = self.tmp / "work"
        self.work.mkdir()
        (self.work / "input.txt").write_text("fixture input\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.store.close()
        self._tmp.cleanup()

    def run_py(self, code: str, **kwargs):
        kwargs.setdefault("task_id", "task_demo")
        kwargs.setdefault("cwd", self.work)
        kwargs.setdefault("timeout_s", 30)
        kwargs.setdefault("policies", self.policies)
        return R.run_command(self.store, argv=[PYTHON, "-c", code], **kwargs)

    def log(self, receipt: R.Receipt, which: str) -> bytes:
        return (self.store.case_dir / getattr(receipt, f"{which}_path")).read_bytes()


# --------------------------------------------------------------------------------------------------
# run_command
# --------------------------------------------------------------------------------------------------


class RunCommandSuccess(ReceiptCase):
    def test_fixtures_are_the_real_ones(self):
        self.assertTrue(self.registry.agents, "registry loaded from the repository")
        self.assertTrue(self.registry.is_role(next(iter(self.registry.agents))))
        self.assertIn(r"\bsk-[A-Za-z0-9_-]{20,}\b", self.policies.redaction_patterns())
        self.assertEqual("[REDACTED:<name>]", self.policies.redaction_replacement())

    def test_real_command_receipt(self):
        receipt = self.run_py(
            "import sys; print('hello from child'); sys.stderr.write('warned\\n')", test_ids=["T-1", "T-2"]
        )
        self.assertIsInstance(receipt, R.Receipt)
        self.assertTrue(receipt.id.startswith("rcpt_"))
        self.assertEqual("task_demo", receipt.task_id)
        self.assertEqual([PYTHON, "-c", "import sys; print('hello from child'); sys.stderr.write('warned\\n')"], receipt.command)
        self.assertEqual(str(self.work), receipt.cwd)
        self.assertEqual(0, receipt.exit_status)
        self.assertFalse(receipt.timed_out)
        self.assertFalse(receipt.cancelled)
        self.assertTrue(receipt.ok)
        self.assertEqual("controller", receipt.observation_source)
        self.assertEqual("command_exit_status_only", receipt.proves)
        self.assertEqual(["T-1", "T-2"], receipt.test_ids)
        self.assertEqual(0, receipt.redactions_applied)
        self.assertLessEqual(parse_time(receipt.started_at), parse_time(receipt.ended_at))
        # Logs live under the store's receipts/ directory and are recorded relative to the case dir.
        self.assertEqual(f"receipts/{receipt.id}.out", receipt.stdout_path)
        self.assertEqual(f"receipts/{receipt.id}.err", receipt.stderr_path)
        self.assertEqual(b"hello from child\n", self.log(receipt, "stdout"))
        self.assertEqual(b"warned\n", self.log(receipt, "stderr"))
        self.assertEqual({f"{receipt.id}.out", f"{receipt.id}.err"}, {p.name for p in (self.store.case_dir / "receipts").iterdir()})
        # The snapshot was taken of cwd, a plain directory, so it is a manifest.
        self.assertEqual("manifest", receipt.snapshot["kind"])
        self.assertTrue(R.is_sha256(receipt.snapshot["manifest_sha256"]))
        self.assertEqual(["."], receipt.snapshot["paths"])
        self.assertTrue(R.is_sha256(receipt.input_hashes["argv"]))

    def test_receipt_is_schema_valid_and_persisted(self):
        receipt = self.run_py("pass")
        payload = receipt.to_dict()
        V.ensure_valid(payload, "receipt")
        self.assertEqual(payload, self.store.get_receipt(receipt.id))
        self.assertEqual([payload], self.store.receipts_for_task("task_demo"))
        row = self.store.get("receipts", receipt.id)
        self.assertEqual(0, row["exit_status"])
        self.assertEqual("controller", row["observation_source"])
        self.assertEqual(receipt, R.Receipt.from_dict(payload))
        self.assertEqual(receipt["exit_status"], 0)

    def test_two_runs_two_receipts(self):
        first = self.run_py("pass")
        second = self.run_py("pass")
        self.assertNotEqual(first.id, second.id)
        self.assertEqual([first.id, second.id], [r["id"] for r in self.store.receipts_for_task("task_demo")])


class RunCommandOutcomes(ReceiptCase):
    def test_nonzero_exit_is_a_result_not_an_exception(self):
        receipt = self.run_py("import sys; sys.stderr.write('boom'); sys.exit(3)")
        self.assertEqual(3, receipt.exit_status)
        self.assertFalse(receipt.timed_out)
        self.assertFalse(receipt.cancelled)
        self.assertFalse(receipt.ok)
        self.assertEqual(b"boom", self.log(receipt, "stderr"))
        self.assertEqual(3, self.store.get("receipts", receipt.id)["exit_status"])

    def test_timeout_is_distinguished_from_failure(self):
        receipt = self.run_py("import time; time.sleep(5)", timeout_s=1)
        self.assertTrue(receipt.timed_out)
        self.assertIsNone(receipt.exit_status)
        self.assertFalse(receipt.cancelled)
        self.assertIsNotNone(receipt.ended_at)
        self.assertFalse(receipt.ok)
        V.ensure_valid(receipt.to_dict(), "receipt")
        stored = self.store.get_receipt(receipt.id)
        self.assertTrue(stored["timed_out"])
        self.assertIsNone(stored["exit_status"])
        self.assertTrue((self.store.case_dir / receipt.stdout_path).is_file())
        self.assertTrue((self.store.case_dir / receipt.stderr_path).is_file())
        # Partial output captured before the kill is kept.
        partial = self.run_py("import sys, time; print('started', flush=True); time.sleep(5)", timeout_s=1)
        self.assertTrue(partial.timed_out)
        self.assertEqual(b"started\n", self.log(partial, "stdout"))

    def test_keyboard_interrupt_is_recorded_as_cancelled_then_propagates(self):
        real_run = subprocess.run

        def interrupted(args, *a, **kw):
            # Only the child command is interrupted; git probes inside snapshot() run for real.
            if args and args[0] == PYTHON:
                raise KeyboardInterrupt
            return real_run(args, *a, **kw)

        with mock.patch.object(R.subprocess, "run", side_effect=interrupted):
            with self.assertRaises(KeyboardInterrupt):
                self.run_py("pass")
        receipts = self.store.receipts_for_task("task_demo")
        self.assertEqual(1, len(receipts))
        receipt = R.Receipt.from_dict(receipts[0])
        self.assertTrue(receipt.cancelled)
        self.assertFalse(receipt.timed_out)
        self.assertIsNone(receipt.exit_status)
        self.assertIsNotNone(receipt.ended_at)
        self.assertTrue((self.store.case_dir / receipt.stdout_path).is_file())

    def test_execution_error_only_when_the_process_cannot_start(self):
        missing = str(self.tmp / "no-such-executable")
        with self.assertRaises(ExecutionError) as ctx:
            R.run_command(self.store, task_id="task_demo", argv=[missing], cwd=self.work, timeout_s=5, policies=self.policies)
        self.assertEqual("execution", ctx.exception.code)
        self.assertEqual("executable_not_found", ctx.exception.details["reason"])
        self.assertEqual([missing], ctx.exception.details["argv"])
        # Nothing was persisted and no log files were left behind.
        self.assertEqual([], self.store.receipts_for_task("task_demo"))
        self.assertEqual([], list((self.store.case_dir / "receipts").iterdir()))

    def test_missing_cwd_cannot_start(self):
        with self.assertRaises(ExecutionError) as ctx:
            R.run_command(self.store, task_id="task_demo", argv=[PYTHON, "-c", "pass"], cwd=self.tmp / "absent", timeout_s=5, policies=self.policies)
        self.assertEqual("cwd_missing", ctx.exception.details["reason"])
        self.assertEqual([], self.store.receipts_for_task("task_demo"))


class RunCommandRedaction(ReceiptCase):
    def test_policy_and_custom_patterns_are_applied_and_counted(self):
        # The secrets come from a file, not argv: the command line is evidence and is stored verbatim.
        (self.work / "secrets.txt").write_text(f"{FAKE_SK_TOKEN}\n{FAKE_CUSTOM_TOKEN}\n", encoding="utf-8")
        code = (
            "import sys; sk, custom = open('secrets.txt').read().split(); "
            "print(f'token {sk} end'); sys.stderr.write(f'err {custom} and again {custom}\\n')"
        )
        receipt = self.run_py(code, redact=[CUSTOM_PATTERN])
        self.assertEqual(0, receipt.exit_status)
        self.assertEqual(3, receipt.redactions_applied)
        out, err = self.log(receipt, "stdout"), self.log(receipt, "stderr")
        self.assertNotIn(FAKE_SK_TOKEN.encode(), out)
        self.assertNotIn(FAKE_CUSTOM_TOKEN.encode(), err)
        self.assertEqual(b"token [REDACTED:openai_style_key] end\n", out)
        self.assertEqual(b"err [REDACTED:custom] and again [REDACTED:custom]\n", err)
        # The count is persisted with the receipt and the stored payload never carries the token.
        stored = self.store.get_receipt(receipt.id)
        self.assertEqual(3, stored["redactions_applied"])
        self.assertNotIn(FAKE_SK_TOKEN, repr(stored))

    def test_policy_patterns_apply_without_custom_patterns(self):
        receipt = self.run_py("print('Authorization: Bearer abcdefghijklmnopqrstuvwxyz0123')")
        self.assertEqual(1, receipt.redactions_applied)
        self.assertIn(b"[REDACTED:", self.log(receipt, "stdout"))
        self.assertNotIn(b"abcdefghijklmnopqrstuvwxyz0123", self.log(receipt, "stdout"))

    def test_benign_output_is_untouched(self):
        receipt = self.run_py("print('3 passed in 0.01s'); print('sk-short')")
        self.assertEqual(0, receipt.redactions_applied)
        self.assertEqual(b"3 passed in 0.01s\nsk-short\n", self.log(receipt, "stdout"))

    def test_undecodable_bytes_survive_redaction(self):
        receipt = self.run_py(
            f"import sys; sys.stdout.buffer.write(b'\\xff\\xfe {FAKE_SK_TOKEN} \\x80')", redact=[]
        )
        self.assertEqual(1, receipt.redactions_applied)
        self.assertEqual(b"\xff\xfe [REDACTED:openai_style_key] \x80", self.log(receipt, "stdout"))

    def test_invalid_custom_pattern_is_refused(self):
        with self.assertRaises(ValidationError):
            self.run_py("pass", redact=["(unclosed"])
        with self.assertRaises(ValidationError):
            self.run_py("pass", redact="not-a-list")  # type: ignore[arg-type]
        self.assertEqual([], self.store.receipts_for_task("task_demo"))

    def test_redact_text_helper(self):
        rules = R.compile_redactions(self.policies, [CUSTOM_PATTERN])
        text, count = R.redact_text(f"a {FAKE_SK_TOKEN} b {FAKE_CUSTOM_TOKEN}", rules)
        self.assertEqual(2, count)
        self.assertEqual("a [REDACTED:openai_style_key] b [REDACTED:custom]", text)
        self.assertEqual(("clean", 0), R.redact_text("clean", rules))
        self.assertEqual(("x", 0), R.redact_text("x", []))


class RunCommandEnvironment(ReceiptCase):
    def test_only_allowlisted_variables_reach_the_child(self):
        probe = "import os; print(os.environ.get('AIPT_TEST_PROBE', 'absent')); print(sorted(os.environ))"
        with mock.patch.dict(os.environ, {"AIPT_TEST_PROBE": "leaked"}):
            hidden = self.run_py(probe)
            shown = self.run_py(probe, env_allowlist=["PATH", "AIPT_TEST_PROBE"])
        self.assertEqual(b"absent", self.log(hidden, "stdout").splitlines()[0])
        self.assertEqual(b"leaked", self.log(shown, "stdout").splitlines()[0])
        self.assertNotIn(b"AIPT_TEST_PROBE", self.log(hidden, "stdout"))
        self.assertEqual(("PATH", "HOME", "LANG", "LC_ALL", "PYTHONPATH"), R.DEFAULT_ENV_ALLOWLIST)

    def test_argument_validation(self):
        bad = [
            dict(task_id="", argv=[PYTHON, "-c", "pass"]),
            dict(task_id="task_demo", argv=[]),
            dict(task_id="task_demo", argv="python3 -c pass"),
            dict(task_id="task_demo", argv=[PYTHON, 3]),
            dict(task_id="task_demo", argv=[""]),
            dict(task_id="task_demo", argv=[PYTHON, "-c", "pass"], timeout_s=0),
            dict(task_id="task_demo", argv=[PYTHON, "-c", "pass"], timeout_s=True),
            dict(task_id="task_demo", argv=[PYTHON, "-c", "pass"], test_ids="T-1"),
            dict(task_id="task_demo", argv=[PYTHON, "-c", "pass"], env_allowlist=[1]),
        ]
        for kwargs in bad:
            kwargs.setdefault("timeout_s", 5)
            with self.subTest(kwargs=kwargs), self.assertRaises(ValidationError):
                R.run_command(self.store, cwd=self.work, policies=self.policies, **kwargs)  # type: ignore[arg-type]
        self.assertEqual([], self.store.receipts_for_task("task_demo"))

    def test_default_policies_come_from_the_repository(self):
        # Without an explicit Policies instance the module loads the checked-in policy set.
        receipt = R.run_command(self.store, task_id="task_demo", argv=[PYTHON, "-c", f"print('{FAKE_SK_TOKEN}')"], cwd=self.work, timeout_s=10)
        self.assertEqual(1, receipt.redactions_applied)
        self.assertEqual(REPO, R.PACKAGE_ROOT)


# --------------------------------------------------------------------------------------------------
# snapshot
# --------------------------------------------------------------------------------------------------


class ManifestSnapshot(ReceiptCase):
    def test_plain_directory_gives_a_deterministic_manifest(self):
        (self.work / "sub").mkdir()
        (self.work / "sub" / "b.txt").write_text("b", encoding="utf-8")
        first = R.snapshot(self.work)
        again = R.snapshot(self.work)
        self.assertEqual({"kind": "manifest", "manifest_sha256": first["manifest_sha256"], "paths": ["."]}, first)
        self.assertEqual(first, again)
        self.assertTrue(R.is_sha256(first["manifest_sha256"]))
        V.ensure_valid({**_receipt_shell(), "snapshot": first}, "receipt")

    def test_manifest_changes_with_content_and_with_paths(self):
        before = R.snapshot(self.work)["manifest_sha256"]
        (self.work / "input.txt").write_text("changed\n", encoding="utf-8")
        after = R.snapshot(self.work)["manifest_sha256"]
        self.assertNotEqual(before, after)
        (self.work / "other.txt").write_text("x", encoding="utf-8")
        whole = R.snapshot(self.work)
        only_input = R.snapshot(self.work, [Path("input.txt")])
        only_input_abs = R.snapshot(self.work, [self.work / "input.txt"])
        self.assertEqual(["input.txt"], only_input["paths"])
        self.assertEqual(only_input, only_input_abs)
        self.assertNotEqual(whole["manifest_sha256"], only_input["manifest_sha256"])
        # Renaming a file changes the manifest even when its bytes do not.
        (self.work / "other.txt").rename(self.work / "renamed.txt")
        self.assertNotEqual(whole["manifest_sha256"], R.snapshot(self.work)["manifest_sha256"])

    def test_manifest_errors(self):
        with self.assertRaises(NotFoundError):
            R.snapshot(self.tmp / "absent")
        with self.assertRaises(NotFoundError):
            R.snapshot(self.work, [Path("missing.txt")])
        with self.assertRaises(ValidationError):
            R.snapshot(self.work, [self.tmp])
        with self.assertRaises(ValidationError):
            R.snapshot(self.work, "input.txt")  # type: ignore[arg-type]


@unittest.skipUnless(GIT, "git executable not available")
class GitSnapshot(ReceiptCase):
    def setUp(self) -> None:
        super().setUp()
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        _git(self.repo, self.tmp, "init", "-q")
        (self.repo / "tracked.txt").write_text("one\n", encoding="utf-8")
        (self.repo / "tests").mkdir()
        (self.repo / "tests" / "test_x.py").write_text("def test(): pass\n", encoding="utf-8")
        _git(self.repo, self.tmp, "add", ".")
        _git(self.repo, self.tmp, "commit", "-q", "-m", "init")
        self.head = _git(self.repo, self.tmp, "rev-parse", "HEAD")

    def test_clean_tree(self):
        snap = R.snapshot(self.repo)
        self.assertEqual({"kind": "git", "commit": self.head, "dirty_diff_sha256": None, "paths": ["."]}, snap)
        V.ensure_valid({**_receipt_shell(), "snapshot": snap}, "receipt")

    def test_dirty_tree_hashes_tracked_changes_and_untracked_files(self):
        (self.repo / "tracked.txt").write_text("two\n", encoding="utf-8")
        modified = R.snapshot(self.repo)
        self.assertEqual("git", modified["kind"])
        self.assertEqual(self.head, modified["commit"])
        self.assertTrue(R.is_sha256(modified["dirty_diff_sha256"]))
        self.assertEqual(modified, R.snapshot(self.repo), "deterministic for the same tree")
        (self.repo / "tracked.txt").write_text("three\n", encoding="utf-8")
        self.assertNotEqual(modified["dirty_diff_sha256"], R.snapshot(self.repo)["dirty_diff_sha256"])
        # A new untracked test file dirties the tree too (a changed test can invalidate a comparison).
        (self.repo / "tracked.txt").write_text("one\n", encoding="utf-8")
        self.assertIsNone(R.snapshot(self.repo)["dirty_diff_sha256"])
        (self.repo / "tests" / "test_new.py").write_text("def test_new(): pass\n", encoding="utf-8")
        untracked = R.snapshot(self.repo)
        self.assertTrue(R.is_sha256(untracked["dirty_diff_sha256"]))

    def test_paths_scope_the_diff(self):
        (self.repo / "tracked.txt").write_text("two\n", encoding="utf-8")
        tests_only = R.snapshot(self.repo, [Path("tests")])
        self.assertEqual(["tests"], tests_only["paths"])
        self.assertIsNone(tests_only["dirty_diff_sha256"], "tests/ is clean")
        tracked_only = R.snapshot(self.repo, [self.repo / "tracked.txt"])
        self.assertEqual(["tracked.txt"], tracked_only["paths"])
        self.assertTrue(R.is_sha256(tracked_only["dirty_diff_sha256"]))
        both = R.snapshot(self.repo, [Path("tests"), Path("tracked.txt")])
        self.assertEqual(["tests", "tracked.txt"], both["paths"])

    def test_committing_moves_the_commit_and_cleans_the_diff(self):
        (self.repo / "tracked.txt").write_text("two\n", encoding="utf-8")
        _git(self.repo, self.tmp, "commit", "-q", "-am", "second")
        snap = R.snapshot(self.repo)
        self.assertNotEqual(self.head, snap["commit"])
        self.assertEqual(_git(self.repo, self.tmp, "rev-parse", "HEAD"), snap["commit"])
        self.assertIsNone(snap["dirty_diff_sha256"])

    def test_unborn_repository_falls_back_to_manifest(self):
        empty = self.tmp / "unborn"
        empty.mkdir()
        _git(empty, self.tmp, "init", "-q")
        (empty / "a.txt").write_text("a", encoding="utf-8")
        snap = R.snapshot(empty)
        self.assertEqual("manifest", snap["kind"])
        self.assertTrue(R.is_sha256(snap["manifest_sha256"]))

    def test_run_command_in_a_repo_records_a_git_snapshot(self):
        receipt = R.run_command(
            self.store, task_id="task_demo", argv=[PYTHON, "-c", "pass"], cwd=self.repo, timeout_s=10, policies=self.policies
        )
        self.assertEqual("git", receipt.snapshot["kind"])
        self.assertEqual(self.head, receipt.snapshot["commit"])
        self.assertIsNone(receipt.snapshot["dirty_diff_sha256"])
        V.ensure_valid(receipt.to_dict(), "receipt")


# --------------------------------------------------------------------------------------------------
# Receipt record
# --------------------------------------------------------------------------------------------------


class ReceiptRecord(unittest.TestCase):
    def test_round_trip_and_defaults(self):
        shell = _receipt_shell()
        receipt = R.Receipt.from_dict(shell)
        self.assertEqual("command_exit_status_only", receipt.proves)
        self.assertEqual({}, receipt.input_hashes)
        self.assertEqual({**shell, "proves": "command_exit_status_only", "input_hashes": {}}, receipt.to_dict())
        self.assertTrue(receipt.ok)
        self.assertFalse(dataclasses_replace(receipt, exit_status=1).ok)
        self.assertFalse(dataclasses_replace(receipt, exit_status=None, timed_out=True).ok)

    def test_from_dict_rejects_bad_shapes(self):
        with self.assertRaises(ValidationError):
            R.Receipt.from_dict({**_receipt_shell(), "bogus": 1})
        with self.assertRaises(ValidationError):
            R.Receipt.from_dict({k: v for k, v in _receipt_shell().items() if k != "cwd"})
        with self.assertRaises(ValidationError):
            R.Receipt.from_dict("rcpt")  # type: ignore[arg-type]


def dataclasses_replace(receipt: R.Receipt, **changes):
    import dataclasses

    return dataclasses.replace(receipt, **changes)


def _receipt_shell() -> dict:
    """A minimal schema-valid receipt payload for snapshot and record tests."""
    return {
        "id": "rcpt_shell",
        "task_id": "task_demo",
        "command": [PYTHON, "-c", "pass"],
        "cwd": "/work",
        "snapshot": {"kind": "manifest", "manifest_sha256": "0" * 64, "paths": ["."]},
        "started_at": "2026-10-17T00:00:00.000Z",
        "ended_at": "2026-10-17T00:00:00.100Z",
        "exit_status": 0,
        "timed_out": False,
        "cancelled": False,
        "stdout_path": "receipts/rcpt_shell.out",
        "stderr_path": "receipts/rcpt_shell.err",
        "observation_source": "controller",
        "test_ids": [],
        "redactions_applied": 0,
    }


if __name__ == "__main__":
    unittest.main()
