"""Unit tests for ai_product_team.routing (contract section 10, section 13 "test_routing", section 14 addendum).

Covers: the AT-06 narrow requests (summarize → context-analyst + claim-checker only; fix wording →
requirements-writer with at most a change-impact-analyst diff check; deploy → R3 human action request with
zero executable stages); explicit role and explicit workflow selection; pruning by a current accepted
artifact with ``satisfied_by_version_id``; review and independence-required stages never pruned; the
external-action path including an explicit role; unknown predicate → ValidationError; budget overflow
reported while the plan is still returned; risk only ever raised; director review only when consequential
or disputed; ``CaseState.from_store`` derivations over a real CaseStore; schema validity of every plan;
and routing-table consistency checks at Router construction. The real registry and policies are loaded
from the repository; every CaseStore lives in tempfile.TemporaryDirectory(); nothing is written into the
repository tree.
"""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from ai_product_team import policies as P
from ai_product_team import registry as R
from ai_product_team import routing as RT
from ai_product_team import storage as S
from ai_product_team import validation as V
from ai_product_team.errors import NotFoundError, ValidationError

REPO = Path(__file__).resolve().parents[2]
REGISTRY = R.Registry.load(REPO)
POLICIES = P.Policies.load(REPO)
ROUTE_PLAN_SCHEMA = V.load_schema("route-plan")

CASE_PAYLOAD = {
    "objective": "Synthetic support copilot case for routing tests.",
    "protected_constraints": ["No automatic sending."],
    "source_scope": ["examples/support-copilot"],
    "owner": "human-owner",
}

ARTIFACT = {
    "kind": "context-brief.md",
    "path": "proposals/context-brief.md",
    "content_hash": "ab" * 32,
    "producer_role": "context-analyst",
    "producer_task": "task_demo",
    "write_scope": "proposal-only",
    "implements_refs": [],
    "status": "proposed",
    "access_classification": "synthetic",
}
CLAIM = {
    "statement": "Drafts only.",
    "claim_type": "fact",
    "status": "supported",
    "supporting_refs": [],
    "contrary_refs": [],
    "confidence_label": "high",
    "assessed_by": "claim-checker",
}
REQUIREMENT = {
    "statement": "No automatic sending.",
    "owner": "human-owner",
    "acceptance_criteria": ["Send path absent."],
    "protected": True,
    "originating_refs": [],
    "status": "approved",
}
CHALLENGE = {
    "contested_ref": "ver_demo",
    "premise": "The premise.",
    "counterevidence_or_gap": "A gap.",
    "consequence": "Material consequence.",
    "resolving_test": "A test.",
    "proposer_role": "assumption-challenger",
    "round": 1,
    "state": "open",
}
VALIDATION = {
    "method": "unit",
    "target_refs": ["ver_demo"],
    "receipt_id": "rcpt_demo",
    "result": "passed",
    "rubric": None,
    "coverage": None,
    "applicability": "current",
}

MANAGEMENT_TYPES = {"leader", "manager", "judge", "adversarial_orchestrator", "decision_maker"}


def included(plan: dict) -> list[dict]:
    return [s for s in plan["stages"] if s["included"]]


def stage(plan: dict, stage_id: str) -> dict:
    for s in plan["stages"]:
        if s["stage_id"] == stage_id:
            return s
    raise AssertionError(f"no stage {stage_id!r} in plan")


def role_types(plan: dict) -> set[str]:
    return {REGISTRY.agents[r].type for r in plan["selected_roles"] if r in REGISTRY.agents}


class RouterBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.router = RT.Router(REGISTRY, POLICIES)

    def assertValidPlan(self, plan: dict) -> None:
        errors = V.validate(plan, ROUTE_PLAN_SCHEMA)
        self.assertEqual(errors, [], errors)
        json.dumps(plan)

    def route(self, request: str, **kwargs) -> dict:
        kwargs.setdefault("case_state", RT.CaseState())
        kwargs.setdefault("mode", "standard")
        plan = self.router.route(request, **kwargs)
        self.assertValidPlan(plan)
        return plan


