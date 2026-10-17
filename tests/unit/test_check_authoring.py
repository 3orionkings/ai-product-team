"""Unit tests for tools/check_authoring.py.

Every gate has a positive and a negative case built from synthetic fixtures in a TemporaryDirectory,
including a tiny fake registry. Run with::

    cd <repo> && PYTHONPATH=src python3 -m unittest tests.unit.test_check_authoring -v
"""

from __future__ import annotations

import contextlib
import io
import json
import random
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import check_authoring as ca  # noqa: E402  (import after sys.path tweak)

# --------------------------------------------------------------------------------------------------
# Fixture material
# --------------------------------------------------------------------------------------------------

LICENSE_LINE = "See LICENSE_PENDING.md in the repository root."

VOCAB = (
    "record version proposal review requirement claim source receipt artifact finding evidence "
    "scope boundary cohort baseline threshold criterion fixture envelope status escalate reviewer "
    "manager workspace ticket draft reply template library option variant measure population period "
    "observation hypothesis fact unknown route plan budget order dependency output heading table "
    "ruling conflict tradeoff direction follow-up request owner judge authority delegation canary "
    "index filter summary cache query latency sample slice split manifest frozen protected"
).split()

TEAMS = [
    {"id": "leadership", "name": "Leadership and coordination", "leader": None, "manager": None},
    {"id": "research", "name": "Research and evidence", "leader": "product-director", "manager": "research-manager"},
]

SKILLS = [
    {"id": "S01", "name": "discovery-interrogation", "provenance": {"status": "adapt", "source_ids": ["A01"]}},
    {"id": "S02", "name": "corpus-grounded-onboarding", "provenance": {"status": "adapt", "source_ids": ["A02"]}},
    {"id": "S04", "name": "context-files-architecture", "provenance": {"status": "adapt", "source_ids": ["A04"]}},
    {"id": "S06", "name": "research-consolidation", "provenance": {"status": "adapt", "source_ids": ["A06"]}},
    {"id": "S12", "name": "evidence-and-lineage", "provenance": {"status": "newly_authored", "source_ids": []}},
]
SKILL_NAME_BY_ID = {s["id"]: "aipt-method-" + s["name"] for s in SKILLS}

AGENTS = [
    {
        "number": 1,
        "id": "product-director",
        "name": "Product Director",
        "type": "leader",
        "team": "leadership",
        "reports_to": "human-owner",
        "reviewed_by": "human-owner",
        "description": "Keeps the teams focused on the customer problem and intended outcome.",
        "skill_ids": ["S01", "S02"],
        "distinctive_rule": "Lead discovery, research and experience managers; intervene only in cross-team product tradeoffs.",
        "negative_test": "Must not approve a feature merely because three teams recommend it.",
        "write_scope": "proposal-only",
        "may_dispatch": False,
        "acceptance_authority": "none",
        "dispatch_condition": "never; return requested follow-up work orders",
    },
    {
        "number": 4,
        "id": "workflow-orchestrator",
        "name": "Workflow Orchestrator",
        "type": "leader",
        "team": "leadership",
        "reports_to": "human-owner",
        "reviewed_by": "human-owner",
        "description": "Routes cases through workflows.",
        "skill_ids": ["S02", "S04"],
        "distinctive_rule": "Owns budget modes and replanning; never rules on product substance.",
        "negative_test": "Must not dispatch from a child session.",
        "write_scope": "proposal-only",
        "may_dispatch": True,
        "acceptance_authority": "none",
        "dispatch_condition": "root_session_only; in a child return a route proposal",
    },
    {
        "number": 12,
        "id": "source-researcher",
        "name": "Source Researcher",
        "type": "specialist",
        "team": "research",
        "reports_to": "research-manager",
        "reviewed_by": "research-manager",
        "description": "Finds and records sources.",
        "skill_ids": ["S06"],
        "distinctive_rule": "Record the source before the claim; never cite from memory.",
        "negative_test": "Must not present an unretrieved reference as a source.",
        "write_scope": "proposal-only",
        "may_dispatch": False,
        "acceptance_authority": "none",
        "dispatch_condition": "never; return requested follow-up work orders",
    },
]
AGENT_BY_ID = {a["id"]: a for a in AGENTS}


def words(seed: str, count: int) -> str:
    rng = random.Random(seed)
    return " ".join(rng.choice(VOCAB) for _ in range(count))


def bullets(seed: str, title: str, count: int) -> list[str]:
    return [f"- {words(f'{seed}|{title}|{i}', 9).capitalize()}." for i in range(count)]


def steps(seed: str, count: int) -> list[str]:
    return [f"{i + 1}. {words(f'{seed}|method|{i}', 11).capitalize()}." for i in range(count)]


def section(title: str, body: list[str]) -> list[str]:
    return [f"## {title}", ""] + body + [""]


