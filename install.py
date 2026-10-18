#!/usr/bin/env python3
"""Install, upgrade, inspect or remove the AI Product Team in one project, safely.

Single responsibility: copy the generated host files from ``dist/<host>/`` into a target project and keep
an ownership manifest at ``<target>/.aipt/install-manifest.json`` so that upgrades and removal touch only
files this script wrote and the user has not changed since.

    python3 install.py --target ~/code/my-app --host claude --dry-run
    python3 install.py --target ~/code/my-app --host both
    python3 install.py --target ~/code/my-app --status
    python3 install.py --target ~/code/my-app --uninstall --dry-run

Rules it never breaks:
- It writes only inside the target, only under the host's own directories (.claude/, .codex/, .agents/)
  and .aipt/. It never edits CLAUDE.md, AGENTS.md, .gitignore, settings or anything global.
- A file it did not write, or one it wrote that the user has since edited, is a conflict. Conflicts stop
  the whole install and change nothing, unless --backup-conflicts is given, which moves each conflicting
  file to .aipt/backup/<timestamp>/ first.
- --dry-run prints the plan and changes nothing.
- Uninstall removes only files whose content still matches what was installed; edited files are kept and
  listed.

Standard library only (Python 3.11+).
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent
DIST = PACKAGE_ROOT / "dist"
MANIFEST_REL = Path(".aipt") / "install-manifest.json"
HOSTS = ("claude", "codex")
ALLOWED_TOP = {"claude": (".claude",), "codex": (".codex", ".agents")}


class InstallError(Exception):
    """Raised for unsafe paths, missing dist files or a corrupt manifest."""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_dest(target: Path, rel: str, host: str) -> Path:
    """Resolve ``rel`` under ``target`` and refuse anything that escapes it or leaves the host's directories."""
    parts = Path(rel).parts
    if not parts or parts[0] not in ALLOWED_TOP[host] or ".." in parts or Path(rel).is_absolute():
        raise InstallError(f"refusing path outside the {host} directories: {rel}")
    dest = target / rel
    probe = target
    for part in parts[:-1]:
        probe = probe / part
        if probe.is_symlink():
            raise InstallError(f"refusing to write through a symlink: {probe}")
    if not dest.resolve().is_relative_to(target.resolve()):
        raise InstallError(f"refusing path that resolves outside the target: {rel}")
    return dest


def load_manifest(target: Path) -> dict:
    p = target / MANIFEST_REL
    if not p.exists():
        return {"package": "ai-product-team", "files": {}}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise InstallError(f"corrupt manifest {p}: {e}") from e
    if not isinstance(data.get("files"), dict):
        raise InstallError(f"corrupt manifest {p}: missing files map")
    return data


def write_manifest(target: Path, manifest: dict) -> None:
    p = target / MANIFEST_REL
    if not manifest["files"]:
        if p.exists():
            p.unlink()
        return
    p.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(p, (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8"))


def atomic_write(dest: Path, data: bytes) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=dest.parent, prefix=".aipt-tmp-")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        os.replace(tmp, dest)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def source_files(host: str) -> dict[str, Path]:
    root = DIST / host
    if not root.is_dir():
        raise InstallError(f"{root} is missing; run python3 tools/build_adapters.py first")
    return {p.relative_to(root).as_posix(): p for p in sorted(root.rglob("*")) if p.is_file() and p.name != ".DS_Store"}


def plan_install(target: Path, hosts: list[str], manifest: dict) -> dict:
    """Classify every file as create, update, unchanged, adopt, conflict or remove (stale owned file)."""
    plan = {"create": [], "update": [], "unchanged": [], "adopt": [], "conflict": [], "remove": [], "keep_modified": []}
    wanted: dict[str, tuple[str, Path]] = {}
    for host in hosts:
        for rel, src in source_files(host).items():
            wanted[rel] = (host, src)
    for rel, (host, src) in wanted.items():
        dest = safe_dest(target, rel, host)
        new_hash = sha256(src)
        owned = manifest["files"].get(rel)
        if not dest.exists():
            plan["create"].append(rel)
        elif owned is None:
            plan["adopt" if sha256(dest) == new_hash else "conflict"].append(rel)
        elif sha256(dest) != owned["sha256"]:
            plan["conflict"].append(rel)
        elif owned["sha256"] == new_hash:
            plan["unchanged"].append(rel)
        else:
            plan["update"].append(rel)
    for rel, owned in manifest["files"].items():
        if rel in wanted or owned.get("host") not in hosts:
            continue
        dest = safe_dest(target, rel, owned["host"])
        if dest.exists() and sha256(dest) != owned["sha256"]:
            plan["keep_modified"].append(rel)
        else:
            plan["remove"].append(rel)
    plan["_wanted"] = wanted
    return plan


def prune_empty_dirs(target: Path, rels: list[str]) -> None:
    for rel in sorted(rels, key=lambda r: -len(Path(r).parts)):
        d = (target / rel).parent
        while d != target and d.is_dir() and not any(d.iterdir()):
            d.rmdir()
            d = d.parent


def install(target: Path, hosts: list[str], *, dry_run: bool, backup_conflicts: bool, out=print) -> int:
    manifest = load_manifest(target)
    plan = plan_install(target, hosts, manifest)
    wanted = plan.pop("_wanted")
    for key in ("create", "update", "adopt", "unchanged", "remove", "keep_modified", "conflict"):
        if plan[key]:
            out(f"{key:14s} {len(plan[key])}")
    for rel in plan["conflict"]:
        out(f"  conflict: {rel} (exists and was not written by this installer, or was edited since)")
    for rel in plan["keep_modified"]:
        out(f"  kept: {rel} (no longer in the package, but edited since install)")
    if plan["conflict"] and not backup_conflicts:
        out("Nothing changed. Resolve the conflicts, or rerun with --backup-conflicts to move them to .aipt/backup/ first.")
        return 1
    if dry_run:
        out("Dry run: nothing changed.")
        return 0
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for rel in plan["conflict"]:
        host, _ = wanted[rel]
        dest = safe_dest(target, rel, host)
        backup = target / ".aipt" / "backup" / stamp / rel
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(dest), str(backup))
        out(f"  backed up: {rel} -> {backup.relative_to(target)}")
    for rel in plan["create"] + plan["update"] + plan["conflict"]:
        host, src = wanted[rel]
        atomic_write(safe_dest(target, rel, host), src.read_bytes())
    for rel in plan["create"] + plan["update"] + plan["conflict"] + plan["adopt"] + plan["unchanged"]:
        host, src = wanted[rel]
        manifest["files"][rel] = {"host": host, "sha256": sha256(src)}
    for rel in plan["remove"]:
        dest = safe_dest(target, rel, manifest["files"][rel]["host"])
        if dest.exists():
            dest.unlink()
        del manifest["files"][rel]
    prune_empty_dirs(target, plan["remove"])
    manifest.update({"package": "ai-product-team", "version": json.loads((DIST / "MANIFEST.json").read_text())["version"],
                     "hosts": sorted({v["host"] for v in manifest["files"].values()}), "updated_at": stamp})
    write_manifest(target, manifest)
    out(f"Installed for {', '.join(hosts)} into {target}.")
    return 0


