"""Tests for tools/build_adapters.py and install.py: generated host files and safe installation."""

from __future__ import annotations

import importlib.util
import io
import json
import re
import tempfile
import tomllib
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


build_adapters = _load("build_adapters", ROOT / "tools" / "build_adapters.py")
installer = _load("aipt_install", ROOT / "install.py")

CLAUDE_AGENT_FIELDS = {"name", "description", "tools", "disallowedTools", "skills"}
SKILL_NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def frontmatter(text: str) -> tuple[dict, str]:
    """Parse the small YAML subset the generator emits: key: value, lists of '  - x', one nested map."""
    assert text.startswith("---\n"), "missing frontmatter"
    head, body = text[4:].split("\n---\n", 1)
    data: dict = {}
    key = None
    for line in head.splitlines():
        if line.startswith("  - "):
            data.setdefault(key, []).append(line[4:])
        elif line.startswith("  "):
            k, v = line.strip().split(": ", 1)
            data.setdefault(key, {})[k] = v.strip('"')
        else:
            key, _, v = line.partition(": ") if ": " in line else (line.rstrip(":"), "", "")
            if v:
                data[key] = json.loads(v) if v.startswith('"') else v
    return data, body


class BuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name)
        cls.manifest = build_adapters.build(cls.out)
        cls.registry = json.loads((ROOT / "registry/agents.json").read_text())
        cls.skills = json.loads((ROOT / "registry/skills.json").read_text())

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_counts_per_host(self):
        self.assertEqual(self.manifest["counts"]["claude"], {"agents": 64, "skills": 41})
        self.assertEqual(self.manifest["counts"]["codex"], {"agents": 64, "skills": 41})

    def test_build_is_deterministic(self):
        with tempfile.TemporaryDirectory() as t:
            again = build_adapters.build(Path(t))
        self.assertEqual(again["files"], self.manifest["files"])

    def test_committed_dist_is_current(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(build_adapters.main(["--check"]), 0, "dist/ is stale; run python3 tools/build_adapters.py")

    def test_claude_agents_use_only_documented_fields_and_no_dispatch_tool(self):
        skill_names = {"aipt-method-" + s["name"] for s in self.skills["skills"]}
        for a in self.registry["agents"]:
            text = (self.out / f"claude/.claude/agents/{a['native_name']}.md").read_text()
            fm, body = frontmatter(text)
            self.assertLessEqual(set(fm), CLAUDE_AGENT_FIELDS, a["id"])
            self.assertEqual(fm["name"], a["native_name"])
            self.assertNotIn("Agent", fm["tools"].split(", "), a["id"])
            self.assertIn("Agent", fm["disallowedTools"].split(", "), a["id"])
            self.assertLessEqual(set(fm["skills"]), skill_names, a["id"])
            self.assertEqual(len(fm["skills"]), len(a["skill_ids"]), a["id"])
            if a["write_scope"] == "proposal-only":
                self.assertFalse({"Write", "Edit", "Bash"} & set(fm["tools"].split(", ")), a["id"])
            self.assertIn(f"# {a['name']}", body)

    def test_codex_agents_parse_and_carry_required_fields(self):
        for a in self.registry["agents"]:
            data = tomllib.loads((self.out / f"codex/.codex/agents/{a['native_name']}.toml").read_text())
            self.assertEqual(set(data), {"name", "description", "developer_instructions"}, a["id"])
            self.assertEqual(data["name"], a["native_name"])
            self.assertNotIn(data["name"], {"default", "worker", "explorer"})
            self.assertIn(a["distinctive_rule"], data["developer_instructions"])
            self.assertIn("Do not start other agents", data["developer_instructions"])

    def test_every_skill_meets_the_agent_skills_name_and_description_rules(self):
        for host, d in (("claude", ".claude/skills"), ("codex", ".agents/skills")):
            dirs = sorted(p for p in (self.out / host / d).iterdir() if p.is_dir())
            self.assertEqual(len(dirs), 41)
            for sd in dirs:
                fm, _ = frontmatter((sd / "SKILL.md").read_text())
                self.assertEqual(fm["name"], sd.name)
                self.assertRegex(fm["name"], SKILL_NAME)
                self.assertLessEqual(len(fm["name"]), 64)
                self.assertTrue(0 < len(fm["description"]) <= 1024, sd.name)

    def test_entry_skills_never_fork_and_cover_all_workflows(self):
        wfs = json.loads((ROOT / "registry/workflows.json").read_text())["workflows"]
        for host, d in (("claude", ".claude/skills"), ("codex", ".agents/skills")):
            for name in ["aipt-start"] + [w["entry_skill"] for w in wfs]:
                text = (self.out / host / d / name / "SKILL.md").read_text()
                self.assertNotIn("context: fork", text, name)
            for w in wfs:
                self.assertTrue((self.out / host / d / w["entry_skill"] / "references/recipe.md").exists())

    def test_installed_copies_point_roles_at_installed_names(self):
        for p in self.out.rglob("*.md"):
            self.assertIsNone(re.search(r"`agents/[a-z0-9-]+\.md`", p.read_text()), str(p))


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.target = Path(self.tmp.name) / "proj"
        self.target.mkdir()
        (self.target / ".claude" / "agents").mkdir(parents=True)
        (self.target / ".claude" / "agents" / "mine.md").write_text("user file\n")
        (self.target / "CLAUDE.md").write_text("# user rules\n")

    def tearDown(self):
        self.tmp.cleanup()

    def run_main(self, *args: str) -> tuple[int, str]:
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = installer.main(["--target", str(self.target), *args])
        return code, buf.getvalue()

    def files(self) -> set[str]:
        return {p.relative_to(self.target).as_posix() for p in self.target.rglob("*") if p.is_file()}

    def test_dry_run_changes_nothing(self):
        before = self.files()
        code, out = self.run_main("--host", "both", "--dry-run")
        self.assertEqual(code, 0)
        self.assertIn("create", out)
        self.assertEqual(self.files(), before)

    def test_install_preserves_user_files_and_is_idempotent(self):
        self.assertEqual(self.run_main("--host", "both")[0], 0)
        self.assertEqual((self.target / "CLAUDE.md").read_text(), "# user rules\n")
        self.assertEqual((self.target / ".claude/agents/mine.md").read_text(), "user file\n")
        self.assertTrue((self.target / ".claude/agents/aipt-claim-checker.md").exists())
        self.assertTrue((self.target / ".codex/agents/aipt-claim-checker.toml").exists())
        code, out = self.run_main("--host", "both")
        self.assertEqual(code, 0)
        self.assertIn("unchanged", out)
        self.assertNotIn("create", out)

    def test_unowned_file_is_a_conflict_and_blocks_install(self):
        clash = self.target / ".claude/agents/aipt-claim-checker.md"
        clash.write_text("someone else's file\n")
        before = self.files()
        code, out = self.run_main("--host", "claude")
        self.assertEqual(code, 1)
        self.assertIn("conflict", out)
        self.assertEqual(self.files(), before)
        self.assertEqual(clash.read_text(), "someone else's file\n")

    def test_backup_conflicts_moves_the_file_aside(self):
        clash = self.target / ".claude/agents/aipt-claim-checker.md"
        clash.write_text("someone else's file\n")
        self.assertEqual(self.run_main("--host", "claude", "--backup-conflicts")[0], 0)
        backups = list((self.target / ".aipt/backup").rglob("aipt-claim-checker.md"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(), "someone else's file\n")

    def test_edited_installed_file_is_a_conflict_on_reinstall_and_kept_on_uninstall(self):
        self.run_main("--host", "claude")
        edited = self.target / ".claude/agents/aipt-claim-checker.md"
        edited.write_text(edited.read_text() + "\nmy note\n")
        self.assertEqual(self.run_main("--host", "claude")[0], 1)
        code, out = self.run_main("--uninstall")
        self.assertEqual(code, 0)
        self.assertTrue(edited.exists())
        self.assertIn("kept", out)
        self.assertFalse((self.target / ".claude/agents/aipt-context-analyst.md").exists())
        self.assertTrue((self.target / ".claude/agents/mine.md").exists())

    def test_uninstall_removes_everything_it_wrote(self):
        before = self.files()
        self.run_main("--host", "both")
        self.assertEqual(self.run_main("--uninstall")[0], 0)
        self.assertEqual(self.files(), before)
        self.assertFalse((self.target / ".aipt").exists())

    def test_refuses_to_write_through_a_symlink(self):
        outside = Path(self.tmp.name) / "outside"
        outside.mkdir()
        (self.target / ".codex").symlink_to(outside, target_is_directory=True)
        code, out = self.run_main("--host", "codex")
        self.assertEqual(code, 1)
        self.assertIn("symlink", out)
        self.assertEqual(list(outside.iterdir()), [])

    def test_refuses_paths_outside_host_directories(self):
        with self.assertRaises(installer.InstallError):
            installer.safe_dest(self.target, "../escape.md", "claude")
        with self.assertRaises(installer.InstallError):
            installer.safe_dest(self.target, "CLAUDE.md", "claude")
        with self.assertRaises(installer.InstallError):
            installer.safe_dest(self.target, ".codex/agents/x.toml", "claude")


if __name__ == "__main__":
    unittest.main()