def make_skill(
    name: str = "aipt-method-discovery-interrogation",
    *,
    skill_id: str = "S01",
    provenance: str = "adapt",
    version: str = "0.1.0",
    description: str | None = None,
    license_line: str | None = LICENSE_LINE,
    extra_metadata: dict[str, str] | None = None,
    drop_metadata: tuple[str, ...] = (),
    extra_frontmatter: list[str] | None = None,
    frontmatter: list[str] | None = None,
    headings: tuple[str, ...] = ca.SKILL_HEADINGS,
    lines_per_section: int = 10,
    method: list[str] | None = None,
    title: str | None = "Discovery interrogation",
    extra_body: list[str] | None = None,
) -> str:
    """Return SKILL.md text that passes every gate unless an override says otherwise."""
    if description is None:
        description = "Discovery questions, problem reconstruction, decision-critical gaps. Use before design."
    if frontmatter is None:
        frontmatter = ["---", f"name: {name}", f"description: {description}"]
        if license_line is not None:
            frontmatter.append(f"license: {license_line}")
        meta = {"aipt_skill_id": skill_id, "aipt_provenance": provenance, "aipt_version": version}
        for key in drop_metadata:
            meta.pop(key, None)
        meta.update(extra_metadata or {})
        frontmatter.append("metadata:")
        frontmatter.extend(f'  {key}: "{value}"' for key, value in meta.items())
        frontmatter.extend(extra_frontmatter or [])
        frontmatter.append("---")
    body: list[str] = []
    if title is not None:
        body += [f"# {title}", ""]
    for heading in headings:
        if heading == "Method":
            body += section(heading, method if method is not None else steps(name, lines_per_section))
        else:
            body += section(heading, bullets(name, heading, lines_per_section))
    body += extra_body or []
    return "\n".join(frontmatter + body) + "\n"


def position_block(entry: dict, **overrides: str) -> list[str]:
    team_name = next(t["name"] for t in TEAMS if t["id"] == entry["team"])
    skills = ", ".join(f"`{SKILL_NAME_BY_ID[sid]}` ({sid})" for sid in entry["skill_ids"])
    values = {
        "role_id": entry["id"],
        "type": entry["type"],
        "team": team_name,
        "reports_to": entry["reports_to"],
        "reviewed_by": entry["reviewed_by"],
        "write_scope": entry["write_scope"],
        "may_dispatch": "yes" if entry["may_dispatch"] else "no",
        "acceptance_authority": entry["acceptance_authority"],
        "dispatch_condition": entry["dispatch_condition"],
        "shared_skills": skills,
    }
    values.update(overrides)
    return [
        f"- Role id: `{values['role_id']}` · Type: {values['type']} · Team: {values['team']}",
        f"- Reports to: `{values['reports_to']}` · Reviewed by: `{values['reviewed_by']}`",
        f"- Write scope: {values['write_scope']} · May dispatch: {values['may_dispatch']} · "
        f"Acceptance authority: {values['acceptance_authority']}",
        f"- Dispatch condition: {values['dispatch_condition']}",
        f"- Shared skills: {values['shared_skills']}",
    ]


def make_agent(
    role_id: str = "product-director",
    *,
    headings: tuple[str, ...] = ca.AGENT_HEADINGS,
    lines_per_section: int = 10,
    position: list[str] | None = None,
    position_overrides: dict[str, str] | None = None,
    distinctive: list[str] | None = None,
    negative: list[str] | None = None,
    method: list[str] | None = None,
    worked_example: list[str] | None = None,
    title: str | None = None,
    extra_body: list[str] | None = None,
) -> str:
    """Return a role body that passes every gate for ``role_id`` unless an override says otherwise."""
    entry = AGENT_BY_ID[role_id]
    body = [f"# {title or entry['name']}", "", entry["description"], ""]
    for heading in headings:
        if heading == "Position":
            body += section(heading, position if position is not None else position_block(entry, **(position_overrides or {})))
        elif heading == "Method":
            body += section(heading, method if method is not None else steps(role_id, lines_per_section))
        elif heading == "Distinctive rule":
            content = distinctive if distinctive is not None else [entry["distinctive_rule"], ""] + bullets(role_id, heading, lines_per_section - 2)
            body += section(heading, content)
        elif heading == "Negative case":
            content = negative if negative is not None else [entry["negative_test"], ""] + bullets(role_id, heading, lines_per_section - 2)
            body += section(heading, content)
        elif heading == "Worked example" and worked_example is not None:
            body += section(heading, worked_example)
        else:
            body += section(heading, bullets(role_id, heading, lines_per_section))
    body += extra_body or []
    return "\n".join(body) + "\n"


class FixtureRoot:
    """A temporary repository root with a fake registry."""

    def __init__(self, *, skills_registry: bool = True, agents_registry: bool = True) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "registry").mkdir()
        if skills_registry:
            (self.root / "registry" / "skills.json").write_text(json.dumps({"skills": SKILLS}), encoding="utf-8")
        if agents_registry:
            (self.root / "registry" / "agents.json").write_text(json.dumps({"teams": TEAMS, "agents": AGENTS}), encoding="utf-8")

    def cleanup(self) -> None:
        self._tmp.cleanup()

    def add_skill(self, name: str, text: str) -> Path:
        directory = self.root / "skills" / name
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / "SKILL.md"
        path.write_text(text, encoding="utf-8")
        return path

    def add_agent(self, role_id: str, text: str) -> Path:
        directory = self.root / "agents"
        directory.mkdir(exist_ok=True)
        path = directory / f"{role_id}.md"
        path.write_text(text, encoding="utf-8")
        return path

    def skills(self) -> dict[str, ca.FileResult]:
        return {r.path: r for r in ca.run_skills(self.root)}

    def agents(self) -> dict[str, ca.FileResult]:
        return {r.path: r for r in ca.run_agents(self.root)}


def gates(result: ca.FileResult, gate: str | None = None) -> list[ca.Finding]:
    return [f for f in result.findings if gate is None or f.gate == gate]


class GateTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.fx = FixtureRoot()
        self.addCleanup(self.fx.cleanup)

    def assertPasses(self, result: ca.FileResult) -> None:
        self.assertTrue(result.ok, f"expected pass, got findings: {[f.to_json() for f in result.findings]}")

    def assertFails(self, result: ca.FileResult, gate: str, fragment: str | None = None) -> list[ca.Finding]:
        failing = [f for f in gates(result, gate) if f.severity in ca.FAILING_SEVERITIES]
        self.assertTrue(failing, f"expected a failing {gate!r} finding; got {[f.to_json() for f in result.findings]}")
        self.assertFalse(result.ok)
        if fragment is not None:
            self.assertTrue(any(fragment in f.message for f in failing), f"{fragment!r} not in {[f.message for f in failing]}")
        return failing

    def skill(self, name: str = "aipt-method-discovery-interrogation", **kwargs) -> ca.FileResult:
        self.fx.add_skill(name, make_skill(name, **kwargs))
        return self.fx.skills()[f"skills/{name}/SKILL.md"]

    def agent(self, role_id: str = "product-director", **kwargs) -> ca.FileResult:
        self.fx.add_agent(role_id, make_agent(role_id, **kwargs))
        return self.fx.agents()[f"agents/{role_id}.md"]


# --------------------------------------------------------------------------------------------------
# Skill gates
# --------------------------------------------------------------------------------------------------


class TestSkillFrontmatterParsing(GateTestCase):
    def test_valid_frontmatter_parses(self) -> None:
        lines = make_skill().splitlines()
        fm, body_start, findings = ca.parse_frontmatter(lines)
        self.assertEqual(findings, [])
        self.assertIsNotNone(fm)
        self.assertEqual(fm.data["name"], "aipt-method-discovery-interrogation")
        self.assertEqual(fm.data["metadata"], {"aipt_skill_id": "S01", "aipt_provenance": "adapt", "aipt_version": "0.1.0"})
        self.assertEqual(lines[body_start], "# Discovery interrogation")
        self.assertEqual(fm.key_lines["metadata.aipt_skill_id"], 6)
        self.assertPasses(self.skill())

    def test_rejects_yaml_outside_the_subset(self) -> None:
        cases = {
            "list": ["---", "name: x", "tags:", "  - a", "---"],
            "other nested map": ["---", "name: x", "extra:", "  k: v", "---"],
            "empty metadata map": ["---", "name: x", "metadata:", "---"],
            "blank line": ["---", "name: x", "", "description: y", "---"],
            "comment": ["---", "# note", "name: x", "---"],
            "duplicate key": ["---", "name: x", "name: y", "---"],
            "flow mapping": ["---", "name: {a: b}", "---"],
            "block scalar": ["---", "description: |", "  text", "---"],
            "unterminated": ["---", "name: x"],
            "no frontmatter": ["# Title", "## Purpose"],
            "indent outside metadata": ["---", "name: x", "  stray: y", "---"],
            "inconsistent indent": ["---", "metadata:", "  a: 1", "    b: 2", "---"],
            "unterminated quote": ["---", 'name: "x', "---"],
        }
        for label, lines in cases.items():
            with self.subTest(label):
                fm, _, findings = ca.parse_frontmatter(lines)
                self.assertIsNone(fm)
                self.assertEqual(len(findings), 1)
                self.assertEqual(findings[0].gate, "frontmatter")
                self.assertEqual(findings[0].severity, "major")

    def test_broken_frontmatter_fails_the_file_but_other_gates_still_run(self) -> None:
        result = self.skill(frontmatter=["---", "name: aipt-method-discovery-interrogation", "tags:", "  - a", "---"])
        self.assertFails(result, "frontmatter", "lists")
        # Headings after the (located) closing fence are still found, so no structure finding appears.
        self.assertEqual(gates(result, "structure"), [])


class TestSkillName(GateTestCase):
    def test_name_equal_to_directory_and_pattern_passes(self) -> None:
        self.assertPasses(self.skill("aipt-method-discovery-interrogation"))

    def test_name_not_equal_to_directory_fails(self) -> None:
        self.fx.add_skill("aipt-method-discovery-interrogation", make_skill("aipt-method-corpus-grounded-onboarding"))
        result = self.fx.skills()["skills/aipt-method-discovery-interrogation/SKILL.md"]
        self.assertFails(result, "name", "does not equal the directory name")

    def test_name_pattern_violations_fail(self) -> None:
        for bad in ("aipt-method-Discovery", "discovery-interrogation", "aipt-method--double", "aipt-method-ends-"):
            with self.subTest(bad):
                self.fx.add_skill(bad, make_skill(bad))
                result = self.fx.skills()[f"skills/{bad}/SKILL.md"]
                self.assertFails(result, "name", "does not match")

    def test_name_longer_than_64_fails(self) -> None:
        long_name = "aipt-method-" + "-".join(["abcde"] * 10)  # 71 characters, otherwise valid
        self.assertGreater(len(long_name), 64)
        self.fx.add_skill(long_name, make_skill(long_name))
        self.assertFails(self.fx.skills()[f"skills/{long_name}/SKILL.md"], "name", "maximum is 64")


