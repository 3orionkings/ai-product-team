"""Contract tests for schemas/*.schema.json against docs/architecture/controller-contracts.md section 3.

Asserts: every listed schema exists and loads with the fixed header; required fields match the table; every
enumeration (in the common catalogue and every inlined copy) equals the contract list; every registry record
validates against its registry-* schema; and a minimal valid fixture per record schema passes while each
missing required field and any extra top-level key is rejected.
"""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from ai_product_team import validation as V

REPO = Path(__file__).resolve().parents[2]
SCHEMAS_DIR = REPO / "schemas"
REGISTRY_DIR = REPO / "registry"
DRAFT = "https://json-schema.org/draft/2020-12/schema"

CONTRACT_ENUMS: dict[str, list[str]] = {
    "role_type": ["leader", "orchestrator", "manager", "specialist", "steward", "reviewer", "builder", "executor", "adversarial_orchestrator", "challenger", "judge", "decision_maker", "auditor"],
    "write_scope": ["proposal-only", "assigned-worktree", "verification-sandbox"],
    "risk_tier": ["R0", "R1", "R2", "R3"],
    "budget_mode": ["focused", "standard", "deep"],
    "execution_mode": ["native", "sequential", "manual_handoff", "fixture_replay"],
    "observation_source": ["native", "controller", "agent_reported"],
    "run_state": ["created", "scoped", "planned", "executing", "reviewing", "completed", "needs_input", "blocked", "rework", "paused", "cancelled", "failed"],
    "task_state": ["planned", "ready", "admitted", "running", "submitted", "reviewed", "accepted", "blocked", "needs_input", "rejected", "cancelled", "failed"],
    "response_status": ["complete", "needs_input", "blocked", "failed", "partial", "out_of_scope"],
    "node_kind": ["source", "claim", "requirement", "proposal", "decision", "artifact", "validation", "challenge", "review", "approval"],
    "claim_type": ["fact", "hypothesis", "observation"],
    "claim_status": ["proposed", "supported", "contested", "unsupported", "superseded"],
    "decision_status": ["proposed", "under_review", "accepted", "rejected", "deferred", "human_required", "review_required", "superseded"],
    "artifact_status": ["proposed", "implemented_not_verified", "verified_for_scope", "changes_required", "revalidation_required", "archived"],
    "validation_result": ["passed", "failed", "blocked", "not_run"],
    "applicability": ["current", "historical", "invalidated", "unestablished"],
    "requirement_status": ["proposed", "approved", "retired", "superseded"],
    "relation": ["supports", "contradicts", "implements", "verifies", "derived_from", "supersedes", "depends_on"],
    "impact_policy": ["review", "invalidate_applicability", "none"],
    "edge_status": ["proposed", "accepted", "rejected"],
    "review_result": ["ready", "revise", "blocked", "escalate", "pass", "fail"],
    "independence": ["verified", "unverified", "conflict"],
    "assurance_level": ["recorded", "validated_structure", "observed_execution", "reviewed_semantics", "enforced_by_host"],
    "challenge_state": ["open", "answered", "upheld", "withdrawn", "unresolved"],
    "ruling_outcome": ["option_acceptable", "option_rejected", "insufficient_evidence", "unresolved", "next_test_required"],
}

# Enumerations the section 3 table defines inline for one schema.
LOCAL_ENUMS: dict[str, list[str]] = {
    "locator_type": ["local", "public", "supplied"],
    "confidence_label": ["low", "medium", "high", "unknown"],
    "decision_outcome": ["accepted", "rejected", "deferred", "human_required"],
    "authority_basis_kind": ["delegation", "human_input"],
    "access_classification": ["public", "private", "synthetic"],
    "evidence_sufficiency": ["sufficient", "insufficient", "not_assessed"],
    "granted_by": ["human-owner", "delegation"],
    "provenance_channel": ["cli", "host_user_input", "file"],
    "snapshot_kind": ["git", "manifest"],
    "provenance_status": ["reuse", "adapt", "reference_only", "newly_authored", "hold", "exclude", "unresolved"],
    "route_confidence": ["exact", "keyword", "fallback"],
    "action_kind": ["analysis", "proposed_change", "local_execution", "external_action"],
}