class StoreBase(RouterBase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.case_dir = Path(self.tmp.name) / "case"
        self.store = S.CaseStore.create(self.case_dir, dict(CASE_PAYLOAD))
        self.addCleanup(self.store.close)
        self.case_id = self.store.case_id

    def add_node(self, kind: str, payload: dict, *, status: str, applicability: str = "current", by: str = "controller") -> tuple[str, str]:
        node_id = self.store.new_node(kind, self.case_id)
        version_id = self.store.put_version(node_id, payload, author_role=payload.get("producer_role", by) if kind == "artifact" else by)
        self.store.set_current(node_id, version_id, status=status, applicability=applicability)
        return node_id, version_id

    def add_artifact(self, kind: str, *, status: str = "verified_for_scope", applicability: str = "current", producer: str = "context-analyst") -> str:
        payload = dict(ARTIFACT, kind=kind, path=f"proposals/{kind}", producer_role=producer, status=status)
        return self.add_node("artifact", payload, status=status, applicability=applicability)[1]

    def state(self) -> RT.CaseState:
        return RT.CaseState.from_store(self.store, self.case_id)


# --------------------------------------------------------------------------------------------------
# AT-06 narrow requests
# --------------------------------------------------------------------------------------------------


class NarrowRequests(RouterBase):
    def test_summarize_design_uses_context_analyst_and_claim_checker_only(self) -> None:
        plan = self.route("Summarize this supplied design document")
        self.assertEqual(plan["selected_roles"], ["context-analyst", "claim-checker"])
        self.assertEqual([s["role_id"] for s in included(plan)], ["context-analyst", "claim-checker"])
        self.assertFalse(role_types(plan) & MANAGEMENT_TYPES)
        for forbidden in ("discovery-manager", "product-director", "convergence-judge", "evidence-judge", "workflow-orchestrator"):
            self.assertNotIn(forbidden, plan["selected_roles"])
        self.assertEqual(plan["action_kind"], "analysis")
        self.assertEqual(plan["risk_tier"], "R0")
        self.assertFalse(plan["human_action_request"])
        self.assertTrue(plan["budget_check"]["fits"])
        self.assertFalse(plan["explicit"])

    def test_fix_wording_uses_requirements_writer_with_optional_diff_check(self) -> None:
        plan = self.route("Fix the wording of requirement R-3 for clarity")
        self.assertIn("requirements-writer", plan["selected_roles"])
        self.assertTrue(set(plan["selected_roles"]) <= {"requirements-writer", "change-impact-analyst"}, plan["selected_roles"])
        self.assertFalse(role_types(plan) & MANAGEMENT_TYPES)
        self.assertEqual(plan["action_kind"], "proposed_change")
        self.assertEqual(plan["risk_tier"], "R0")
        self.assertEqual(plan["workflow_id"], "W02")
        self.assertLessEqual(len(included(plan)), 2)

    def test_deploy_to_production_is_r3_human_action_request_without_executable_stage(self) -> None:
        plan = self.route("Deploy this to production now")
        self.assertEqual(plan["risk_tier"], "R3")
        self.assertTrue(plan["human_action_request"])
        self.assertEqual(plan["action_kind"], "external_action")
        self.assertEqual(included(plan), [])
        self.assertEqual(plan["selected_roles"], [])
        self.assertTrue(all(s["included"] is False for s in plan["stages"]))

    def test_every_narrow_pattern_routes_without_management_roles(self) -> None:
        for pattern in POLICIES.narrow_request_patterns():
            plan = self.route(f"Please {pattern} for the attached draft")
            with self.subTest(pattern=pattern):
                self.assertTrue(included(plan), pattern)
                self.assertFalse(role_types(plan) & MANAGEMENT_TYPES, plan["selected_roles"])
                self.assertLessEqual(len(plan["selected_roles"]), 3)

    def test_narrow_plan_reports_omitted_workflow_roles_with_reasons(self) -> None:
        plan = self.route("Summarize this supplied design document")
        omitted = {o["role_id"]: o["reason"] for o in plan["omitted_roles"]}
        self.assertIn("discovery-manager", omitted)
        self.assertIn("product-director", omitted)
        self.assertTrue(all(reason for reason in omitted.values()))
        self.assertFalse(set(omitted) & set(plan["selected_roles"]))


# --------------------------------------------------------------------------------------------------
# Classification
# --------------------------------------------------------------------------------------------------


class Classification(RouterBase):
    def test_keyword_match_selects_workflow(self) -> None:
        result = self.router.classify("Turn these documents into a feature proposal")
        self.assertEqual(result["workflow_id"], "W02")
        self.assertEqual(result["confidence"], "keyword")
        self.assertIn("turn these documents into", result["matched_phrases"])
        self.assertEqual(result["action_kind"], "analysis")
        self.assertEqual(result["risk_tier"], "R0")

    def test_exact_when_request_names_the_workflow(self) -> None:
        result = self.router.classify("run shape-feature on the corpus")
        self.assertEqual((result["workflow_id"], result["confidence"]), ("W02", "exact"))

    def test_fallback_when_nothing_matches(self) -> None:
        result = self.router.classify("lorem ipsum dolor sit amet")
        self.assertEqual(result["workflow_id"], "W01")
        self.assertEqual(result["confidence"], "fallback")
        self.assertEqual(result["matched_phrases"], [])

    def test_workflow_min_risk_is_a_floor(self) -> None:
        result = self.router.classify("Is this feature ready for release?")
        self.assertEqual(result["workflow_id"], "W09")
        self.assertEqual(result["risk_tier"], "R2")

    def test_risk_trigger_raises_tier_and_action_kind(self) -> None:
        result = self.router.classify("Should we add AI to this workflow and change the permission model?")
        self.assertEqual(result["workflow_id"], "W01")
        self.assertEqual(result["risk_tier"], "R2")
        self.assertEqual(result["action_kind"], "proposed_change")
        self.assertIn("permission", result["risk_triggers"])

    def test_external_trigger_from_risk_policy_alone_is_external_action(self) -> None:
        result = self.router.classify("Please publish the comparison")
        self.assertEqual(result["action_kind"], "external_action")
        self.assertEqual(result["risk_tier"], "R3")

    def test_local_execution_for_build_workflow(self) -> None:
        result = self.router.classify("Build a bounded version we can test")
        self.assertEqual(result["workflow_id"], "W04")
        self.assertEqual(result["action_kind"], "local_execution")
        self.assertEqual(result["risk_tier"], "R1")

    def test_plural_and_singular_tokens_match(self) -> None:
        self.assertTrue(RT.phrase_in("requirements", RT.tokens("one requirement here")))
        self.assertTrue(RT.phrase_in("trace", RT.tokens("the traces show it")))
        self.assertFalse(RT.phrase_in("send", RT.tokens("sending is not a whole-word match")))
        self.assertFalse(RT.phrase_in("", RT.tokens("anything")))

    def test_empty_request_refused(self) -> None:
        with self.assertRaises(ValidationError):
            self.router.classify("   ")
        with self.assertRaises(ValidationError):
            self.router.route("", case_state=RT.CaseState(), mode="standard")


# --------------------------------------------------------------------------------------------------
# Explicit selection
# --------------------------------------------------------------------------------------------------


class ExplicitSelection(RouterBase):
    def test_explicit_role_yields_one_stage_with_write_and_source_scope(self) -> None:
        state = RT.CaseState(source_scope=("docs/", "examples/support-copilot"))
        plan = self.route("Anything at all", case_state=state, explicit_role="claim-checker")
        self.assertEqual(len(plan["stages"]), 1)
        self.assertEqual(plan["selected_roles"], ["claim-checker"])
        self.assertEqual(plan["stages"][0]["role_id"], "claim-checker")
        self.assertTrue(plan["stages"][0]["included"])
        self.assertEqual(plan["explicit"]["role"], "claim-checker")
        self.assertEqual(plan["explicit"]["write_scope"], "proposal-only")
        self.assertEqual(plan["explicit"]["source_scope"], ["docs/", "examples/support-copilot"])
        self.assertEqual(plan["omitted_roles"], [])
        self.assertEqual(plan["budget_check"]["selected_tasks"], 1)

    def test_explicit_role_wins_over_narrow_pattern(self) -> None:
        plan = self.route("Summarize this supplied design document", explicit_role="journey-designer")
        self.assertEqual(plan["selected_roles"], ["journey-designer"])

    def test_explicit_workflow_wins_over_keywords_and_is_exact(self) -> None:
        plan = self.route("Summarize this supplied design document", explicit_workflow="shape-feature")
        self.assertEqual(plan["workflow_id"], "W02")
        self.assertEqual(plan["confidence"], "exact")
        self.assertEqual(plan["explicit"], {"workflow": "W02"})
        self.assertEqual([s["stage_id"] for s in plan["stages"]], ["reconstruct", "clarify", "design-job", "specify", "define-evidence", "review"])
        self.assertTrue(all(s["included"] for s in plan["stages"]))

    def test_explicit_workflow_by_id_and_role_together(self) -> None:
        plan = self.route("Anything", explicit_workflow="W03", explicit_role="retrieval-designer")
        self.assertEqual(plan["workflow_id"], "W03")
        self.assertEqual(plan["explicit"]["workflow"], "W03")
        self.assertEqual(plan["explicit"]["role"], "retrieval-designer")
        self.assertEqual(plan["risk_tier"], "R1")

    def test_unknown_role_workflow_and_mode_raise_not_found(self) -> None:
        with self.assertRaises(NotFoundError):
            self.router.route("x", case_state=RT.CaseState(), mode="standard", explicit_role="nobody")
        with self.assertRaises(NotFoundError):
            self.router.route("x", case_state=RT.CaseState(), mode="standard", explicit_role="human-owner")
        with self.assertRaises(NotFoundError):
            self.router.route("x", case_state=RT.CaseState(), mode="standard", explicit_workflow="W99")
        with self.assertRaises(NotFoundError):
            self.router.route("x", case_state=RT.CaseState(), mode="turbo")

    def test_case_state_type_is_checked(self) -> None:
        with self.assertRaises(ValidationError):
            self.router.route("x", case_state={"current_artifacts": {}}, mode="standard")  # type: ignore[arg-type]


# --------------------------------------------------------------------------------------------------
# External actions
# --------------------------------------------------------------------------------------------------


class ExternalActions(RouterBase):
    def test_explicit_role_cannot_bypass_external_action_rule(self) -> None:
        plan = self.route("Send the email to all customers", explicit_role="requirements-writer")
        self.assertEqual(plan["risk_tier"], "R3")
        self.assertTrue(plan["human_action_request"])
        self.assertEqual(included(plan), [])
        self.assertEqual(plan["selected_roles"], [])
        self.assertEqual(plan["explicit"]["role"], "requirements-writer")

    def test_explicit_workflow_with_external_keyword_has_no_executable_stage(self) -> None:
        plan = self.route("Review release and then push to main", explicit_workflow="review-release")
        self.assertEqual(plan["workflow_id"], "W09")
        self.assertEqual(plan["risk_tier"], "R3")
        self.assertEqual(included(plan), [])
        self.assertTrue(all("satisfied_by_version_id" not in s for s in plan["stages"]))
        omitted = {o["role_id"] for o in plan["omitted_roles"]}
        self.assertIn("independent-auditor", omitted)

    def test_case_floor_at_top_tier_is_not_executable(self) -> None:
        plan = self.route("Summarize this supplied design document", case_state=RT.CaseState(risk_floor="R3"))
        self.assertEqual(plan["risk_tier"], "R3")
        self.assertTrue(plan["human_action_request"])
        self.assertEqual(included(plan), [])

    def test_non_external_requests_are_not_human_action_requests(self) -> None:
        plan = self.route("Turn these documents into a feature proposal")
        self.assertFalse(plan["human_action_request"])
        self.assertTrue(included(plan))


# --------------------------------------------------------------------------------------------------
# Pruning and review gates
# --------------------------------------------------------------------------------------------------


class Pruning(StoreBase):
    def test_current_accepted_artifact_prunes_stage_with_version_id(self) -> None:
        version_id = self.add_artifact("context-brief.md")
        state = self.state()
        self.assertEqual(state.current_artifacts, {"context-brief.md": version_id})
        plan = self.route("Turn these documents into a feature proposal", case_state=state, explicit_workflow="W02")
        reconstruct = stage(plan, "reconstruct")
        self.assertFalse(reconstruct["included"])
        self.assertEqual(reconstruct["satisfied_by_version_id"], version_id)
        self.assertNotIn("context-analyst", plan["selected_roles"])
        self.assertIn("context-analyst", {o["role_id"] for o in plan["omitted_roles"]})
        self.assertTrue(stage(plan, "clarify")["included"])
        self.assertEqual(plan["budget_check"]["selected_tasks"], 5)

    def test_proposed_or_non_current_artifacts_do_not_prune(self) -> None:
        self.add_artifact("context-brief.md", status="proposed")
        self.add_artifact("journey.md", status="implemented_not_verified")
        self.add_artifact("requirements.json", status="verified_for_scope", applicability="historical")
        self.add_artifact("acceptance-map.json", status="verified_for_scope", applicability="invalidated")
        state = self.state()
        self.assertEqual(state.current_artifacts, {})
        plan = self.route("shape feature", case_state=state, explicit_workflow="W02")
        self.assertTrue(all(s["included"] for s in plan["stages"]))
        self.assertTrue(all("satisfied_by_version_id" not in s for s in plan["stages"]))

    def test_review_stage_is_never_pruned(self) -> None:
        self.add_artifact("experience-review.json", producer="experience-manager")
        state = self.state()
        self.assertIn("experience-review.json", state.current_artifacts)
        plan = self.route("shape feature", case_state=state, explicit_workflow="W02")
        review = stage(plan, "review")
        self.assertTrue(review["included"])
        self.assertIsNone(review.get("satisfied_by_version_id"))
        self.assertIn("never pruned", review["reason"])
        self.assertIn("experience-manager", plan["selected_roles"])

    def test_independence_required_stage_is_never_pruned(self) -> None:
        self.add_artifact("audit.json", producer="independent-auditor")
        self.add_artifact("repository-map.md", producer="repository-mapper")
        plan = self.route("Build a bounded version we can test", case_state=self.state(), explicit_workflow="W04")
        audit = stage(plan, "audit")
        self.assertTrue(audit["included"])
        self.assertIsNone(audit.get("satisfied_by_version_id"))
        self.assertFalse(stage(plan, "map")["included"])
        self.assertIn("independent-auditor", plan["selected_roles"])
        self.assertIn("engineering-manager", plan["selected_roles"])

    def test_gates_survive_every_workflow_fully_satisfied(self) -> None:
        for workflow_id in REGISTRY.workflow_ids:
            workflow = REGISTRY.workflow(workflow_id)
            state = RT.CaseState(
                current_artifacts={s.artifact: f"ver_{i}" for i, s in enumerate(workflow.stages)},
                has_retrieval=True,
                protected_scope_touched=False,
                material_conflicts=1,
                evidence_points_to_code=True,
                rework_required=True,
                revalidation_required=True,
                improvement_has_fixtures=True,
            )
            plan = self.route(workflow.title, case_state=state, explicit_workflow=workflow_id)
            with self.subTest(workflow=workflow_id):
                for s in workflow.stages:
                    decision = stage(plan, s.id)
                    if s.review or s.independence_required:
                        self.assertTrue(decision["included"], (workflow_id, s.id))
                        self.assertIsNone(decision.get("satisfied_by_version_id"))
                    else:
                        self.assertFalse(decision["included"], (workflow_id, s.id))
                        if s.conditional and "satisfied_by_version_id" not in decision:
                            self.assertIn(f"predicate {s.conditional!r} is false", decision["reason"])
                        else:
                            self.assertEqual(decision["satisfied_by_version_id"], state.current_artifacts[s.artifact])


# --------------------------------------------------------------------------------------------------
# Predicates
# --------------------------------------------------------------------------------------------------


class Predicates(RouterBase):
    def test_unknown_predicate_raises_validation_error(self) -> None:
        with self.assertRaises(ValidationError) as ctx:
            self.router.evaluate_predicate("eval_user_code", RT.CaseState())
        self.assertTrue(any("eval_user_code" in e for e in ctx.exception.errors))
        with self.assertRaises(ValidationError):
            self.router.evaluate_predicate(None, RT.CaseState())  # type: ignore[arg-type]

    def test_every_registry_predicate_is_evaluable(self) -> None:
        state = RT.CaseState(current_artifacts={"context-brief.md": "ver_1"})
        for name in REGISTRY.predicates:
            with self.subTest(predicate=name):
                value = self.router.evaluate_predicate(name, state, artifact="journey.md")
                self.assertIsInstance(value, bool)

    def test_predicate_values_follow_case_state(self) -> None:
        empty = RT.CaseState()
        full = RT.CaseState(
            current_artifacts={"journey.md": "ver_j"},
            has_retrieval=True,
            protected_scope_touched=True,
            material_conflicts=2,
            unresolved_dissent=1,
            risk_floor="R2",
            evidence_points_to_code=True,
            rework_required=True,
            revalidation_required=True,
            improvement_has_fixtures=True,
        )
        ev = self.router.evaluate_predicate
        self.assertTrue(ev("missing_current_artifact", empty, artifact="journey.md"))
        self.assertFalse(ev("missing_current_artifact", full, artifact="journey.md"))
        for name in ("requires_retrieval", "changes_protected_scope", "material_conflict", "independent_review_required",
                     "consequential_or_disputed", "evidence_points_to_code", "rework_required", "revalidation_required",
                     "improvement_needs_evaluation"):
            self.assertFalse(ev(name, empty), name)
            self.assertTrue(ev(name, full), name)
        self.assertTrue(ev("consequential_or_disputed", RT.CaseState(unresolved_dissent=1)))
        self.assertTrue(ev("independent_review_required", RT.CaseState(risk_floor="R3")))
        self.assertFalse(ev("independent_review_required", RT.CaseState(risk_floor="R1")))

    def test_missing_current_artifact_requires_artifact(self) -> None:
        with self.assertRaises(ValidationError):
            self.router.evaluate_predicate("missing_current_artifact", RT.CaseState())

    def test_case_state_type_checked(self) -> None:
        with self.assertRaises(ValidationError):
            self.router.evaluate_predicate("requires_retrieval", object())  # type: ignore[arg-type]

    def test_conditional_stages_follow_predicates(self) -> None:
        base = RT.CaseState()
        plan = self.route("design how this ai feature should work", case_state=base)
        self.assertEqual(plan["workflow_id"], "W03")
        self.assertFalse(stage(plan, "retrieval")["included"])
        self.assertNotIn("retrieval-designer", plan["selected_roles"])
        plan = self.route("design how this ai feature should work", case_state=RT.CaseState(has_retrieval=True))
        self.assertTrue(stage(plan, "retrieval")["included"])
        self.assertIn("retrieval-designer", plan["selected_roles"])
        self.assertTrue(plan["predicates"]["requires_retrieval"])

    def test_plan_predicates_map_is_complete_and_boolean(self) -> None:
        plan = self.route("why this feature is failing", case_state=RT.CaseState(evidence_points_to_code=True))
        self.assertEqual(set(plan["predicates"]), set(REGISTRY.predicates))
        self.assertTrue(all(isinstance(v, bool) for v in plan["predicates"].values()))
        self.assertTrue(stage(plan, "targeted-causes")["included"])


# --------------------------------------------------------------------------------------------------
# Risk, directors and budget
# --------------------------------------------------------------------------------------------------


class RiskAndBudget(RouterBase):
    def test_risk_is_never_lowered_below_any_minimum(self) -> None:
        self.assertEqual(self.route("Is this feature ready for release?")["risk_tier"], "R2")
        self.assertEqual(self.route("Should we add AI to this workflow?")["risk_tier"], "R0")
        self.assertEqual(self.route("Should we add AI to this workflow?", case_state=RT.CaseState(risk_floor="R1"))["risk_tier"], "R1")
        self.assertEqual(self.route("Should we add AI to this workflow?", case_state=RT.CaseState(protected_scope_touched=True))["risk_tier"], "R2")
        self.assertEqual(self.route("Should we add AI to this workflow? Rotate the credential first.")["risk_tier"], "R2")
        self.assertEqual(self.route("Is this feature ready for release?", case_state=RT.CaseState(risk_floor="R0"))["risk_tier"], "R2")

    def test_protected_scope_requires_independent_review_and_director(self) -> None:
        plan = self.route("Should we add AI to this workflow?", case_state=RT.CaseState(protected_scope_touched=True))
        self.assertTrue(plan["predicates"]["independent_review_required"])
        self.assertTrue(plan["predicates"]["consequential_or_disputed"])
        self.assertTrue(stage(plan, "decide-or-test")["included"])
        self.assertIn("product-director", plan["selected_roles"])
        self.assertTrue(stage(plan, "director-review")["included"])

    def test_director_only_when_consequential_or_disputed(self) -> None:
        plain = self.route("Should we add AI to this workflow?")
        self.assertNotIn("product-director", plain["selected_roles"])
        self.assertFalse(stage(plain, "decide-or-test")["included"])
        self.assertIn("product-director", {o["role_id"] for o in plain["omitted_roles"]})
        disputed = self.route("Should we add AI to this workflow?", case_state=RT.CaseState(unresolved_dissent=1))
        self.assertIn("product-director", disputed["selected_roles"])
        self.assertTrue(stage(disputed, "decide-or-test")["included"])
        self.assertIn("decision-authority", disputed["selected_roles"])

    def test_manager_review_stage_is_part_of_the_full_plan(self) -> None:
        plan = self.route("Should we add AI to this workflow?")
        self.assertIn("discovery-manager", plan["selected_roles"])
        self.assertEqual(plan["selected_roles"], ["context-analyst", "discovery-interviewer", "opportunity-analyst", "discovery-manager"])

    def test_budget_overflow_is_reported_and_plan_still_returned(self) -> None:
        plan = self.route("Challenge this proposal and resolve the disagreement", mode="focused")
        self.assertEqual(plan["workflow_id"], "W11")
        check = plan["budget_check"]
        self.assertFalse(check["fits"])
        self.assertEqual(check["max_worker_tasks"], POLICIES.mode("focused")["max_worker_tasks"])
        self.assertEqual(check["selected_tasks"], len(included(plan)))
        self.assertEqual(check["overflow"], check["selected_tasks"] - check["max_worker_tasks"])
        self.assertGreater(check["overflow"], 0)
        deep = self.route("Challenge this proposal and resolve the disagreement", mode="deep")
        self.assertTrue(deep["budget_check"]["fits"])
        self.assertEqual(deep["budget_check"]["overflow"], 0)

    def test_root_orchestrator_is_not_a_worker_slot(self) -> None:
        plan = self.route("Build a bounded version we can test")
        self.assertEqual(plan["workflow_id"], "W04")
        self.assertTrue(stage(plan, "handoff")["included"])
        self.assertIn("workflow-orchestrator", plan["selected_roles"])
        self.assertEqual(plan["budget_check"]["selected_tasks"], len(included(plan)) - 1)

    def test_proposal_owner_stage_counts_but_is_not_a_registry_role(self) -> None:
        plan = self.route("resolve decision", explicit_workflow="W11")
        respond = stage(plan, "respond")
        self.assertEqual(respond["role_id"], "proposal-owner")
        self.assertTrue(respond["included"])
        self.assertNotIn("proposal-owner", plan["selected_roles"])
        self.assertNotIn("proposal-owner", {o["role_id"] for o in plan["omitted_roles"]})

    def test_omitted_roles_never_overlap_selected(self) -> None:
        for request in ("Should we add AI to this workflow?", "Summarize this", "Build a bounded version we can test", "Something changed. What must we revisit?"):
            plan = self.route(request)
            with self.subTest(request=request):
                self.assertFalse({o["role_id"] for o in plan["omitted_roles"]} & set(plan["selected_roles"]))
                self.assertEqual(len(set(plan["selected_roles"])), len(plan["selected_roles"]))


# --------------------------------------------------------------------------------------------------
# CaseState.from_store
# --------------------------------------------------------------------------------------------------


class CaseStateFromStore(StoreBase):
    def test_empty_case(self) -> None:
        state = self.state()
        self.assertEqual(state, RT.CaseState(source_scope=("examples/support-copilot",), case_id=self.case_id))

    def test_wrong_case_id_raises(self) -> None:
        with self.assertRaises(NotFoundError):
            RT.CaseState.from_store(self.store, "case_other")

    def test_artifacts_claims_challenges_and_queue(self) -> None:
        brief = self.add_artifact("context-brief.md")
        self.add_artifact("journey.md", status="proposed")
        self.add_artifact("retrieval-contract.md", producer="retrieval-designer")
        _, req_version = self.add_node("requirement", dict(REQUIREMENT), status="approved")
        self.add_node("claim", dict(CLAIM, status="contested"), status="contested")
        self.add_node("claim", dict(CLAIM), status="supported")
        self.add_node("challenge", dict(CHALLENGE), status="open")
        self.add_node("challenge", dict(CHALLENGE, state="withdrawn"), status="withdrawn")
        self.store.insert("impact_queue", {"affected_version": req_version, "changed_version": "ver_x", "impact_policy": "review", "state": "review_required", "reason": "x"})
        state = self.state()
        self.assertEqual(state.current_artifacts["context-brief.md"], brief)
        self.assertNotIn("journey.md", state.current_artifacts)
        self.assertTrue(state.has_retrieval)
        self.assertTrue(state.protected_scope_touched)
        self.assertEqual(state.material_conflicts, 1)
        self.assertEqual(state.unresolved_dissent, 1)
        self.assertFalse(state.rework_required)
        self.assertFalse(state.revalidation_required)
        self.assertFalse(state.improvement_has_fixtures)
        self.assertEqual(state.risk_floor, "R0")

    def test_protected_reason_in_queue_and_resolved_rows(self) -> None:
        self.store.insert("impact_queue", {"affected_version": "ver_a", "reason": RT.PROTECTED_IMPACT_REASON, "state": "review_required"})
        self.assertTrue(self.state().protected_scope_touched)
        rows = self.store.query("impact_queue")
        self.store.update("impact_queue", rows[0]["id"], {"resolved_at": "2026-10-16T12:00:00Z"})
        self.assertFalse(self.state().protected_scope_touched)

    def test_invalidated_records_set_rework_and_revalidation(self) -> None:
        self.add_artifact("patch.diff", status="changes_required", producer="prototype-engineer")
        self.assertTrue(self.state().rework_required)
        self.assertFalse(self.state().revalidation_required)
        self.add_node("validation", dict(VALIDATION), status="passed", applicability="invalidated")
        self.assertTrue(self.state().revalidation_required)

    def test_fixture_artifacts_and_retrieval_requirement(self) -> None:
        self.add_artifact("dataset-manifest.json", producer="dataset-curator")
        self.add_node("requirement", dict(REQUIREMENT, statement="Answers cite retrieved passages.", protected=False), status="approved")
        state = self.state()
        self.assertTrue(state.improvement_has_fixtures)
        self.assertTrue(state.has_retrieval)
        self.assertFalse(state.protected_scope_touched)

    def test_case_flags_and_risk_floor_from_payload(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        payload = dict(CASE_PAYLOAD, risk_floor="R1", flags={"evidence_points_to_code": True, "improvement_has_fixtures": True, "has_retrieval": "yes"})
        store = S.CaseStore.create(Path(tmp.name) / "flagged", payload)
        self.addCleanup(store.close)
        state = RT.CaseState.from_store(store, store.case_id)
        self.assertTrue(state.evidence_points_to_code)
        self.assertTrue(state.improvement_has_fixtures)
        self.assertFalse(state.has_retrieval)
        self.assertEqual(state.risk_floor, "R1")
        plan = self.route("Should we add AI to this workflow?", case_state=state)
        self.assertEqual(plan["risk_tier"], "R1")

    def test_from_store_state_routes_end_to_end(self) -> None:
        self.add_artifact("context-brief.md")
        plan = self.route("Should we add AI to this workflow?", case_state=self.state())
        frame = stage(plan, "frame")
        self.assertFalse(frame["included"])
        self.assertEqual(frame["satisfied_by_version_id"], self.state().current_artifacts["context-brief.md"])


# --------------------------------------------------------------------------------------------------
# Router construction checks
# --------------------------------------------------------------------------------------------------


class RouterConstruction(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.docs = {attr: copy.deepcopy(getattr(POLICIES, attr)) for attr in P.POLICY_FILES}

    def build(self) -> RT.Router:
        return RT.Router(REGISTRY, P.Policies.from_data(Path(self.tmp.name), self.docs))

    def test_real_policies_build(self) -> None:
        self.assertIsInstance(self.build(), RT.Router)

    def test_narrow_route_to_a_director_is_refused(self) -> None:
        self.docs["routing_keywords"]["narrow_routes"]["summarize"] = ["product-director"]
        with self.assertRaises(ValidationError) as ctx:
            self.build()
        self.assertTrue(any("product-director" in e for e in ctx.exception.errors))

    def test_narrow_route_to_unknown_agent_is_refused(self) -> None:
        self.docs["routing_keywords"]["narrow_routes"]["summarize"] = ["ghost-writer"]
        with self.assertRaises(ValidationError):
            self.build()

    def test_pattern_without_route_is_refused(self) -> None:
        self.docs["routing_keywords"]["narrow_request_patterns"].append("tidy up")
        with self.assertRaises(ValidationError) as ctx:
            self.build()
        self.assertTrue(any("tidy up" in e for e in ctx.exception.errors))

    def test_unknown_keyword_workflow_is_refused(self) -> None:
        self.docs["routing_keywords"]["workflows"]["W13"] = ["thirteen"]
        with self.assertRaises(ValidationError):
            self.build()

    def test_unknown_fallback_is_refused(self) -> None:
        self.docs["routing_keywords"]["fallback"]["workflow_id"] = "W42"
        with self.assertRaises(ValidationError):
            self.build()


if __name__ == "__main__":
    unittest.main()