class TestSkillDescription(GateTestCase):
    def test_short_description_passes(self) -> None:
        self.assertPasses(self.skill(description="Trigger words first. Use when discovery is needed."))

    def test_empty_or_missing_description_fails(self) -> None:
        self.assertFails(self.skill(description=" "), "description", "missing or empty")
        no_description = make_skill().replace("description: Discovery questions, problem reconstruction, decision-critical gaps. Use before design.\n", "")
        self.fx.add_skill("aipt-method-discovery-interrogation", no_description)
        self.assertFails(self.fx.skills()["skills/aipt-method-discovery-interrogation/SKILL.md"], "description", "missing")

    def test_description_over_600_warns_and_over_1024_fails(self) -> None:
        warned = self.skill(description="w" * 700)
        self.assertPasses(warned)
        self.assertEqual([f.severity for f in gates(warned, "description")], ["warning"])
        self.assertFails(self.skill(description="x" * 1025), "description", "hard limit is 1024")


class TestSkillLicense(GateTestCase):
    def test_license_present_passes(self) -> None:
        self.assertPasses(self.skill())

    def test_license_missing_or_empty_fails(self) -> None:
        self.assertFails(self.skill(license_line=None), "license", "missing")
        self.assertFails(self.skill(license_line=""), "license", "missing or empty")


class TestSkillMetadata(GateTestCase):
    def test_exact_metadata_passes(self) -> None:
        self.assertPasses(self.skill())

    def test_missing_metadata_key_fails(self) -> None:
        self.assertFails(self.skill(drop_metadata=("aipt_version",)), "metadata", "missing aipt_version")

    def test_extra_metadata_key_fails(self) -> None:
        self.assertFails(self.skill(extra_metadata={"aipt_owner": "x"}), "metadata", "unexpected keys aipt_owner")

    def test_invalid_metadata_values_fail(self) -> None:
        self.assertFails(self.skill(skill_id="S29"), "metadata", "not in S01-S28")
        self.assertFails(self.skill(skill_id="s01"), "metadata", "not in S01-S28")
        self.assertFails(self.skill(provenance="reuse"), "metadata", "adapt or newly_authored")
        self.assertFails(self.skill(version="v1"), "metadata", "must look like 0.1.0")

    def test_missing_metadata_map_fails(self) -> None:
        fm = ["---", "name: aipt-method-discovery-interrogation", "description: d", f"license: {LICENSE_LINE}", "---"]
        self.assertFails(self.skill(frontmatter=fm), "metadata", "metadata map is missing")

    def test_unknown_top_level_key_only_warns(self) -> None:
        result = self.skill(extra_frontmatter=["allowed-tools: Read"])
        self.assertPasses(result)
        self.assertEqual([f.severity for f in gates(result, "frontmatter")], ["warning"])


class TestSkillHeadings(GateTestCase):
    def test_ten_headings_in_order_pass(self) -> None:
        self.assertPasses(self.skill())

    def test_missing_heading_fails(self) -> None:
        headings = tuple(h for h in ca.SKILL_HEADINGS if h != "Guardrails")
        self.assertFails(self.skill(headings=headings), "structure", "missing H2 heading '## Guardrails'")

    def test_out_of_order_heading_fails(self) -> None:
        swapped = list(ca.SKILL_HEADINGS)
        swapped[1], swapped[2] = swapped[2], swapped[1]
        self.assertFails(self.skill(headings=tuple(swapped)), "structure", "out of order")

    def test_extra_heading_fails(self) -> None:
        self.assertFails(self.skill(extra_body=["## Notes", "", "- a", ""]), "structure", "unexpected H2 heading '## Notes'")

    def test_duplicate_heading_fails(self) -> None:
        self.assertFails(self.skill(extra_body=["## Example", "", "- again", ""]), "structure", "duplicate H2 heading")

    def test_missing_title_fails(self) -> None:
        self.assertFails(self.skill(title=None), "structure", "missing the '# <Title>' heading")

    def test_headings_inside_code_fences_are_ignored(self) -> None:
        fenced = ["```markdown", "## Not a heading", "# Not a title", "```"]
        self.assertPasses(self.skill(extra_body=fenced))

    def test_unclosed_fence_fails(self) -> None:
        self.assertFails(self.skill(extra_body=["```", "## hidden"]), "structure", "never closed")


class TestSkillLength(GateTestCase):
    def test_length_in_target_passes_cleanly(self) -> None:
        result = self.skill(lines_per_section=10)  # 141 lines
        self.assertPasses(result)
        self.assertEqual(gates(result, "length"), [])

    def test_length_outside_target_warns(self) -> None:
        low = self.skill(lines_per_section=7)  # 111 lines
        self.assertPasses(low)
        self.assertEqual([f.severity for f in gates(low, "length")], ["warning"])
        high = self.skill(lines_per_section=30)  # 341 lines
        self.assertPasses(high)
        self.assertEqual([f.severity for f in gates(high, "length")], ["warning"])

    def test_length_outside_hard_bounds_fails(self) -> None:
        self.assertFails(self.skill(lines_per_section=4), "length", "within 90-360")  # 81 lines
        self.assertFails(self.skill(lines_per_section=35), "length", "within 90-360")  # 391 lines

    def test_check_length_boundaries(self) -> None:
        self.assertEqual(ca.check_length(120, ca.SKILL_LENGTH, "x"), [])
        self.assertEqual(ca.check_length(300, ca.SKILL_LENGTH, "x"), [])
        self.assertEqual(ca.check_length(90, ca.SKILL_LENGTH, "x")[0].severity, "warning")
        self.assertEqual(ca.check_length(360, ca.SKILL_LENGTH, "x")[0].severity, "warning")
        self.assertEqual(ca.check_length(89, ca.SKILL_LENGTH, "x")[0].severity, "major")
        self.assertEqual(ca.check_length(361, ca.SKILL_LENGTH, "x")[0].severity, "major")