REQUIRED: dict[str, list[str]] = {
    "registry-agent": ["number", "id", "native_name", "name", "type", "team", "reports_to", "reviewed_by", "description", "skill_ids", "input_contract", "output_contract", "distinctive_rule", "negative_test", "write_scope", "may_dispatch", "acceptance_authority", "status", "dispatch_condition"],
    "registry-skill": ["id", "name", "title", "summary", "provenance"],
    "registry-workflow": ["id", "name", "entry_skill", "title", "manager", "min_risk", "core_cross_host", "inputs", "outputs", "stages", "conditional_specialists", "acceptance", "fixture"],
    "task-envelope": ["case_id", "run_id", "task_id", "role_id", "role_version", "objective", "deliverable", "input_refs", "context_brief", "allowed_sources", "write_scope", "output_paths", "prohibited_actions", "risk_tier", "budget", "expected_output_schema", "acceptance_criteria", "review_assignment", "capabilities", "stop_conditions", "escalation_to", "return_instruction"],
    "agent-response": ["task_id", "role_id", "status", "summary", "input_versions", "findings", "evidence_refs", "artifact_refs", "proposed_links", "observed_checks", "uncertainties", "requested_followups", "scope_violations", "actual_execution_metadata"],
    "source": ["id", "title", "locator", "locator_type", "observed_at", "content_hash", "access_scope", "authority_type", "limitations"],
    "claim": ["statement", "claim_type", "status", "supporting_refs", "contrary_refs", "confidence_label", "assessed_by"],
    "requirement": ["statement", "owner", "acceptance_criteria", "protected", "originating_refs", "status"],
    "proposal": ["title", "options", "recommended_option", "assumptions", "evidence_refs", "constraints", "unresolved_questions", "target_refs", "author_role", "requested_authority"],
    "decision": ["proposal_version_id", "outcome", "selected_option", "criteria", "rationale", "dissent", "authority_basis", "revisit_conditions", "status"],
    "artifact": ["kind", "path", "content_hash", "producer_role", "producer_task", "write_scope", "implements_refs", "status", "access_classification"],
    "validation": ["method", "target_refs", "receipt_id", "result", "rubric", "coverage", "applicability"],
    "challenge": ["contested_ref", "premise", "counterevidence_or_gap", "consequence", "resolving_test", "proposer_role", "round", "state"],
    "review": ["reviewed_refs", "reviewer_role", "reviewer_session", "findings", "evidence_sufficiency", "result", "conflict_check", "unresolved"],
    "approval": ["granted_by", "scope", "allowed_decisions", "allowed_actions", "bound_version_id", "limits", "expires_at", "revoked", "provenance"],
    "event": ["id", "seq", "case_id", "type", "actor_role", "actor_task", "expected_state_version", "payload_refs", "created_at", "idempotency_key"],
    "receipt": ["id", "task_id", "command", "cwd", "snapshot", "started_at", "ended_at", "exit_status", "timed_out", "cancelled", "stdout_path", "stderr_path", "observation_source", "test_ids", "redactions_applied"],
    "route-plan": ["request", "workflow_id", "mode", "risk_tier", "selected_roles", "omitted_roles", "stages", "predicates", "budget_check", "explicit"],
    "work-order": ["id", "task_id", "role_id", "envelope"],
    "policy-authority": ["roles", "risk_tiers"],
}
RECORD_SCHEMAS = list(REQUIRED)
ALL_SCHEMAS = RECORD_SCHEMAS + ["common"]

