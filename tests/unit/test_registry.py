"""Unit tests for ai_product_team.registry.

Covers: a valid load of the real registry (zero hard issues, only ``not_authored`` findings); every
validation rule from contract section 4 triggered by a mutated in-memory copy (duplicate id, dangling
reports_to/reviewed_by, reports_to cycle, missing skill, unreferenced skill, unknown predicate, 63 agents,
wrong team size, manager mismatch, bad entry_skill, unknown stage role, proposal-owner without binding,
bad workflow manager, schema failure, team count, duplicate stage, dangling delegates_to); the
``not_authored`` reporting for missing role bodies and skill directories; and the derived indexes
(reporting_chain, manager_of, director_of, skill_used_by, teams, dual-keyed workflows, paths).
Mutated registries are built with ``Registry.from_data`` under ``tempfile.TemporaryDirectory()``; nothing
is written into the repository tree.
"""

from __future__ import annotations

import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from ai_product_team import registry as R
from ai_product_team.errors import NotFoundError, ValidationError

REPO = Path(__file__).resolve().parents[2]
REGISTRY_DIR = REPO / "registry"


def _load(name: str) -> dict:
    return json.loads((REGISTRY_DIR / f"{name}.json").read_text(encoding="utf-8"))


_AGENTS = _load("agents")
_SKILLS = _load("skills")
_WORKFLOWS = _load("workflows")


def _agent(doc: dict, agent_id: str) -> dict:
    for record in doc["agents"]:
        if record["id"] == agent_id:
            return record
    raise KeyError(agent_id)


def _workflow(doc: dict, workflow_id: str) -> dict:
    for record in doc["workflows"]:
        if record["id"] == workflow_id:
            return record
    raise KeyError(workflow_id)