class TestProhibitedContent(GateTestCase):
    def test_clean_body_has_no_hits(self) -> None:
        clean = [
            "- Read the corpus and the options list before ruling.",
            "- Options: O0 do nothing, O1 shared template library, O3 variant.",
            "- Budget: focused; p95 latency; the receipt names the version.",
            "- Compare per workspace and per ticket, not per team.",
        ]
        self.assertEqual(ca.scan_prohibited(clean), [])
        self.assertPasses(self.skill(extra_body=["## Example", "", *clean][2:] and []))

    def test_each_prohibited_category_is_flagged(self) -> None:
        cases = {
            "provider_or_model_name": "Ask Claude or OpenAI for a draft.",
            "model_id": "Use gpt-4o-mini for the cheap path.",
            "currency_amount": "The pilot costs $12 per seat.",
            "token_rate": "Priced per 1k tokens on the input side.",
            "persona_opener": "You are a world-class analyst.",
            "filler": "It is important to note that drafts are never sent.",
            "emoji": "Ship it ✅ when green.",
        }
        for category, line in cases.items():
            with self.subTest(category):
                findings = ca.scan_prohibited([line])
                self.assertTrue(findings, f"{line!r} produced no finding")
                self.assertIn(category, {f.message.split(":")[0] for f in findings})
                self.assertTrue(all(f.gate == "prohibited_content" and f.severity == "major" for f in findings))
                self.assertEqual(findings[0].line, 1)

    def test_lowercase_short_model_names_flagged_but_option_labels_are_not(self) -> None:
        self.assertEqual(sorted(f.message for f in ca.scan_prohibited(["Route hard cases to o1 or o3-mini."])),
                         ["model_id: 'o3-mini'", "provider_or_model_name: 'o1'"])
        self.assertEqual(ca.scan_prohibited(["| criterion | O0 | O1 | A1 |", "O4 is the fourth option."]), [])

    def test_overlapping_matches_reported_once(self) -> None:
        findings = ca.scan_prohibited(["claude-3-haiku"])
        self.assertEqual(len(findings), 1)
        self.assertTrue(findings[0].message.startswith("model_id:"))

    def test_prohibited_content_fails_a_skill_with_line_number(self) -> None:
        result = self.skill(extra_body=["", "Be sure to check the price: £5 per million tokens.", ""])
        failing = self.assertFails(result, "prohibited_content")
        categories = {f.message.split(":")[0] for f in failing}
        self.assertEqual(categories, {"filler", "currency_amount", "token_rate"})
        self.assertTrue(all(isinstance(f.line, int) for f in failing))


class TestSkillNearDuplicates(GateTestCase):
    def test_distinct_methods_are_not_flagged(self) -> None:
        self.fx.add_skill("aipt-method-discovery-interrogation", make_skill("aipt-method-discovery-interrogation"))
        self.fx.add_skill("aipt-method-corpus-grounded-onboarding", make_skill("aipt-method-corpus-grounded-onboarding", skill_id="S02"))
        results = self.fx.skills()
        self.assertTrue(all(not gates(r, "near_duplicate") for r in results.values()))

    def test_identical_methods_are_blocking_and_reported_once(self) -> None:
        shared = steps("shared", 10)
        self.fx.add_skill("aipt-method-discovery-interrogation", make_skill("aipt-method-discovery-interrogation", method=shared))
        self.fx.add_skill("aipt-method-corpus-grounded-onboarding", make_skill("aipt-method-corpus-grounded-onboarding", skill_id="S02", method=shared))
        results = self.fx.skills()
        hits = [(p, f) for p, r in results.items() for f in gates(r, "near_duplicate")]
        self.assertEqual(len(hits), 1)
        path, finding = hits[0]
        self.assertEqual(path, "skills/aipt-method-corpus-grounded-onboarding/SKILL.md")  # first in sort order
        self.assertEqual(finding.severity, "blocking")
        self.assertIn("aipt-method-discovery-interrogation", finding.message)
        self.assertIn("1.00", finding.message)
        self.assertFalse(results[path].ok)
        self.assertTrue(results["skills/aipt-method-discovery-interrogation/SKILL.md"].ok)

    def test_partial_overlap_is_major(self) -> None:
        common = steps("common", 6)
        a = common + steps("only-a", 4)
        b = common + steps("only-b", 4)
        score = ca.jaccard(ca.shingles("\n".join(a)), ca.shingles("\n".join(b)))
        self.assertGreaterEqual(score, ca.DUPLICATE_MAJOR)
        self.assertLess(score, ca.DUPLICATE_BLOCKING)
        out = ca.near_duplicate_findings({"x": ("\n".join(a), 5), "y": ("\n".join(b), 7)})
        self.assertEqual(list(out), ["x"])
        self.assertEqual(out["x"][0].severity, "major")
        self.assertEqual(out["x"][0].line, 5)

    def test_shingles_and_jaccard(self) -> None:
        self.assertEqual(ca.shingles("a b c d e f"), {("a", "b", "c", "d", "e"), ("b", "c", "d", "e", "f")})
        self.assertEqual(ca.shingles("too short"), set())
        self.assertEqual(ca.jaccard(set(), set()), 0.0)
        self.assertEqual(ca.jaccard({1, 2}, {2, 3}), 1 / 3)
        self.assertEqual(ca.near_duplicate_findings({"x": ("one two", 1), "y": ("one two", 1)}), {})