# Where each contract enum must appear inline: (schema, schema-pointer, enum name).
ENUM_SITES: list[tuple[str, str, str]] = [
    ("registry-agent", "/properties/type", "role_type"),
    ("registry-agent", "/properties/write_scope", "write_scope"),
    ("registry-workflow", "/properties/min_risk", "risk_tier"),
    ("registry-workflow", "/$defs/stage/properties/write_scope", "write_scope"),
    ("registry-workflow", "/$defs/stage/properties/may_return/items", "response_status"),
    ("task-envelope", "/properties/write_scope", "write_scope"),
    ("task-envelope", "/properties/risk_tier", "risk_tier"),
    ("task-envelope", "/$defs/input_ref/properties/kind", "node_kind"),
    ("task-envelope", "/$defs/capabilities/properties/execution_mode", "execution_mode"),
    ("agent-response", "/properties/status", "response_status"),
    ("agent-response", "/$defs/execution_metadata/properties/execution_mode", "execution_mode"),
    ("agent-response", "/$defs/proposed_link/properties/relation", "relation"),
    ("agent-response", "/$defs/proposed_link/properties/impact_policy", "impact_policy"),
    ("claim", "/properties/claim_type", "claim_type"),
    ("claim", "/properties/status", "claim_status"),
    ("requirement", "/properties/status", "requirement_status"),
    ("proposal", "/properties/requested_authority", "risk_tier"),
    ("decision", "/properties/status", "decision_status"),
    ("decision", "/properties/requested_authority", "risk_tier"),
    ("artifact", "/properties/write_scope", "write_scope"),
    ("artifact", "/properties/status", "artifact_status"),
    ("validation", "/properties/result", "validation_result"),
    ("validation", "/properties/applicability", "applicability"),
    ("challenge", "/properties/state", "challenge_state"),
    ("review", "/properties/result", "review_result"),
    ("review", "/properties/conflict_check", "independence"),
    ("event", "/properties/type", None),
    ("receipt", "/properties/observation_source", "observation_source"),
    ("route-plan", "/properties/mode", "budget_mode"),
    ("route-plan", "/properties/risk_tier", "risk_tier"),
    ("work-order", "/$defs/task_envelope/properties/write_scope", "write_scope"),
    ("work-order", "/$defs/task_envelope/properties/risk_tier", "risk_tier"),
]


def _at(schema: dict, pointer: str):
    node = schema
    for token in pointer.strip("/").split("/"):
        node = node[token]
    return node


def _enums(node, pointer: str = ""):
    """Yield (pointer, enum-list) for every enum keyword in a schema, structure-aware."""
    if isinstance(node, dict):
        for key, value in node.items():
            child = f"{pointer}/{key}"
            if key == "enum":
                yield child, value
            elif key in ("properties", "$defs") and isinstance(value, dict):
                for name, sub in value.items():
                    yield from _enums(sub, f"{child}/{name}")
            elif key in ("items", "not", "additionalProperties"):
                yield from _enums(value, child)
            elif key in ("oneOf", "anyOf", "allOf") and isinstance(value, list):
                for index, sub in enumerate(value):
                    yield from _enums(sub, f"{child}/{index}")


def _registry(name: str) -> dict:
    return json.loads((REGISTRY_DIR / f"{name}.json").read_text(encoding="utf-8"))


class SchemaFiles(unittest.TestCase):
    def test_exactly_the_listed_schema_files_exist(self):
        on_disk = sorted(p.name[: -len(V.SCHEMA_SUFFIX)] for p in SCHEMAS_DIR.glob(f"*{V.SCHEMA_SUFFIX}"))
        self.assertEqual(sorted(ALL_SCHEMAS), on_disk)

    def test_every_schema_loads_with_contract_header(self):
        for name in ALL_SCHEMAS:
            with self.subTest(schema=name):
                schema = V.load_schema(name)
                self.assertEqual(DRAFT, schema["$schema"])
                self.assertEqual(f"https://aipt.local/schemas/{name}", schema["$id"])
                self.assertTrue(schema.get("title"))
                self.assertTrue(schema.get("description"))
                self.assertEqual([], V.schema_keyword_errors(schema))

    def test_record_schemas_are_closed_objects(self):
        for name in RECORD_SCHEMAS:
            with self.subTest(schema=name):
                schema = V.load_schema(name)
                self.assertEqual("object", schema["type"])
                self.assertIs(False, schema["additionalProperties"])
                self.assertTrue(schema["required"])
                self.assertTrue(set(schema["required"]) <= set(schema["properties"]), "required fields must be declared properties")

    def test_required_fields_match_contract_table(self):
        for name, required in REQUIRED.items():
            with self.subTest(schema=name):
                self.assertEqual(required, V.load_schema(name)["required"])

    def test_schema_ids_are_unique(self):
        ids = [V.load_schema(name)["$id"] for name in ALL_SCHEMAS]
        self.assertEqual(len(ids), len(set(ids)))