class Base(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.agents = copy.deepcopy(_AGENTS)
        self.skills = copy.deepcopy(_SKILLS)
        self.workflows = copy.deepcopy(_WORKFLOWS)

    def build(self) -> R.Registry:
        return R.Registry.from_data(self.root, self.agents, self.skills, self.workflows)

    def hard_codes(self, registry: R.Registry) -> list[str]:
        return sorted({issue.code for issue in registry.hard_issues()})

    def issues(self, registry: R.Registry, code: str) -> list[str]:
        found = [str(issue) for issue in registry.issues() if issue.code == code]
        for text in found:
            self.assertRegex(text, r"^registry/[a-z]+\.json#/.*: \[" + code + r"\] .+$")
        return found

    def assertOnlyCodes(self, registry: R.Registry, *codes: str) -> None:
        self.assertEqual(sorted(set(codes)), self.hard_codes(registry))


class RealRegistry(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = R.Registry.load(REPO)

    def test_loads_with_no_hard_issues(self) -> None:
        self.assertEqual([], [str(i) for i in self.registry.hard_issues()])
        for text in self.registry.validate():
            self.assertIn("[not_authored]", text)
        self.registry.ensure_valid()  # must not raise

    def test_counts_and_keys(self) -> None:
        reg = self.registry
        self.assertEqual(64, len(reg.agents))
        self.assertEqual(11, len(reg.teams))
        self.assertEqual(28, len(reg.skill_ids))
        self.assertEqual(12, len(reg.workflow_ids))
        self.assertEqual(24, len(reg.workflows), "workflows are keyed by id and by name")
        self.assertIs(reg.workflows["W02"], reg.workflows["shape-feature"])
        self.assertIs(reg.skills["S12"], reg.skills["evidence-and-lineage"])
        self.assertEqual(["W%02d" % n for n in range(1, 13)], reg.workflow_ids)

    def test_records_are_frozen_dataclasses(self) -> None:
        agent = self.registry.agent("context-analyst")
        self.assertEqual("specialist", agent.type)
        self.assertEqual(("S02", "S11"), agent.skill_ids)
        with self.assertRaises(Exception):
            agent.type = "manager"  # type: ignore[misc]
        stage = self.registry.workflow("W11").stage("respond")
        self.assertEqual(R.PROPOSAL_OWNER, stage.role)
        self.assertTrue(stage.role_binding)
        review = self.registry.workflow("W01").stage("review")
        self.assertTrue(review.review)
        self.assertIsNone(review.conditional)
        self.assertEqual("consequential_or_disputed", self.registry.workflow("W01").stage("decide-or-test").conditional)

    def test_teams_and_members(self) -> None:
        teams = self.registry.teams
        self.assertEqual(4, len(teams["leadership"].members))
        self.assertIsNone(teams["leadership"].manager)
        for team_id, team in teams.items():
            if team_id != "leadership":
                self.assertEqual(6, len(team.members), team_id)
                self.assertIn(team.manager, team.members)
        self.assertEqual("adversarial-orchestrator", teams["challenge"].manager)
        self.assertEqual("assurance-director", teams["challenge"].leader)

    def test_reporting_chain(self) -> None:
        reg = self.registry
        self.assertEqual(["discovery-manager", "product-director", "human-owner"], reg.reporting_chain("context-analyst"))
        self.assertEqual(["product-director", "human-owner"], reg.reporting_chain("discovery-manager"))
        self.assertEqual(["human-owner"], reg.reporting_chain("product-director"))
        self.assertEqual(["human-owner"], reg.reporting_chain("workflow-orchestrator"))
        self.assertEqual(["adversarial-orchestrator", "assurance-director", "human-owner"], reg.reporting_chain("red-team-tester"))
        for agent_id in reg.agents:
            chain = reg.reporting_chain(agent_id)
            self.assertEqual("human-owner", chain[-1])
            self.assertNotIn(agent_id, chain)

    def test_manager_of_and_director_of(self) -> None:
        reg = self.registry
        self.assertEqual("discovery-manager", reg.manager_of("context-analyst"))
        self.assertEqual("product-director", reg.director_of("context-analyst"))
        self.assertIsNone(reg.manager_of("discovery-manager"))
        self.assertEqual("product-director", reg.director_of("discovery-manager"))
        self.assertIsNone(reg.manager_of("product-director"))
        self.assertIsNone(reg.director_of("product-director"))
        self.assertIsNone(reg.manager_of("workflow-orchestrator"))
        self.assertIsNone(reg.director_of("workflow-orchestrator"))
        self.assertEqual("adversarial-orchestrator", reg.manager_of("assumption-challenger"))
        self.assertEqual("assurance-director", reg.director_of("assumption-challenger"))
        self.assertEqual("review-manager", reg.manager_of("decision-authority"))
        for team in reg.teams.values():
            for member in team.members:
                if team.manager and member != team.manager:
                    self.assertEqual(team.manager, reg.manager_of(member), member)
                if team.leader:
                    self.assertEqual(team.leader, reg.director_of(member), member)

    def test_skill_used_by(self) -> None:
        reg = self.registry
        for skill_id in reg.skill_ids:
            expected = sorted(a["id"] for a in _AGENTS["agents"] if skill_id in a["skill_ids"])
            self.assertEqual(expected, reg.skill_used_by(skill_id), skill_id)
            self.assertTrue(expected, f"{skill_id} must be referenced")
        self.assertEqual(reg.skill_used_by("S10"), reg.skill_used_by("independent-audit"))
        self.assertEqual([], reg.skill_used_by("S99"))

    def test_paths(self) -> None:
        reg = self.registry
        self.assertEqual(REPO / "agents" / "context-analyst.md", reg.role_body_path("context-analyst"))
        self.assertEqual(REPO / "skills" / "aipt-method-discovery-interrogation", reg.skill_dir("S01"))
        self.assertEqual(reg.skill_dir("S01"), reg.skill_dir("discovery-interrogation"))
        self.assertEqual(reg.skill_dir("S01") / "SKILL.md", reg.skill_body_path("S01"))
        self.assertEqual(REPO / "workflows" / "shape-feature.md", reg.workflow_body_path("W02"))
        self.assertEqual(reg.workflow_body_path("W02"), reg.workflow_body_path("shape-feature"))
        self.assertTrue(reg.skill_dir("S01").is_dir())

    def test_unknown_ids_raise_not_found(self) -> None:
        reg = self.registry
        with self.assertRaises(NotFoundError):
            reg.agent("nobody")
        with self.assertRaises(NotFoundError):
            reg.skill("S99")
        with self.assertRaises(NotFoundError):
            reg.workflow("W99")
        with self.assertRaises(NotFoundError):
            reg.reporting_chain("nobody")
        with self.assertRaises(NotFoundError):
            reg.role_body_path("nobody")
        with self.assertRaises(NotFoundError):
            reg.skill_dir("S99")
        with self.assertRaises(NotFoundError):
            reg.workflow("W11").stage("no-such-stage")

    def test_predicates_and_budget_modes_exposed(self) -> None:
        self.assertIn("consequential_or_disputed", self.registry.predicates)
        self.assertEqual({"focused", "standard", "deep"}, set(self.registry.budget_modes))


class Loading(Base):
    def _write_registry(self) -> None:
        (self.root / "registry").mkdir()
        for name, doc in (("agents", self.agents), ("skills", self.skills), ("workflows", self.workflows)):
            (self.root / "registry" / f"{name}.json").write_text(json.dumps(doc), encoding="utf-8")

    def test_load_from_directory_matches_from_data(self) -> None:
        self._write_registry()
        loaded = R.Registry.load(self.root)
        self.assertEqual([], self.hard_codes(loaded))
        self.assertEqual(self.root, loaded.root)
        self.assertEqual(set(self.build().agents), set(loaded.agents))
        # every body is missing in the temp root: all 64 agents and 28 skills are reported as not_authored
        not_authored = self.issues(loaded, "not_authored")
        self.assertEqual(64 + 28, len(not_authored))

    def test_missing_file_raises_not_found(self) -> None:
        self._write_registry()
        (self.root / "registry" / "skills.json").unlink()
        with self.assertRaises(NotFoundError):
            R.Registry.load(self.root)

    def test_invalid_json_raises_validation_error(self) -> None:
        self._write_registry()
        (self.root / "registry" / "agents.json").write_text("{not json", encoding="utf-8")
        with self.assertRaises(ValidationError):
            R.Registry.load(self.root)

    def test_malformed_top_level_is_reported_not_raised(self) -> None:
        reg = R.Registry.from_data(self.root, {"agents": {}}, [], {"workflows": "x"})
        codes = self.hard_codes(reg)
        self.assertIn("document_shape", codes)
        self.assertEqual({}, reg.agents)
        self.assertEqual({}, reg.workflows)


class NotAuthored(Base):
    def test_reports_only_missing_bodies(self) -> None:
        (self.root / "agents").mkdir()
        for record in self.agents["agents"]:
            if record["id"] != "claim-checker":
                (self.root / "agents" / f"{record['id']}.md").write_text("# body\n", encoding="utf-8")
        for record in self.skills["skills"]:
            directory = self.root / "skills" / f"aipt-method-{record['name']}"
            directory.mkdir(parents=True)
            if record["id"] != "S07":
                (directory / "SKILL.md").write_text("---\nname: x\n---\n", encoding="utf-8")
        shutil.rmtree(self.root / "skills" / "aipt-method-status-handoff")  # S11 directory removed entirely
        reg = self.build()
        found = self.issues(reg, "not_authored")
        self.assertEqual(3, len(found), found)
        self.assertTrue(any("agents/claim-checker.md" in f for f in found))
        self.assertTrue(any("aipt-method-drift-and-regression-audit/SKILL.md" in f for f in found))
        self.assertTrue(any("aipt-method-status-handoff/ is missing" in f for f in found))
        self.assertEqual([], self.hard_codes(reg))
        reg.ensure_valid()

    def test_skill_dir_template_falls_back_without_naming(self) -> None:
        del self.skills["naming"]
        reg = self.build()
        self.assertEqual(self.root / "skills" / "discovery-interrogation", reg.skill_dir("S01"))
        self.assertEqual("SKILL.md", reg.skill_body_name)


class ValidationRules(Base):
    def test_unmutated_copy_has_no_hard_issues(self) -> None:
        self.assertEqual([], self.hard_codes(self.build()))

    def test_duplicate_agent_id(self) -> None:
        clone = copy.deepcopy(_agent(self.agents, "claim-checker"))
        clone["number"] = 999
        clone["native_name"] = "aipt-claim-checker-2"
        self.agents["agents"].append(clone)
        reg = self.build()
        found = self.issues(reg, "duplicate_id")
        self.assertEqual(1, len(found))
        self.assertIn("'claim-checker'", found[0])
        self.assertIn("#/agents/64/id", found[0])
        self.assertIn("agent_count", self.hard_codes(reg))

    def test_duplicate_skill_and_workflow_ids(self) -> None:
        self.skills["skills"].append(dict(self.skills["skills"][0]))
        self.workflows["workflows"].append(copy.deepcopy(self.workflows["workflows"][0]))
        reg = self.build()
        found = self.issues(reg, "duplicate_id")
        self.assertTrue(any("skills.json#/skills/28/id" in f for f in found))
        self.assertTrue(any("workflows.json#/workflows/12/id" in f for f in found))
        self.assertTrue(self.issues(reg, "duplicate_name"))

    def test_duplicate_stage_id(self) -> None:
        stages = _workflow(self.workflows, "W02")["stages"]
        stages.append(dict(stages[0]))
        self.assertOnlyCodes(self.build(), "duplicate_stage")

    def test_dangling_reports_to(self) -> None:
        _agent(self.agents, "claim-checker")["reports_to"] = "ghost-manager"
        reg = self.build()
        found = self.issues(reg, "dangling_reference")
        self.assertEqual(1, len(found))
        self.assertIn("reports_to 'ghost-manager'", found[0])
        self.assertIn("manager_mismatch", self.hard_codes(reg))
        with self.assertRaises(ValidationError):
            reg.reporting_chain("claim-checker")

    def test_dangling_reviewed_by(self) -> None:
        _agent(self.agents, "claim-checker")["reviewed_by"] = "ghost-reviewer"
        reg = self.build()
        found = self.issues(reg, "dangling_reference")
        self.assertEqual(1, len(found))
        self.assertIn("reviewed_by 'ghost-reviewer'", found[0])
        self.assertOnlyCodes(reg, "dangling_reference")

    def test_human_owner_is_a_valid_reference(self) -> None:
        _agent(self.agents, "claim-checker")["reviewed_by"] = "human-owner"
        self.assertEqual([], self.hard_codes(self.build()))

    def test_reports_to_cycle(self) -> None:
        # research-manager -> product-director -> human-owner becomes research-manager -> claim-checker -> research-manager
        _agent(self.agents, "research-manager")["reports_to"] = "claim-checker"
        reg = self.build()
        found = self.issues(reg, "reports_to_cycle")
        self.assertEqual(1, len(found), found)
        self.assertIn("claim-checker -> research-manager -> claim-checker", found[0])
        with self.assertRaises(ValidationError) as ctx:
            reg.reporting_chain("evidence-curator")
        self.assertIn("cycle", str(ctx.exception))
        self.assertIsNone(reg.director_of("claim-checker"))
        self.assertEqual("research-manager", reg.manager_of("claim-checker"))

    def test_self_reporting_is_a_cycle(self) -> None:
        _agent(self.agents, "product-director")["reports_to"] = "product-director"
        reg = self.build()
        found = self.issues(reg, "reports_to_cycle")
        self.assertEqual(1, len(found), found)
        self.assertIn("product-director -> product-director", found[0])

    def test_missing_skill(self) -> None:
        _agent(self.agents, "claim-checker")["skill_ids"].append("S28")  # valid pattern, exists -> fine
        _agent(self.agents, "claim-checker")["skill_ids"].append("S27")
        self.skills["skills"] = [s for s in self.skills["skills"] if s["id"] != "S27"]
        reg = self.build()
        found = self.issues(reg, "missing_skill")
        self.assertTrue(found)
        self.assertTrue(all("'S27'" in f for f in found))
        self.assertNotIn("unreferenced_skill", self.hard_codes(reg))

    def test_unreferenced_skill(self) -> None:
        for record in self.agents["agents"]:
            record["skill_ids"] = [s for s in record["skill_ids"] if s != "S10"]
        reg = self.build()
        found = self.issues(reg, "unreferenced_skill")
        self.assertEqual(1, len(found))
        self.assertIn("'S10'", found[0])
        self.assertEqual([], reg.skill_used_by("S10"))

    def test_unknown_predicate(self) -> None:
        _workflow(self.workflows, "W01")["stages"][4]["conditional"] = "moon_is_full"
        reg = self.build()
        found = self.issues(reg, "unknown_predicate")
        self.assertEqual(1, len(found))
        self.assertIn("'moon_is_full'", found[0])
        self.assertIn("workflows.json#/workflows/0/stages/4/conditional", found[0])
        self.assertOnlyCodes(reg, "unknown_predicate")

    def test_sixty_three_agents(self) -> None:
        removed = self.agents["agents"].pop()  # learning-steward
        reg = self.build()
        found = self.issues(reg, "agent_count")
        self.assertEqual(1, len(found))
        self.assertIn("found 63", found[0])
        self.assertIn("team_size", self.hard_codes(reg))
        self.assertEqual(63, len(reg.agents))
        self.assertNotIn(removed["id"], reg.agents)

    def test_sixty_five_agents(self) -> None:
        extra = copy.deepcopy(_agent(self.agents, "claim-checker"))
        extra.update({"id": "claim-checker-two", "native_name": "aipt-claim-checker-two", "number": 65})
        self.agents["agents"].append(extra)
        reg = self.build()
        self.assertIn("found 65", self.issues(reg, "agent_count")[0])

    def test_wrong_team_size(self) -> None:
        _agent(self.agents, "claim-checker")["team"] = "discovery"
        reg = self.build()
        found = self.issues(reg, "team_size")
        self.assertEqual(2, len(found), found)
        self.assertTrue(any("'discovery' must have 6 members, found 7" in f for f in found))
        self.assertTrue(any("'research' must have 6 members, found 5" in f for f in found))
        self.assertIn("manager_mismatch", self.hard_codes(reg))  # still reports to research-manager

    def test_leadership_team_size(self) -> None:
        _agent(self.agents, "claim-checker")["team"] = "leadership"
        found = self.issues(self.build(), "team_size")
        self.assertTrue(any("'leadership' must have 4 members, found 5" in f for f in found))

    def test_unknown_team(self) -> None:
        _agent(self.agents, "claim-checker")["team"] = "marketing"
        reg = self.build()
        self.assertIn("'marketing'", self.issues(reg, "unknown_team")[0])

    def test_team_count(self) -> None:
        self.agents["teams"] = [t for t in self.agents["teams"] if t["id"] != "research"]
        reg = self.build()
        self.assertIn("found 10", self.issues(reg, "team_count")[0])
        self.assertEqual(6, len(self.issues(reg, "unknown_team")))

    def test_manager_mismatch_member_reports_elsewhere(self) -> None:
        _agent(self.agents, "claim-checker")["reports_to"] = "discovery-manager"
        reg = self.build()
        found = self.issues(reg, "manager_mismatch")
        self.assertEqual(1, len(found), found)
        self.assertIn("'claim-checker' is in team 'research' but reports to 'discovery-manager', expected manager 'research-manager'", found[0])
        self.assertOnlyCodes(reg, "manager_mismatch")

    def test_manager_mismatch_team_declares_other_manager(self) -> None:
        for team in self.agents["teams"]:
            if team["id"] == "research":
                team["manager"] = "discovery-manager"
        reg = self.build()
        found = self.issues(reg, "manager_mismatch")
        self.assertTrue(any("belongs to team 'discovery', not 'research'" in f for f in found))

    def test_manager_must_report_to_team_leader(self) -> None:
        _agent(self.agents, "research-manager")["reports_to"] = "engineering-director"
        found = self.issues(self.build(), "manager_mismatch")
        self.assertTrue(any("team manager 'research-manager' reports to 'engineering-director', expected team leader 'product-director'" in f for f in found))

    def test_team_manager_must_be_manager_type(self) -> None:
        _agent(self.agents, "research-manager")["type"] = "specialist"
        reg = self.build()
        found = self.issues(reg, "bad_manager")
        self.assertTrue(any("teams/2/manager" in f for f in found), found)

    def test_bad_entry_skill(self) -> None:
        _workflow(self.workflows, "W02")["entry_skill"] = "aipt-shape-features"
        reg = self.build()
        found = self.issues(reg, "bad_entry_skill")
        self.assertEqual(1, len(found))
        self.assertIn("must be 'aipt-shape-feature', found 'aipt-shape-features'", found[0])
        self.assertOnlyCodes(reg, "bad_entry_skill")

    def test_workflow_manager_must_be_manager_type(self) -> None:
        _workflow(self.workflows, "W02")["manager"] = "claim-checker"
        reg = self.build()
        found = self.issues(reg, "bad_manager")
        self.assertEqual(1, len(found))
        self.assertIn("'claim-checker' has type 'reviewer'", found[0])
        _workflow(self.workflows, "W03")["manager"] = "nobody"
        reg = self.build()
        self.assertTrue(any("workflows/2/manager" in f for f in self.issues(reg, "dangling_reference")))

    def test_adversarial_orchestrator_may_manage(self) -> None:
        _workflow(self.workflows, "W11")["manager"] = "adversarial-orchestrator"
        self.assertEqual([], self.hard_codes(self.build()))

    def test_unknown_stage_role(self) -> None:
        _workflow(self.workflows, "W02")["stages"][0]["role"] = "ghost-analyst"
        reg = self.build()
        found = self.issues(reg, "unknown_role")
        self.assertEqual(1, len(found))
        self.assertIn("workflows/1/stages/0/role", found[0])

    def test_proposal_owner_requires_role_binding(self) -> None:
        stage = _workflow(self.workflows, "W11")["stages"][4]
        self.assertEqual("proposal-owner", stage["role"])
        del stage["role_binding"]
        reg = self.build()
        found = self.issues(reg, "unknown_role")
        self.assertEqual(1, len(found))
        self.assertIn("requires a non-empty role_binding", found[0])

    def test_unknown_conditional_specialist(self) -> None:
        _workflow(self.workflows, "W02")["conditional_specialists"].append("ghost-specialist")
        reg = self.build()
        found = self.issues(reg, "unknown_role")
        self.assertEqual(1, len(found))
        self.assertIn("conditional_specialists/4", found[0])

    def test_conditional_specialist_may_be_human_owner(self) -> None:
        _workflow(self.workflows, "W02")["conditional_specialists"].append("human-owner")
        self.assertEqual([], self.hard_codes(self.build()))

    def test_dangling_delegates_to(self) -> None:
        _workflow(self.workflows, "W01")["stages"][4]["delegates_to"] = "W99"
        found = self.issues(self.build(), "dangling_reference")
        self.assertTrue(any("delegates_to 'W99'" in f for f in found))

    def test_schema_failure_per_record(self) -> None:
        _agent(self.agents, "claim-checker")["type"] = "wizard"
        del _agent(self.agents, "context-analyst")["negative_test"]
        self.skills["skills"][0]["provenance"]["status"] = "maybe"
        _workflow(self.workflows, "W02")["min_risk"] = "R9"
        reg = self.build()
        found = self.issues(reg, "schema")
        self.assertTrue(any("agents.json#/agents/13/type" in f for f in found), found)
        self.assertTrue(any("agents.json#/agents/5/negative_test" in f for f in found), found)
        self.assertTrue(any("skills.json#/skills/0/provenance/status" in f for f in found), found)
        self.assertTrue(any("workflows.json#/workflows/1/min_risk" in f for f in found), found)

    def test_dispatch_flag_and_native_name(self) -> None:
        _agent(self.agents, "claim-checker")["may_dispatch"] = True
        _agent(self.agents, "context-analyst")["native_name"] = "aipt-context"
        reg = self.build()
        self.assertEqual(1, len(self.issues(reg, "dispatch_flag")))
        self.assertEqual(1, len(self.issues(reg, "native_name_mismatch")))

    def test_ensure_valid_raises_with_every_hard_issue(self) -> None:
        _agent(self.agents, "claim-checker")["reports_to"] = "ghost"
        _workflow(self.workflows, "W02")["entry_skill"] = "wrong"
        reg = self.build()
        with self.assertRaises(ValidationError) as ctx:
            reg.ensure_valid()
        codes = ctx.exception.details["codes"]
        self.assertIn("dangling_reference", codes)
        self.assertIn("bad_entry_skill", codes)
        self.assertNotIn("not_authored", codes)
        self.assertEqual(len(reg.hard_issues()), len(ctx.exception.errors))

    def test_validate_strings_are_deterministic(self) -> None:
        reg = self.build()
        self.assertEqual(reg.validate(), reg.validate())
        self.assertEqual(reg.validate(), self.build().validate())


if __name__ == "__main__":
    unittest.main()