class TestSkillRegistryAgreement(GateTestCase):
    def test_matching_registry_entry_passes(self) -> None:
        self.assertPasses(self.skill("aipt-method-evidence-and-lineage", skill_id="S12", provenance="newly_authored"))

    def test_skill_id_mismatch_fails(self) -> None:
        self.assertFails(self.skill(skill_id="S02"), "registry_agreement", "registry/skills.json gives 'S01'")

    def test_provenance_mismatch_fails(self) -> None:
        self.assertFails(self.skill(provenance="newly_authored"), "registry_agreement", "gives 'adapt'")

    def test_unlisted_skill_fails(self) -> None:
        self.assertFails(self.skill("aipt-method-mystery", skill_id="S27"), "registry_agreement", "not listed")

    def test_without_registry_the_check_is_skipped(self) -> None:
        fx = FixtureRoot(skills_registry=False)
        self.addCleanup(fx.cleanup)
        fx.add_skill("aipt-method-mystery", make_skill("aipt-method-mystery", skill_id="S27"))
        result = fx.skills()["skills/aipt-method-mystery/SKILL.md"]
        self.assertPasses(result)
        self.assertEqual(gates(result, "registry_agreement"), [])

    def test_unauthored_registry_skills_are_listed_not_failed(self) -> None:
        self.fx.add_skill("aipt-method-discovery-interrogation", make_skill())
        results = self.fx.skills()
        self.assertEqual(len(results), len(SKILLS))
        missing = results["skills/aipt-method-evidence-and-lineage/SKILL.md"]
        self.assertEqual(missing.status, "not_authored")
        self.assertTrue(missing.ok)
        self.assertEqual(missing.findings[0].gate, "not_authored")
        report = ca.build_report(list(results.values()))
        self.assertEqual(report["summary"], {"checked": 1, "passed": 1, "failed": 0, "warnings": 0, "not_authored": 4})

    def test_directory_without_skill_file_fails(self) -> None:
        (self.fx.root / "skills" / "aipt-method-discovery-interrogation").mkdir(parents=True)
        result = self.fx.skills()["skills/aipt-method-discovery-interrogation/SKILL.md"]
        self.assertTrue(result.authored)
        self.assertFails(result, "structure", "no SKILL.md")


# --------------------------------------------------------------------------------------------------
# Agent gates
# --------------------------------------------------------------------------------------------------


class TestAgentHeadings(GateTestCase):
    def test_twelve_headings_in_order_pass(self) -> None:
        self.assertPasses(self.agent())

    def test_missing_heading_fails(self) -> None:
        headings = tuple(h for h in ca.AGENT_HEADINGS if h != "Review rubric")
        self.assertFails(self.agent(headings=headings), "structure", "missing H2 heading '## Review rubric'")

    def test_out_of_order_fails(self) -> None:
        swapped = list(ca.AGENT_HEADINGS)
        swapped[-1], swapped[-2] = swapped[-2], swapped[-1]
        self.assertFails(self.agent(headings=tuple(swapped)), "structure", "out of order")

    def test_extra_heading_fails(self) -> None:
        self.assertFails(self.agent(extra_body=["## Appendix", "", "- a", ""]), "structure", "unexpected H2 heading")

    def test_fenced_headings_in_worked_example_are_ignored(self) -> None:
        example = ["Case: Larkspur Support.", "", "```markdown", "## Objective and outcome hypothesis", "## Direction", "```"] + bullets("ex", "w", 4)
        self.assertPasses(self.agent(worked_example=example))

    def test_title_mismatch_only_warns(self) -> None:
        result = self.agent(title="Product director")
        self.assertPasses(result)
        self.assertEqual([f.severity for f in gates(result, "registry_agreement")], ["warning"])


class TestAgentLength(GateTestCase):
    def test_length_in_target_passes_cleanly(self) -> None:
        result = self.agent(lines_per_section=10)  # 154 lines
        self.assertPasses(result)
        self.assertEqual(gates(result, "length"), [])

    def test_length_outside_target_warns(self) -> None:
        low = self.agent(lines_per_section=6)  # 110 lines
        self.assertPasses(low)
        self.assertEqual([f.severity for f in gates(low, "length")], ["warning"])
        high = self.agent(lines_per_section=19)  # 253 lines
        self.assertPasses(high)
        self.assertEqual([f.severity for f in gates(high, "length")], ["warning"])

    def test_length_outside_hard_bounds_fails(self) -> None:
        self.assertFails(self.agent(lines_per_section=4), "length", "within 90-300")  # 88 lines
        self.assertFails(self.agent(lines_per_section=25), "length", "within 90-300")  # 319 lines