class Enumerations(unittest.TestCase):
    def test_common_catalogue_holds_every_contract_enum_exactly(self):
        defs = V.load_schema("common")["$defs"]
        self.assertEqual(sorted(CONTRACT_ENUMS), sorted(defs))
        for name, values in CONTRACT_ENUMS.items():
            with self.subTest(enum=name):
                self.assertEqual({"type": "string", "enum": values}, defs[name])

    def test_every_inlined_enum_is_a_contract_or_local_list(self):
        known = {tuple(v): k for k, v in {**CONTRACT_ENUMS, **LOCAL_ENUMS}.items()}
        seen_contract: set[str] = set()
        for name in RECORD_SCHEMAS:
            for pointer, values in _enums(V.load_schema(name)):
                with self.subTest(schema=name, pointer=pointer):
                    self.assertIsInstance(values, list)
                    self.assertIn(tuple(values), known, f"{name}{pointer} enum {values!r} matches no contract list")
                    if known[tuple(values)] in CONTRACT_ENUMS:
                        seen_contract.add(known[tuple(values)])
        expected_inline = {site[2] for site in ENUM_SITES if site[2]}
        self.assertEqual(expected_inline, seen_contract & expected_inline)

    def test_enum_sites_carry_the_exact_contract_list(self):
        for schema_name, pointer, enum_name in ENUM_SITES:
            if enum_name is None:
                continue
            with self.subTest(schema=schema_name, pointer=pointer):
                node = _at(V.load_schema(schema_name), pointer)
                self.assertEqual(CONTRACT_ENUMS[enum_name], node["enum"])

    def test_local_enums_sit_where_the_table_puts_them(self):
        sites = {
            ("source", "/properties/locator_type"): "locator_type",
            ("claim", "/properties/confidence_label"): "confidence_label",
            ("decision", "/properties/outcome"): "decision_outcome",
            ("decision", "/properties/authority_basis/properties/kind"): "authority_basis_kind",
            ("artifact", "/properties/access_classification"): "access_classification",
            ("review", "/properties/evidence_sufficiency"): "evidence_sufficiency",
            ("approval", "/properties/granted_by"): "granted_by",
            ("approval", "/properties/provenance/properties/channel"): "provenance_channel",
            ("receipt", "/$defs/snapshot/properties/kind"): "snapshot_kind",
            ("registry-skill", "/properties/provenance/properties/status"): "provenance_status",
        }
        for (schema_name, pointer), enum_name in sites.items():
            with self.subTest(schema=schema_name, pointer=pointer):
                self.assertEqual(LOCAL_ENUMS[enum_name], _at(V.load_schema(schema_name), pointer)["enum"])