def uninstall(target: Path, *, dry_run: bool, out=print) -> int:
    manifest = load_manifest(target)
    if not manifest["files"]:
        out("Nothing installed here.")
        return 0
    remove, keep = [], []
    for rel, owned in sorted(manifest["files"].items()):
        dest = safe_dest(target, rel, owned["host"])
        if not dest.exists() or sha256(dest) == owned["sha256"]:
            remove.append(rel)
        else:
            keep.append(rel)
    out(f"remove {len(remove)}  keep (edited since install) {len(keep)}")
    for rel in keep:
        out(f"  kept: {rel}")
    if dry_run:
        out("Dry run: nothing changed.")
        return 0
    for rel in remove:
        dest = target / rel
        if dest.exists():
            dest.unlink()
        del manifest["files"][rel]
    prune_empty_dirs(target, remove)
    write_manifest(target, manifest)
    aipt = target / ".aipt"
    if aipt.is_dir() and not any(aipt.iterdir()):
        aipt.rmdir()
    out("Uninstalled." if not keep else "Uninstalled; edited files were kept and stay listed in the manifest.")
    return 0


def status(target: Path, out=print) -> int:
    manifest = load_manifest(target)
    if not manifest["files"]:
        out("Not installed.")
        return 0
    edited = [rel for rel, o in manifest["files"].items() if (target / rel).exists() and sha256(target / rel) != o["sha256"]]
    missing = [rel for rel in manifest["files"] if not (target / rel).exists()]
    out(f"version {manifest.get('version')}  hosts {', '.join(manifest.get('hosts', []))}  files {len(manifest['files'])}  edited {len(edited)}  missing {len(missing)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Install the AI Product Team agents and skills into one project.")
    ap.add_argument("--target", required=True, type=Path, help="project directory to install into")
    ap.add_argument("--host", choices=("claude", "codex", "both"), default="both")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--uninstall", action="store_true")
    mode.add_argument("--status", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="print the plan; change nothing")
    ap.add_argument("--backup-conflicts", action="store_true", help="move conflicting files to .aipt/backup/ before installing")
    args = ap.parse_args(argv)
    target = args.target.expanduser().resolve()
    if not target.is_dir():
        print(f"Target is not a directory: {target}")
        return 2
    if target == PACKAGE_ROOT or target.is_relative_to(PACKAGE_ROOT):
        print("Refusing to install into the package repository itself; choose a project directory.")
        return 2
    try:
        if args.status:
            return status(target)
        if args.uninstall:
            return uninstall(target, dry_run=args.dry_run)
        hosts = list(HOSTS) if args.host == "both" else [args.host]
        return install(target, hosts, dry_run=args.dry_run, backup_conflicts=args.backup_conflicts)
    except InstallError as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