class TestAgentPositionRegistryAgreement(GateTestCase):
    def test_matching_position_passes_for_every_fixture_role(self) -> None:
        for role_id in AGENT_BY_ID:
            with self.subTest(role_id):
                self.assertPasses(self.agent(role_id))

    def test_each_position_field_mismatch_fails(self) -> None:
        cases = {
            "reports_to": ("discovery-manager", "Reports to"),
            "reviewed_by": ("engineering-director", "Reviewed by"),
            "write_scope": ("assigned-worktree", "Write scope"),
            "dispatch_condition": ("never; return follow-up work orders", "Dispatch condition"),
            "type": ("manager", "Type"),
            "team": ("Research and evidence", "Team"),
            "may_dispatch": ("yes", "May dispatch"),
            "acceptance_authority": ("delegation-limited", "Acceptance authority"),
            "role_id": ("product-manager", "Role id"),
        }
        for field_name, (value, label) in cases.items():
            with self.subTest(field_name):
                result = self.agent(position_overrides={field_name: value})
                self.assertFails(result, "registry_agreement", f"Position '{label}'")

    def test_team_id_is_accepted_in_place_of_team_name(self) -> None:
        self.assertPasses(self.agent(position_overrides={"team": "leadership"}))

    def test_skill_list_must_equal_registry_skill_ids(self) -> None:
        missing = self.agent(position_overrides={"shared_skills": "`aipt-method-discovery-interrogation` (S01)"})
        self.assertFails(missing, "registry_agreement", "do not equal registry skill_ids")
        extra = self.agent(position_overrides={
            "shared_skills": "`aipt-method-discovery-interrogation` (S01), `aipt-method-corpus-grounded-onboarding` (S02), "
                             "`aipt-method-research-consolidation` (S06)"
        })
        self.assertFails(extra, "registry_agreement", "do not equal registry skill_ids")
        duplicated = self.agent(position_overrides={
            "shared_skills": "`aipt-method-discovery-interrogation` (S01), `aipt-method-discovery-interrogation` (S01), "
                             "`aipt-method-corpus-grounded-onboarding` (S02)"
        })
        self.assertFails(duplicated, "registry_agreement", "more than once")

    def test_skill_name_id_pair_must_agree_with_skills_registry(self) -> None:
        wrong_pair = self.agent(position_overrides={
            "shared_skills": "`aipt-method-corpus-grounded-onboarding` (S01), `aipt-method-discovery-interrogation` (S02)"
        })
        self.assertFails(wrong_pair, "registry_agreement", "registry/skills.json gives")
        unknown = self.agent(position_overrides={
            "shared_skills": "`aipt-method-nope` (S01), `aipt-method-corpus-grounded-onboarding` (S02)"
        })
        self.assertFails(unknown, "registry_agreement", "not in registry/skills.json")

    def test_unparsable_skill_list_fails(self) -> None:
        self.assertFails(self.agent(position_overrides={"shared_skills": "S01, S02"}), "registry_agreement", "could not be parsed")

    def test_missing_position_fields_fail(self) -> None:
        result = self.agent(position=["- Role id: `product-director`"])
        failing = self.assertFails(result, "registry_agreement", "has no 'Reports to' field")
        self.assertTrue(any("Shared skills" in f.message for f in failing))

    def test_shared_skills_order_does_not_matter(self) -> None:
        reordered = "`aipt-method-corpus-grounded-onboarding` (S02), `aipt-method-discovery-interrogation` (S01)"
        self.assertPasses(self.agent(position_overrides={"shared_skills": reordered}))


class TestAgentDistinctiveRule(GateTestCase):
    def test_verbatim_first_paragraph_passes(self) -> None:
        wrapped = ["Lead discovery, research and experience managers;", "intervene only in cross-team product tradeoffs.", "", "In practice this means the trigger is tested first."]
        self.assertPasses(self.agent(distinctive=wrapped))

    def test_paraphrase_fails(self) -> None:
        result = self.agent(distinctive=["Lead the discovery, research and experience managers.", "", "More text."])
        self.assertFails(result, "registry_agreement", "Distinctive rule")

    def test_rule_not_first_paragraph_fails(self) -> None:
        entry = AGENT_BY_ID["product-director"]
        result = self.agent(distinctive=["Preamble paragraph.", "", entry["distinctive_rule"]])
        self.assertFails(result, "registry_agreement", "Distinctive rule")


class TestAgentNegativeCase(GateTestCase):
    def test_section_beginning_with_registry_text_passes(self) -> None:
        entry = AGENT_BY_ID["product-director"]
        same_paragraph = [entry["negative_test"] + " Tempting input: three concurring reviews.", "", "Wrong output: approval."]
        self.assertPasses(self.agent(negative=same_paragraph))
        own_paragraph = [entry["negative_test"], "", "Tempting input: three concurring reviews."]
        self.assertPasses(self.agent(negative=own_paragraph))

    def test_section_not_beginning_with_registry_text_fails(self) -> None:
        result = self.agent(negative=["Tempting input first.", "", AGENT_BY_ID["product-director"]["negative_test"]])
        self.assertFails(result, "registry_agreement", "Negative case")
        altered = self.agent(negative=["Must not approve a feature because three teams recommend it.", ""])
        self.assertFails(altered, "registry_agreement", "Negative case")


class TestAgentProhibitedContent(GateTestCase):
    def test_clean_body_passes(self) -> None:
        self.assertPasses(self.agent())

    def test_persona_opener_and_model_name_fail(self) -> None:
        result = self.agent(extra_body=["", "You are a world-class director who prefers Sonnet.", ""])
        failing = self.assertFails(result, "prohibited_content")
        categories = {f.message.split(":")[0] for f in failing}
        self.assertEqual(categories, {"persona_opener", "provider_or_model_name"})