class RegistrySchemas(unittest.TestCase):
    def test_registry_agent_patterns(self):
        schema = V.load_schema("registry-agent")
        self.assertEqual("^[a-z][a-z0-9-]*$", schema["properties"]["id"]["pattern"])
        self.assertEqual("^S(0[1-9]|1[0-9]|2[0-8])$", schema["properties"]["skill_ids"]["items"]["pattern"])
        self.assertEqual("integer", schema["properties"]["number"]["type"])
        self.assertEqual("boolean", schema["properties"]["may_dispatch"]["type"])

    def test_registry_skill_name_constraints(self):
        name = V.load_schema("registry-skill")["properties"]["name"]
        self.assertEqual("^[a-z0-9]+(-[a-z0-9]+)*$", name["pattern"])
        self.assertEqual(52, name["maxLength"])
        self.assertEqual(64, len("aipt-method-") + 52)

    def test_registry_workflow_stage_shape(self):
        stage = V.load_schema("registry-workflow")["$defs"]["stage"]
        self.assertEqual(["id", "title", "role", "work", "artifact"], stage["required"])
        self.assertIs(False, stage["additionalProperties"])
        optional = {"conditional", "review", "independence_required", "write_scope", "may_return", "delegates_to", "role_binding"}
        self.assertTrue(optional <= set(stage["properties"]), optional - set(stage["properties"]))
        self.assertEqual({"$ref": "#/$defs/stage"}, V.load_schema("registry-workflow")["properties"]["stages"]["items"])

    def test_registry_documents_have_loose_top_level_shape(self):
        for file_name, list_key in (("agents", "agents"), ("skills", "skills"), ("workflows", "workflows")):
            with self.subTest(file=file_name):
                doc = _registry(file_name)
                self.assertIsInstance(doc, dict)
                self.assertIsInstance(doc["schema_version"], str)
                self.assertEqual("ai-product-team", doc["package"])
                self.assertIsInstance(doc.get("reconstruction_note"), str)
                records = doc[list_key]
                self.assertIsInstance(records, list)
                self.assertTrue(records)
                self.assertTrue(all(isinstance(r, dict) for r in records))
        self.assertIsInstance(_registry("agents")["teams"], list)
        self.assertIsInstance(_registry("workflows")["predicates"], dict)

    def test_every_registry_record_validates(self):
        for file_name, list_key, schema_name in (("agents", "agents", "registry-agent"), ("skills", "skills", "registry-skill"), ("workflows", "workflows", "registry-workflow")):
            schema = V.load_schema(schema_name)
            records = _registry(file_name)[list_key]
            for record in records:
                with self.subTest(file=file_name, id=record.get("id")):
                    self.assertEqual([], V.validate(record, schema))
                    V.ensure_valid(record, schema_name)

    def test_workflow_stage_predicates_are_declared_in_registry(self):
        doc = _registry("workflows")
        declared = set(doc["predicates"])
        for workflow in doc["workflows"]:
            for stage in workflow["stages"]:
                if "conditional" in stage:
                    self.assertIn(stage["conditional"], declared, f"{workflow['id']}/{stage['id']}")

    def test_mutated_registry_records_are_rejected(self):
        agent = copy.deepcopy(_registry("agents")["agents"][0])
        agent["extra"] = 1
        self.assertEqual(["/extra: additional property 'extra' is not allowed"], V.validate(agent, V.load_schema("registry-agent")))
        agent = copy.deepcopy(_registry("agents")["agents"][0])
        agent["type"] = "boss"
        self.assertEqual([f"/type: 'boss' is not one of {CONTRACT_ENUMS['role_type']!r}"], V.validate(agent, V.load_schema("registry-agent")))
        agent["skill_ids"] = ["S29", "S01", "S01"]
        errors = V.validate(agent, V.load_schema("registry-agent"))
        self.assertTrue(any("/skill_ids/0: 'S29' does not match pattern" in e for e in errors))
        self.assertTrue(any("/skill_ids: array items are not unique" in e for e in errors))

        skill = copy.deepcopy(_registry("skills")["skills"][0])
        skill["name"] = "a" * 53
        self.assertTrue(any("longer than maxLength 52" in e for e in V.validate(skill, V.load_schema("registry-skill"))))
        skill["name"] = "Bad_Name"
        self.assertTrue(any("/name:" in e and "pattern" in e for e in V.validate(skill, V.load_schema("registry-skill"))))
        skill["provenance"]["status"] = "copied"
        self.assertTrue(any("/provenance/status: 'copied' is not one of" in e for e in V.validate(skill, V.load_schema("registry-skill"))))

        workflow = copy.deepcopy(_registry("workflows")["workflows"][0])
        workflow["stages"][0]["conditional"] = "Not A Predicate"
        workflow["stages"][1]["review"] = "yes"
        workflow["min_risk"] = "R9"
        errors = V.validate(workflow, V.load_schema("registry-workflow"))
        self.assertTrue(any(e.startswith("/stages/0/conditional: 'Not A Predicate' does not match pattern") for e in errors))
        self.assertIn("/stages/1/review: 'yes' is not of type 'boolean'", errors)
        self.assertIn(f"/min_risk: 'R9' is not one of {CONTRACT_ENUMS['risk_tier']!r}", errors)


TS = "2026-10-16T20:54:00.000Z"
ENVELOPE = {
    "case_id": "case_demo", "run_id": "run_demo", "task_id": "task_demo", "role_id": "context-analyst", "role_version": "0.1.0",
    "objective": "Summarise the supplied design.", "deliverable": "context-brief.md",
    "input_refs": [{"node_id": "node_1", "version_id": "ver_1", "kind": "source"}],
    "context_brief": "One supplied design document.", "allowed_sources": ["src_1"], "write_scope": "proposal-only",
    "output_paths": ["proposals/"], "prohibited_actions": ["publish", "deploy", "send"], "risk_tier": "R0",
    "budget": {"max_steps": 12, "timeout_s": 600}, "expected_output_schema": "agent-response",
    "acceptance_criteria": ["Separates stated facts from inferences."], "review_assignment": None,
    "capabilities": {"tools": ["read"], "unavailable": ["network"], "execution_mode": "native"},
    "stop_conditions": ["missing source"], "escalation_to": "discovery-manager", "return_instruction": "Return an agent-response.",
}
FIXTURES: dict[str, dict] = {
    "task-envelope": ENVELOPE,
    "agent-response": {
        "task_id": "task_demo", "role_id": "context-analyst", "status": "complete", "summary": "Brief produced.",
        "input_versions": ["ver_1"], "findings": ["The design assumes drafts only.", {"statement": "No send path.", "refs": ["ver_1"]}],
        "evidence_refs": ["ver_1"], "artifact_refs": [{"kind": "context-brief.md", "path": "proposals/context-brief.md"}],
        "proposed_links": [{"from_version": "ver_2", "to_version": "ver_1", "relation": "depends_on", "impact_policy": "review", "reason": "derived from the design"}],
        "observed_checks": [{"command": ["python3", "-m", "unittest"], "claimed_exit_status": 0}, {"command": "ls", "receipt_id": "rcpt_1"}],
        "uncertainties": [], "requested_followups": [], "scope_violations": [],
        "actual_execution_metadata": {"execution_mode": "native", "native_child_id": "child-1", "host": "codex", "started_at": TS, "ended_at": None},
    },
    "source": {"id": "src_1", "title": "Design doc", "locator": "docs/design.md", "locator_type": "local", "observed_at": TS, "content_hash": "ab" * 32, "access_scope": "private", "authority_type": "primary", "limitations": ["Draft, undated."]},
    "claim": {"statement": "Drafts only.", "claim_type": "fact", "status": "supported", "supporting_refs": ["ver_1"], "contrary_refs": [], "confidence_label": "high", "assessed_by": "claim-checker"},
    "requirement": {"statement": "No automatic sending.", "owner": "human-owner", "acceptance_criteria": ["Send path absent."], "protected": True, "originating_refs": ["ver_1"], "status": "approved"},
    "proposal": {"title": "Assistance options", "options": [{"id": "A", "summary": "Draft assistance"}, {"id": "B", "summary": "Rules only"}], "recommended_option": "A", "assumptions": ["Volume stays flat."], "evidence_refs": ["ver_1"], "constraints": ["No send"], "unresolved_questions": [], "target_refs": [], "author_role": "opportunity-analyst", "requested_authority": "R1"},
    "decision": {"proposal_version_id": "ver_9", "outcome": "accepted", "selected_option": "A", "criteria": ["Fits protected constraints"], "rationale": "Reversible and within delegation.", "dissent": ["B would be cheaper."], "authority_basis": {"kind": "delegation", "approval_version_id": "ver_7"}, "revisit_conditions": ["New evidence on volume"], "status": "accepted"},
    "artifact": {"kind": "context-brief.md", "path": "proposals/context-brief.md", "content_hash": "cd" * 32, "producer_role": "context-analyst", "producer_task": "task_demo", "write_scope": "proposal-only", "implements_refs": [], "status": "proposed", "access_classification": "synthetic"},
    "validation": {"method": "unit tests", "target_refs": ["ver_3"], "receipt_id": "rcpt_1", "result": "passed", "rubric": None, "coverage": {"tests": 12}, "applicability": "current"},
    "challenge": {"contested_ref": "ver_9", "premise": "Volume stays flat.", "counterevidence_or_gap": "Q3 tickets doubled.", "consequence": "Cost model breaks.", "resolving_test": "Re-run with Q3 volume.", "proposer_role": "alternative-advocate", "round": 1, "state": "open"},
    "review": {"reviewed_refs": ["ver_3"], "reviewer_role": "review-manager", "reviewer_session": "sess-2", "findings": ["Receipts present."], "evidence_sufficiency": "sufficient", "result": "pass", "conflict_check": "verified", "unresolved": []},
    "approval": {"granted_by": "human-owner", "scope": "W02 shape-feature", "allowed_decisions": ["R1"], "allowed_actions": [], "bound_version_id": "ver_9", "limits": {"max_tasks": 3}, "expires_at": None, "revoked": False, "provenance": {"channel": "host_user_input", "attested": True, "note": "typed by owner"}},
    "event": {"id": "evt_1", "seq": 1, "case_id": "case_demo", "type": "case.created", "actor_role": "controller", "actor_task": None, "expected_state_version": 0, "payload_refs": [], "created_at": TS, "idempotency_key": "case.created:case_demo"},
    "receipt": {"id": "rcpt_1", "task_id": "task_demo", "command": ["python3", "-c", "pass"], "cwd": "/work", "snapshot": {"kind": "git", "commit": "abc123", "dirty_diff_sha256": None, "paths": ["src"]}, "started_at": TS, "ended_at": TS, "exit_status": 0, "timed_out": False, "cancelled": False, "stdout_path": "receipts/rcpt_1.out", "stderr_path": "receipts/rcpt_1.err", "observation_source": "controller", "test_ids": [], "redactions_applied": 0, "proves": "command_exit_status_only"},
    "route-plan": {"request": "summarize this design", "workflow_id": "W02", "mode": "focused", "risk_tier": "R0", "selected_roles": ["context-analyst", "claim-checker"], "omitted_roles": [{"role_id": "product-director", "reason": "narrow request"}], "stages": [{"stage_id": "frame", "role_id": "context-analyst", "included": True, "reason": "non-conditional"}, {"stage_id": "review", "role_id": "discovery-manager", "included": True, "reason": "review stages are never pruned", "satisfied_by_version_id": None}], "predicates": {"missing_current_artifact": True}, "budget_check": {"fits": True, "overflow": 0}, "explicit": False},
    "work-order": {"id": "wo_1", "task_id": "task_demo", "role_id": "context-analyst", "envelope": ENVELOPE},
    "policy-authority": {"roles": {"specialist": {"propose": True, "review": "assigned_only", "adjudicate": False, "accept": False, "execute": "declared_scope"}, "judge": {"adjudicate": "assigned_question"}}, "special": {"human-owner": {"accept": True, "execute": "personally"}}, "risk_tiers": {"R0": {"autonomous": "recommendation"}, "R2": {"autonomous": False, "requires": ["independent_review", "human_acceptance"]}, "R3": {"autonomous": False, "executable_in_v0_1": False}}},
}