class TestAgentNearDuplicates(GateTestCase):
    def test_distinct_methods_pass(self) -> None:
        for role_id in AGENT_BY_ID:
            self.fx.add_agent(role_id, make_agent(role_id))
        results = self.fx.agents()
        self.assertTrue(all(not gates(r, "near_duplicate") for r in results.values()))
        self.assertTrue(all(r.ok for r in results.values()))

    def test_identical_methods_are_blocking_and_reported_once(self) -> None:
        shared = steps("shared-method", 10)
        self.fx.add_agent("product-director", make_agent("product-director", method=shared))
        self.fx.add_agent("source-researcher", make_agent("source-researcher", method=shared))
        results = self.fx.agents()
        hits = [(p, f) for p, r in results.items() for f in gates(r, "near_duplicate")]
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0][0], "agents/product-director.md")
        self.assertEqual(hits[0][1].severity, "blocking")
        self.assertIn("agents/source-researcher.md", hits[0][1].message)


class TestAgentDirectoryStates(GateTestCase):
    def test_missing_agents_directory_lists_everything_as_not_authored(self) -> None:
        results = self.fx.agents()
        self.assertEqual(len(results), len(AGENTS))
        self.assertTrue(all(r.status == "not_authored" and r.ok for r in results.values()))
        report = ca.build_report(list(results.values()))
        self.assertEqual(report["summary"], {"checked": 0, "passed": 0, "failed": 0, "warnings": 0, "not_authored": 3})

    def test_partial_directory_mixes_checked_and_not_authored(self) -> None:
        self.fx.add_agent("source-researcher", make_agent("source-researcher"))
        (self.fx.root / "agents" / "README.md").write_text("# ignored\n", encoding="utf-8")
        results = self.fx.agents()
        self.assertEqual(results["agents/source-researcher.md"].status, "passed")
        self.assertEqual(results["agents/product-director.md"].status, "not_authored")
        self.assertNotIn("agents/README.md", results)
        self.assertEqual(ca.build_report(list(results.values()))["summary"]["not_authored"], 2)

    def test_unknown_role_file_fails(self) -> None:
        self.fx.add_agent("mystery-role", make_agent("product-director"))
        self.assertFails(self.fx.agents()["agents/mystery-role.md"], "registry_agreement", "not a role id")

    def test_missing_agent_registry_is_a_gate_error(self) -> None:
        fx = FixtureRoot(agents_registry=False)
        self.addCleanup(fx.cleanup)
        with self.assertRaises(ca.GateError):
            ca.run_agents(fx.root)


# --------------------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------------------


def run_cli(*argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = ca.main(list(argv))
    return code, out.getvalue(), err.getvalue()


class TestCli(GateTestCase):
    def test_json_report_shape_and_exit_zero_when_all_pass(self) -> None:
        self.fx.add_skill("aipt-method-discovery-interrogation", make_skill())
        code, out, err = run_cli("skills", "--root", str(self.fx.root), "--json")
        self.assertEqual(code, 0, err)
        report = json.loads(out)
        self.assertEqual(set(report), {"files", "summary"})
        self.assertEqual(report["summary"], {"checked": 1, "passed": 1, "failed": 0, "warnings": 0, "not_authored": 4})
        checked = [f for f in report["files"] if f["status"] != "not_authored"]
        self.assertEqual(checked, [{"path": "skills/aipt-method-discovery-interrogation/SKILL.md", "ok": True, "status": "passed", "findings": []}])

    def test_exit_one_and_finding_fields_when_a_file_fails(self) -> None:
        self.fx.add_agent("product-director", make_agent("product-director", position_overrides={"reports_to": "nobody"}))
        code, out, _ = run_cli("agents", "--root", str(self.fx.root), "--json")
        self.assertEqual(code, 1)
        report = json.loads(out)
        failed = next(f for f in report["files"] if f["path"] == "agents/product-director.md")
        self.assertFalse(failed["ok"])
        finding = failed["findings"][0]
        self.assertEqual(set(finding), {"gate", "severity", "message", "line"})
        self.assertEqual(finding["gate"], "registry_agreement")
        self.assertEqual(report["summary"]["failed"], 1)
        self.assertEqual(report["summary"]["not_authored"], 2)

    def test_text_output_lists_results_and_not_authored_ids(self) -> None:
        self.fx.add_agent("product-director", make_agent("product-director"))
        code, out, _ = run_cli("agents", "--root", str(self.fx.root))
        self.assertEqual(code, 0)
        self.assertIn("PASS  agents/product-director.md", out)
        self.assertIn("not authored (2): source-researcher, workflow-orchestrator", out)
        self.assertIn("agents: 1 checked, 1 passed, 0 failed, 0 warnings, 2 not authored", out)

    def test_missing_registry_exits_two(self) -> None:
        fx = FixtureRoot(agents_registry=False)
        self.addCleanup(fx.cleanup)
        code, out, err = run_cli("agents", "--root", str(fx.root))
        self.assertEqual(code, 2)
        self.assertIn("agents.json", err)
        code, out, _ = run_cli("agents", "--root", str(fx.root), "--json")
        self.assertEqual(code, 2)
        self.assertIn("error", json.loads(out))

    def test_bad_root_exits_two(self) -> None:
        code, _, err = run_cli("skills", "--root", str(self.fx.root / "nope"))
        self.assertEqual(code, 2)
        self.assertIn("not a directory", err)


if __name__ == "__main__":
    unittest.main()