class RecordFixtures(unittest.TestCase):
    def test_a_fixture_exists_for_every_non_registry_schema(self):
        expected = {name for name in RECORD_SCHEMAS if not name.startswith("registry-")}
        self.assertEqual(expected, set(FIXTURES))

    def test_fixtures_validate(self):
        for name, fixture in FIXTURES.items():
            with self.subTest(schema=name):
                self.assertEqual([], V.validate(fixture, V.load_schema(name)))

    def test_extra_top_level_key_is_rejected(self):
        for name, fixture in FIXTURES.items():
            with self.subTest(schema=name):
                mutated = dict(copy.deepcopy(fixture), zzz_extra=1)
                self.assertEqual(["/zzz_extra: additional property 'zzz_extra' is not allowed"], V.validate(mutated, V.load_schema(name)))

    def test_each_missing_required_field_is_reported_at_its_pointer(self):
        for name, fixture in FIXTURES.items():
            for field in REQUIRED[name]:
                with self.subTest(schema=name, field=field):
                    mutated = copy.deepcopy(fixture)
                    del mutated[field]
                    self.assertIn(f"/{field}: '{field}' is a required property", V.validate(mutated, V.load_schema(name)))

    def test_contract_specific_constraints(self):
        def errors(name, **changes):
            inst = copy.deepcopy(FIXTURES[name])
            inst.update(changes)
            return V.validate(inst, V.load_schema(name))

        self.assertTrue(any("shorter than minLength 1" in e for e in errors("challenge", premise="")))
        self.assertTrue(any("/round: 0 is less than minimum 1" in e for e in errors("challenge", round=0)))
        self.assertTrue(any("/reviewed_refs: array has 0 item(s) but minItems is 1" in e for e in errors("review", reviewed_refs=[])))
        self.assertTrue(any("/proves:" in e and "is not the constant" in e for e in errors("receipt", proves="everything")))
        self.assertEqual([], errors("receipt", exit_status=None, timed_out=True))
        self.assertTrue(any("/exit_status: '0' is not of type 'integer', 'null'" in e for e in errors("receipt", exit_status="0")))
        self.assertTrue(any("/snapshot/kind: 'zip' is not one of ['git', 'manifest']" in e for e in errors("receipt", snapshot={"kind": "zip"})))
        self.assertTrue(any("/seq: 0 is less than minimum 1" in e for e in errors("event", seq=0)))
        self.assertTrue(any("/created_at:" in e and "date-time" in e for e in errors("event", created_at="today")))
        self.assertTrue(any("/options: array has 0 item(s) but minItems is 1" in e for e in errors("proposal", options=[])))
        self.assertTrue(any("/options/0/extra: additional property" in e for e in errors("proposal", options=[{"id": "A", "summary": "x", "extra": 1}])))
        self.assertTrue(any("/budget/max_steps: 0 is less than minimum 1" in e for e in errors("task-envelope", budget={"max_steps": 0, "timeout_s": 1})))
        self.assertTrue(any("/capabilities/execution_mode: 'live' is not one of" in e for e in errors("task-envelope", capabilities={"tools": [], "unavailable": [], "execution_mode": "live"})))
        self.assertTrue(any("/observed_checks/0/command: 'command' is a required property" in e for e in errors("agent-response", observed_checks=[{"receipt_id": "r"}])))
        self.assertTrue(any("/actual_execution_metadata/execution_mode: 'execution_mode' is a required property" in e for e in errors("agent-response", actual_execution_metadata={})))
        self.assertTrue(any("/proposed_links/0/relation: 'relation' is a required property" in e for e in errors("agent-response", proposed_links=[{"to_version": "v"}])))
        self.assertTrue(any("/predicates/requires_retrieval: 'maybe' is not of type 'boolean'" in e for e in errors("route-plan", predicates={"requires_retrieval": "maybe"})))
        self.assertTrue(any("/provenance/attested: 'yes' is not of type 'boolean'" in e for e in errors("approval", provenance={"channel": "cli", "attested": "yes"})))
        self.assertTrue(any("/granted_by: 'manager' is not one of ['human-owner', 'delegation']" in e for e in errors("approval", granted_by="manager")))
        self.assertTrue(any("/authority_basis/kind: 'vibes' is not one of ['delegation', 'human_input']" in e for e in errors("decision", authority_basis={"kind": "vibes"})))
        self.assertTrue(any("/envelope/case_id: 'case_id' is a required property" in e for e in errors("work-order", envelope={k: v for k, v in ENVELOPE.items() if k != "case_id"})))
        self.assertTrue(any("/roles/specialist/accept: 'sometimes' is not of type 'boolean', 'string'" in e for e in errors("policy-authority", roles={"specialist": {"accept": ["sometimes"]}})) or any("/roles/specialist/accept:" in e for e in errors("policy-authority", roles={"specialist": {"accept": ["sometimes"]}})))
        self.assertTrue(any("/assessed_by:" in e and "pattern" in e for e in errors("claim", assessed_by="Claim Checker")))

    def test_work_order_embeds_the_task_envelope_exactly(self):
        envelope = V.load_schema("task-envelope")
        work_order = V.load_schema("work-order")
        embedded = work_order["$defs"]["task_envelope"]
        self.assertEqual({k: envelope[k] for k in ("type", "additionalProperties", "required", "properties")}, embedded)
        for name, definition in envelope["$defs"].items():
            self.assertEqual(definition, work_order["$defs"][name], name)
        self.assertEqual({"$ref": "#/$defs/task_envelope"}, work_order["properties"]["envelope"])


if __name__ == "__main__":
    unittest.main()
