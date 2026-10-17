"""Unit tests for ai_product_team.decisions (contract section 8, section 13 "test_decisions").

Covers: author cannot review own artifact; same session (and same native child id) conflict; unknown origin
stored as unverified; manager review recorded as not independent; pass citing an unexecuted check refused;
challenge round cap and consecutive rounds; empty material field refused; challenge response by the owner
with a superseding revision; judge-only rulings that change no status; judge/manager/specialist cannot
accept; decision-authority needs a delegation bound to the exact proposal version (AT-09: a revised proposal
invalidates the approval); expired and revoked approvals refused; R2 needs a human; cli-channel human input
is unattested and refused while the status stays human_required; attested host input accepts; R3 has no
accept or execute path. Everything runs in a tempfile.TemporaryDirectory(); nothing touches the repo tree.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any

from ai_product_team import decisions as D
from ai_product_team.errors import BudgetExhausted, ConflictError, NotFoundError, PolicyError, TransitionError, ValidationError
from ai_product_team.policies import Policies
from ai_product_team.registry import Registry
from ai_product_team.storage import CaseStore

REPO = Path(__file__).resolve().parents[2]
TS = "2026-10-16T12:00:00Z"
FAR_FUTURE = "2999-01-01T00:00:00Z"
LONG_AGO = "2000-01-01T00:00:00Z"

PROPOSAL: dict[str, Any] = {
    "title": "Retrieval strategy for the support copilot",
    "options": [{"id": "A", "summary": "Keyword search over the synthetic FAQ."}, {"id": "B", "summary": "Hybrid search."}],
    "recommended_option": "A",
    "assumptions": ["The FAQ is small."],
    "evidence_refs": [],
    "constraints": ["Drafts only; no automatic sending."],
    "unresolved_questions": [],
    "target_refs": [],
    "author_role": "workflow-architect",
    "author_session": "sess-architect",
    "requested_authority": "R1",
}
ARTIFACT: dict[str, Any] = {
    "kind": "prototype",
    "path": "proposals/prototype.md",
    "content_hash": "ab" * 32,
    "producer_role": "prototype-engineer",
    "producer_task": "task_build",
    "producer_session": "sess-builder",
    "write_scope": "assigned-worktree",
    "implements_refs": [],
    "status": "implemented_not_verified",
    "access_classification": "synthetic",
}
REVIEW: dict[str, Any] = {
    "findings": ["Looks structurally complete."],
    "evidence_sufficiency": "sufficient",
    "result": "ready",
    "unresolved": [],
}
CHALLENGE: dict[str, Any] = {
    "premise": "Keyword search is enough for the FAQ.",
    "counterevidence_or_gap": "No measurement of paraphrased questions exists.",
    "consequence": "Paraphrased questions would return nothing.",
    "resolving_test": "Run the paraphrase fixture set through both options.",
    "proposer_role": "assumption-challenger",
}
RULING: dict[str, Any] = {
    "criteria": ["Answers paraphrased questions", "Stays within the FAQ"],
    "admissible_evidence": [],
    "findings_per_objection": [{"objection": "paraphrase gap", "finding": "unmeasured"}],
    "option_comparison": {"A": "cheaper", "B": "unmeasured recall gain"},
    "outcome": "next_test_required",
    "uncertainty": "No fixture has been run.",
    "next_checks": ["Run the paraphrase fixture set."],
    "dissent_preserved": ["Alternative advocate prefers B."],
}


def receipt(receipt_id: str) -> dict[str, Any]:
    return {
        "id": receipt_id,
        "task_id": "task_build",
        "command": ["python3", "-c", "pass"],
        "cwd": "/work",
        "snapshot": {"kind": "manifest", "manifest_sha256": "cd" * 32, "paths": ["src"]},
        "started_at": TS,
        "ended_at": TS,
        "exit_status": 0,
        "timed_out": False,
        "cancelled": False,
        "stdout_path": f"receipts/{receipt_id}.out",
        "stderr_path": f"receipts/{receipt_id}.err",
        "observation_source": "controller",
        "test_ids": [],
        "redactions_applied": 0,
        "proves": "command_exit_status_only",
    }


class FakeController:
    """Minimal stand-in for Controller.task_mark_reviewed (the controller module is owned elsewhere)."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def task_mark_reviewed(self, task_id: str, review_version_id: str) -> None:
        self.calls.append((task_id, review_version_id))


class DecisionsCase(unittest.TestCase):
    """One temporary case store per test, with the real registry and policies loaded from the repo."""

    registry: Registry
    policies: Policies

    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = Registry.load(REPO)
        cls.policies = Policies.load(REPO)

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.store = CaseStore.create(self.tmp / "case", {"objective": "Decisions tests", "owner": "human-owner", "source_scope": ["docs/"]})
        self.case_id = self.store.case_id
        self.controller = FakeController()
        self.decisions = D.Decisions(self.store, self.registry, self.policies, controller=self.controller)
        self.run_id = self.store.insert("runs", {"mode": "standard", "state": "executing", "workflow_id": "W02"})

    def tearDown(self) -> None:
        self.store.close()
        self._tmp.cleanup()

    # -- fixtures -------------------------------------------------------------------------------------

    def add_proposal(self, **overrides: Any) -> tuple[str, str]:
        payload = {**PROPOSAL, **overrides}
        node = self.store.new_node("proposal", self.case_id)
        version = self.store.put_version(node, payload, author_role=payload["author_role"], author_session=payload.get("author_session"))
        self.store.set_current(node, version, status="proposed")
        return node, version

    def add_artifact(self, **overrides: Any) -> tuple[str, str]:
        payload = {**ARTIFACT, **overrides}
        node = self.store.new_node("artifact", self.case_id)
        version = self.store.put_version(
            node, payload, author_role=payload["producer_role"], author_task=payload["producer_task"], author_session=payload.get("producer_session")
        )
        self.store.set_current(node, version, status=payload["status"])
        return node, version

    def add_decision(self, proposal_version: str, *, by: str = "decision-authority", **overrides: Any) -> str:
        payload = {
            "proposal_version_id": proposal_version,
            "outcome": "accepted",
            "selected_option": "A",
            "criteria": ["Fits the FAQ"],
            "rationale": "Reversible and cheap.",
            "dissent": ["Alternative advocate prefers B."],
            "authority_basis": {"kind": "delegation", "approval_version_id": None},
            "revisit_conditions": ["Paraphrase recall measured below 80%."],
            "status": "proposed",
            **overrides,
        }
        return self.decisions.propose_decision(self.case_id, payload, by=by)

    def add_approval(self, bound: str, *, granted_by: str = "delegation", channel: str = "file", **overrides: Any) -> str:
        payload = {
            "granted_by": granted_by,
            "scope": "retrieval strategy for the synthetic support copilot",
            "allowed_decisions": ["R0", "R1", "R2"],
            "allowed_actions": [],
            "bound_version_id": bound,
            "limits": {"note": "local, reversible"},
            "expires_at": FAR_FUTURE,
            "revoked": False,
            **overrides,
        }
        return self.decisions.record_user_input(self.case_id, payload, channel=channel)

    def review(self, refs: list[str], *, role: str = "test-engineer", session: str | None = "sess-reviewer", payload: dict | None = None, task_id: str | None = None) -> str:
        return self.decisions.submit_review(
            self.case_id, reviewed_refs=refs, reviewer_role=role, reviewer_session=session, payload=payload or REVIEW, task_id=task_id
        )

    def status_of(self, version_id: str) -> str:
        node = self.store.get_version(version_id)["node_id"]
        current = self.store.current(node)
        assert current is not None
        return current["status"]

    def payload_of(self, version_id: str) -> dict[str, Any]:
        return self.store.get_version(version_id)["payload"]


# --------------------------------------------------------------------------------------------------
# Reviews and independence
# --------------------------------------------------------------------------------------------------


class ReviewIndependence(DecisionsCase):
    def test_author_cannot_review_own_artifact(self) -> None:
        _, artifact = self.add_artifact()
        with self.assertRaises(PolicyError) as ctx:
            self.review([artifact], role="prototype-engineer", session="sess-other")
        self.assertEqual("author_cannot_review_own_artifact", ctx.exception.details["reason"])
        self.assertEqual("conflict", ctx.exception.details["conflict_check"])
        self.assertEqual([], self.store.find_current("review"))

    def test_proposal_author_cannot_review_own_proposal(self) -> None:
        _, proposal = self.add_proposal()
        with self.assertRaises(PolicyError) as ctx:
            self.review([proposal], role="workflow-architect", session="sess-fresh")
        self.assertEqual("author_cannot_review_own_artifact", ctx.exception.details["reason"])

    def test_same_session_is_conflict(self) -> None:
        _, artifact = self.add_artifact(producer_session="sess-shared")
        with self.assertRaises(PolicyError) as ctx:
            self.review([artifact], role="test-engineer", session="sess-shared")
        self.assertEqual("same_session_conflict", ctx.exception.details["reason"])
        self.assertEqual("conflict", ctx.exception.details["conflict_check"])

    def test_same_native_child_id_from_dispatch_is_conflict(self) -> None:
        _, artifact = self.add_artifact(producer_session=None)
        self.store.insert("dispatches", {"run_id": self.run_id, "task_id": "task_build", "native_child_id": "child-77", "execution_mode": "native", "observed_by": "controller"})
        with self.assertRaises(PolicyError) as ctx:
            self.review([artifact], role="test-engineer", session="child-77")
        self.assertEqual("same_session_conflict", ctx.exception.details["reason"])

    def test_unknown_producer_origin_is_stored_unverified(self) -> None:
        _, artifact = self.add_artifact(producer_session=None)
        version = self.review([artifact], role="test-engineer", session="sess-reviewer")
        record = self.payload_of(version)
        self.assertEqual("unverified", record["conflict_check"])
        self.assertFalse(record["independent"])
        self.assertEqual("ready", self.status_of(version))

    def test_unknown_reviewer_session_is_stored_unverified(self) -> None:
        _, artifact = self.add_artifact()
        version = self.review([artifact], role="test-engineer", session=None)
        self.assertEqual("unverified", self.payload_of(version)["conflict_check"])

    def test_distinct_known_sessions_are_verified_and_independent(self) -> None:
        _, artifact = self.add_artifact()
        version = self.review([artifact], role="security-reviewer", session="sess-sec")
        record = self.payload_of(version)
        self.assertEqual("verified", record["conflict_check"])
        self.assertTrue(record["independent"])
        self.assertEqual("security-reviewer", record["reviewer_role"])
        self.assertEqual("sess-sec", record["reviewer_session"])

    def test_manager_review_of_own_team_is_recorded_not_independent(self) -> None:
        _, artifact = self.add_artifact()
        version = self.review([artifact], role="engineering-manager", session="sess-mgr")
        record = self.payload_of(version)
        self.assertEqual("verified", record["conflict_check"])
        self.assertFalse(record["independent"])
        events = [e for e in self.store.events(type="review.submitted")]
        self.assertTrue(events[-1].payload["manager_review"])

    def test_caller_cannot_set_conflict_check_or_independent(self) -> None:
        _, artifact = self.add_artifact(producer_session=None)
        version = self.review([artifact], session="sess-reviewer", payload={**REVIEW, "conflict_check": "verified", "independent": True})
        record = self.payload_of(version)
        self.assertEqual("unverified", record["conflict_check"])
        self.assertFalse(record["independent"])

    def test_pass_citing_unexecuted_check_is_refused(self) -> None:
        _, artifact = self.add_artifact()
        passing = {**REVIEW, "result": "pass", "observed_checks": [{"command": "python3 -m unittest", "claimed_exit_status": 0}]}
        with self.assertRaises(PolicyError) as ctx:
            self.review([artifact], payload=passing)
        self.assertEqual("review_cites_unexecuted_check", ctx.exception.details["reason"])
        self.assertEqual("missing_receipt_id", ctx.exception.details["cause"])

    def test_pass_citing_unknown_receipt_is_refused(self) -> None:
        _, artifact = self.add_artifact()
        passing = {**REVIEW, "result": "pass", "observed_checks": [{"command": "pytest", "receipt_id": "rcpt_nothing"}]}
        with self.assertRaises(PolicyError) as ctx:
            self.review([artifact], payload=passing)
        self.assertEqual("unknown_receipt", ctx.exception.details["cause"])

    def test_pass_citing_check_shaped_finding_without_receipt_is_refused(self) -> None:
        _, artifact = self.add_artifact()
        passing = {**REVIEW, "result": "pass", "findings": [{"command": "make test", "claimed_exit_status": 0}]}
        with self.assertRaises(PolicyError):
            self.review([artifact], payload=passing)

    def test_pass_with_stored_receipt_is_recorded_with_evidence_ref(self) -> None:
        _, artifact = self.add_artifact()
        self.store.put_receipt(receipt("rcpt_real"))
        passing = {**REVIEW, "result": "pass", "observed_checks": [{"command": ["python3", "-c", "pass"], "receipt_id": "rcpt_real"}]}
        version = self.review([artifact], payload=passing)
        record = self.payload_of(version)
        self.assertEqual("pass", record["result"])
        self.assertIn("rcpt_real", record["evidence_refs"])
        self.assertNotIn("observed_checks", record)
        self.assertEqual("pass", self.status_of(version))

    def test_non_pass_result_may_cite_claimed_checks(self) -> None:
        _, artifact = self.add_artifact()
        revise = {**REVIEW, "result": "revise", "observed_checks": [{"command": "pytest"}]}
        version = self.review([artifact], payload=revise)
        self.assertEqual("revise", self.payload_of(version)["result"])

    def test_review_with_assigned_task_marks_task_reviewed(self) -> None:
        _, artifact = self.add_artifact()
        task_id = self.store.insert("tasks", {"run_id": self.run_id, "role_id": "test-engineer", "state": "submitted"})
        version = self.review([artifact], task_id=task_id)
        self.assertEqual([(task_id, version)], self.controller.calls)
        self.assertEqual(task_id, self.store.get_version(version)["author_task"])

    def test_review_of_task_assigned_to_other_role_is_refused(self) -> None:
        _, artifact = self.add_artifact()
        task_id = self.store.insert("tasks", {"run_id": self.run_id, "role_id": "security-reviewer", "state": "submitted"})
        with self.assertRaises(PolicyError) as ctx:
            self.review([artifact], role="test-engineer", task_id=task_id)
        self.assertEqual("review_not_assigned", ctx.exception.details["reason"])
        self.assertEqual([], self.controller.calls)

    def test_review_requires_known_role_and_existing_refs(self) -> None:
        _, artifact = self.add_artifact()
        with self.assertRaises(PolicyError):
            self.review([artifact], role="nobody-here")
        with self.assertRaises(NotFoundError):
            self.review(["ver_missing"])
        with self.assertRaises(ValidationError):
            self.review([])
        with self.assertRaises(NotFoundError):
            self.review([artifact], payload={**REVIEW, "evidence_refs": ["ver_ghost"]})


# --------------------------------------------------------------------------------------------------
# Challenges
# --------------------------------------------------------------------------------------------------


class Challenges(DecisionsCase):
    def challenge(self, contested: str, **overrides: Any) -> str:
        return self.decisions.open_challenge(self.case_id, self.run_id, {**CHALLENGE, "contested_ref": contested, **overrides})

    def test_challenge_round_cap_for_standard_mode(self) -> None:
        _, proposal = self.add_proposal()
        first = self.challenge(proposal)
        self.assertEqual(1, self.payload_of(first)["round"])
        self.assertEqual("open", self.status_of(first))
        self.assertEqual(1, self.decisions.rounds_used(self.run_id))
        self.challenge(proposal, round=1, premise="A second material objection in the same round.")
        self.assertEqual(1, self.decisions.rounds_used(self.run_id))
        with self.assertRaises(BudgetExhausted) as ctx:
            self.challenge(proposal, round=2)
        self.assertEqual("max_challenge_rounds", ctx.exception.details["reason"])
        self.assertEqual(1, ctx.exception.partial_state["rounds_used"])
        self.assertEqual(1, ctx.exception.partial_state["max_challenge_rounds"])

    def test_focused_mode_allows_no_challenge_rounds(self) -> None:
        _, proposal = self.add_proposal()
        focused = self.store.insert("runs", {"mode": "focused", "state": "executing", "workflow_id": "W01"})
        with self.assertRaises(BudgetExhausted) as ctx:
            self.decisions.open_challenge(self.case_id, focused, {**CHALLENGE, "contested_ref": proposal})
        self.assertEqual(0, ctx.exception.details["max_challenge_rounds"])

    def test_deep_mode_allows_two_consecutive_rounds(self) -> None:
        _, proposal = self.add_proposal()
        deep = self.store.insert("runs", {"mode": "deep", "state": "executing", "workflow_id": "W11"})
        with self.assertRaises(ValidationError) as ctx:
            self.decisions.open_challenge(self.case_id, deep, {**CHALLENGE, "contested_ref": proposal, "round": 2})
        self.assertEqual("round_not_consecutive", ctx.exception.details["reason"])
        self.decisions.open_challenge(self.case_id, deep, {**CHALLENGE, "contested_ref": proposal})
        second = self.decisions.open_challenge(self.case_id, deep, {**CHALLENGE, "contested_ref": proposal, "round": 2})
        self.assertEqual(2, self.payload_of(second)["round"])
        self.assertEqual(2, self.decisions.rounds_used(deep))
        self.assertEqual(0, self.decisions.rounds_used(self.run_id))
        with self.assertRaises(BudgetExhausted):
            self.decisions.open_challenge(self.case_id, deep, {**CHALLENGE, "contested_ref": proposal, "round": 3})

    def test_rounds_are_synced_into_budget_row_when_present(self) -> None:
        _, proposal = self.add_proposal()
        self.store.insert("budgets", {"run_id": self.run_id, "mode": "standard", "max_challenge_rounds": 1, "used_rounds": 0, "used_tasks": 0, "running": 0})
        self.challenge(proposal)
        self.assertEqual(1, self.store.get("budgets", self.run_id)["used_rounds"])

    def test_empty_material_field_is_refused(self) -> None:
        _, proposal = self.add_proposal()
        for field in ("premise", "counterevidence_or_gap", "consequence", "resolving_test"):
            with self.subTest(field=field):
                with self.assertRaises(ValidationError) as ctx:
                    self.challenge(proposal, **{field: "   "})
                self.assertEqual("empty_material_field", ctx.exception.details["reason"])
                self.assertEqual(field, ctx.exception.details["field"])
        with self.assertRaises(ValidationError):
            self.decisions.open_challenge(self.case_id, self.run_id, {k: v for k, v in {**CHALLENGE, "contested_ref": proposal}.items() if k != "consequence"})
        with self.assertRaises(ValidationError):
            self.challenge("")
        self.assertEqual([], self.store.find_current("challenge"))

    def test_challenge_needs_existing_run_and_contested_version(self) -> None:
        _, proposal = self.add_proposal()
        with self.assertRaises(NotFoundError):
            self.decisions.open_challenge(self.case_id, "run_missing", {**CHALLENGE, "contested_ref": proposal})
        with self.assertRaises(NotFoundError):
            self.challenge("ver_missing")

    def test_respond_challenge_owner_only(self) -> None:
        _, proposal = self.add_proposal()
        challenge = self.challenge(proposal)
        with self.assertRaises(PolicyError) as ctx:
            self.decisions.respond_challenge(challenge, {"response": "Not mine to answer."}, by="assumption-challenger")
        self.assertEqual("not_proposal_owner", ctx.exception.details["reason"])
        self.assertEqual("open", self.status_of(challenge))

    def test_respond_challenge_records_answer(self) -> None:
        _, proposal = self.add_proposal()
        challenge = self.challenge(proposal)
        result = self.decisions.respond_challenge(challenge, {"response": "Reasoned disagreement: the FAQ is a closed set."}, by="workflow-architect")
        answered = self.payload_of(result["challenge_version"])
        self.assertEqual("answered", answered["state"])
        self.assertEqual("workflow-architect", answered["responded_by"])
        self.assertIsNone(result["proposal_version"])
        node = self.store.get_version(challenge)["node_id"]
        self.assertEqual(result["challenge_version"], self.store.current(node)["version_id"])
        self.assertEqual("answered", self.store.current(node)["status"])
        with self.assertRaises(ConflictError):
            self.decisions.respond_challenge(challenge, {"response": "again"}, by="workflow-architect")
        with self.assertRaises(TransitionError):
            self.decisions.respond_challenge(result["challenge_version"], {"response": "again"}, by="workflow-architect")

    def test_respond_challenge_with_revision_supersedes_proposal(self) -> None:
        node, proposal = self.add_proposal()
        challenge = self.challenge(proposal)
        revision = {**PROPOSAL, "title": "Retrieval strategy, revised", "recommended_option": "B", "requested_authority": "R0"}
        result = self.decisions.respond_challenge(challenge, {"response": "Revised toward hybrid search.", "revision": revision}, by="workflow-architect")
        new_version = result["proposal_version"]
        self.assertIsNotNone(new_version)
        self.assertEqual(new_version, self.store.current(node)["version_id"])
        self.assertEqual("R1", self.payload_of(new_version)["requested_authority"], "a revision cannot lower the requested authority")
        edges = self.store.edges_from(new_version, "supersedes", status="accepted")
        self.assertEqual(1, len(edges))
        self.assertEqual(proposal, edges[0]["to_version"])
        with self.assertRaises(ValidationError):
            self.decisions.respond_challenge(
                self.challenge(new_version, round=1), {"response": "bad", "revision": {**PROPOSAL, "recommended_option": "Z"}}, by="workflow-architect"
            )


# --------------------------------------------------------------------------------------------------
# Rulings
# --------------------------------------------------------------------------------------------------


class Rulings(DecisionsCase):
    def ruling(self, refs: list[str], *, judge: str = "convergence-judge", **overrides: Any) -> str:
        return self.decisions.submit_ruling(self.case_id, judge_role=judge, payload={**RULING, "scope": {"question": "A or B?", "refs": refs}, **overrides})

    def test_only_judge_types_may_rule(self) -> None:
        _, proposal = self.add_proposal()
        for role in ("review-manager", "decision-authority", "context-analyst", "human-owner", "nobody"):
            with self.subTest(role=role):
                with self.assertRaises(PolicyError) as ctx:
                    self.ruling([proposal], judge=role)
                self.assertEqual("not_a_judge", ctx.exception.details["reason"])

    def test_judge_may_not_rule_on_own_proposal(self) -> None:
        _, proposal = self.add_proposal(author_role="convergence-judge", author_session="sess-judge")
        with self.assertRaises(PolicyError) as ctx:
            self.ruling([proposal])
        self.assertEqual("judge_authored_proposal", ctx.exception.details["reason"])
        self.assertEqual([], self.store.find_current("review"))

    def test_ruling_is_recorded_and_changes_no_other_status(self) -> None:
        _, proposal = self.add_proposal()
        _, artifact = self.add_artifact()
        decision = self.add_decision(proposal)
        version = self.ruling([proposal, decision, artifact], outcome="option_acceptable", judge_session="sess-judge")
        record = self.payload_of(version)
        self.assertEqual("convergence-judge", record["reviewer_role"])
        self.assertEqual("pass", record["result"])
        self.assertEqual("ruling", record["findings"][0]["record_type"])
        self.assertEqual("option_acceptable", record["findings"][0]["outcome"])
        self.assertEqual(["Run the paraphrase fixture set.", "Alternative advocate prefers B."], record["unresolved"])
        self.assertEqual("option_acceptable", self.status_of(version))
        self.assertEqual("proposed", self.status_of(decision))
        self.assertEqual("proposed", self.status_of(proposal))
        self.assertEqual("implemented_not_verified", self.status_of(artifact))
        events = self.store.events(type="ruling.submitted")
        self.assertFalse(events[-1].payload["changes_other_status"])

    def test_ruling_outcome_and_fields_validated(self) -> None:
        _, proposal = self.add_proposal()
        with self.assertRaises(ValidationError):
            self.ruling([proposal], outcome="approved")
        with self.assertRaises(ValidationError):
            self.decisions.submit_ruling(self.case_id, judge_role="evidence-judge", payload={k: v for k, v in RULING.items() if k != "criteria"})
        with self.assertRaises(ValidationError):
            self.decisions.submit_ruling(self.case_id, judge_role="evidence-judge", payload={**RULING, "scope": "which option?"})
        with self.assertRaises(NotFoundError):
            self.ruling([proposal], admissible_evidence=["ver_ghost"])

    def test_ruling_independence_follows_review_rules(self) -> None:
        _, proposal = self.add_proposal()
        unverified = self.ruling([proposal])
        self.assertEqual("unverified", self.payload_of(unverified)["conflict_check"])
        verified = self.ruling([proposal], judge="evidence-judge", judge_session="sess-ej", outcome="insufficient_evidence")
        record = self.payload_of(verified)
        self.assertEqual("verified", record["conflict_check"])
        self.assertEqual("insufficient", record["evidence_sufficiency"])
        self.assertEqual("blocked", record["result"])
        with self.assertRaises(PolicyError) as ctx:
            self.ruling([proposal], judge_session="sess-architect")
        self.assertEqual("same_session_conflict", ctx.exception.details["reason"])


# --------------------------------------------------------------------------------------------------
# Proposals, approvals and acceptance
# --------------------------------------------------------------------------------------------------


class ProposeAndRecord(DecisionsCase):
    def test_propose_decision_checks_option_and_floors_authority(self) -> None:
        _, proposal = self.add_proposal()
        with self.assertRaises(ValidationError):
            self.add_decision(proposal, selected_option="Z")
        with self.assertRaises(ValidationError):
            self.add_decision(proposal, selected_option=None)
        with self.assertRaises(NotFoundError):
            self.add_decision(proposal, proposal_version_id="ver_missing")
        decision = self.add_decision(proposal, requested_authority="R0")
        record = self.payload_of(decision)
        self.assertEqual("R1", record["requested_authority"])
        self.assertEqual("proposed", record["status"])
        self.assertEqual("proposed", self.status_of(decision))
        self.assertEqual(["Alternative advocate prefers B."], record["dissent"])

    def test_propose_decision_requires_known_role_and_proposal_kind(self) -> None:
        _, artifact = self.add_artifact()
        _, proposal = self.add_proposal()
        with self.assertRaises(PolicyError):
            self.add_decision(proposal, by="nobody")
        with self.assertRaises(ValidationError):
            self.add_decision(artifact)

    def test_record_user_input_sets_attested_from_channel_only(self) -> None:
        _, proposal = self.add_proposal()
        cli = self.add_approval(proposal, granted_by="human-owner", channel="cli", provenance={"channel": "host_user_input", "attested": True, "note": "typed"})
        record = self.payload_of(cli)
        self.assertEqual({"channel": "cli", "attested": False, "note": "typed"}, record["provenance"])
        self.assertEqual("unverified_claim", self.status_of(cli))
        host = self.add_approval(proposal, granted_by="human-owner", channel="host_user_input", provenance={"attested": False})
        self.assertEqual({"channel": "host_user_input", "attested": True}, self.payload_of(host)["provenance"])
        self.assertEqual("attested", self.status_of(host))
        file_ = self.add_approval(proposal, granted_by="human-owner", channel="file")
        self.assertFalse(self.payload_of(file_)["provenance"]["attested"])
        events = self.store.events(type="approval.recorded")
        self.assertEqual(True, events[0].payload["caller_supplied_attested"])
        self.assertEqual(False, events[0].payload["attested"])
        with self.assertRaises(ValidationError):
            self.add_approval(proposal, channel="telepathy")
        with self.assertRaises(NotFoundError):
            self.add_approval("ver_missing")

    def test_revoke_approval_appends_revoked_version(self) -> None:
        _, proposal = self.add_proposal()
        approval = self.add_approval(proposal)
        revoked = self.decisions.revoke_approval(approval, channel="cli", note="owner changed scope")
        self.assertTrue(self.payload_of(revoked)["revoked"])
        self.assertEqual("revoked", self.status_of(approval))
        self.assertFalse(self.payload_of(approval)["revoked"], "the original version is immutable")


class AcceptDecision(DecisionsCase):
    def test_judge_manager_specialist_cannot_accept(self) -> None:
        _, proposal = self.add_proposal()
        decision = self.add_decision(proposal)
        approval = self.add_approval(proposal)
        for role in ("convergence-judge", "evidence-judge", "engineering-manager", "review-manager", "context-analyst", "independent-auditor", "workflow-orchestrator"):
            with self.subTest(role=role):
                with self.assertRaises(PolicyError) as ctx:
                    self.decisions.accept_decision(decision, by=role, approval_version=approval)
                self.assertEqual("role_cannot_accept", ctx.exception.details["reason"])
        self.assertEqual("proposed", self.status_of(decision))

    def test_decision_authority_needs_delegation_bound_to_exact_version(self) -> None:
        _, proposal = self.add_proposal()
        _, other = self.add_proposal(title="Another proposal")
        decision = self.add_decision(proposal)
        with self.assertRaises(PolicyError) as ctx:
            self.decisions.accept_decision(decision, by="decision-authority")
        self.assertEqual("delegation_required", ctx.exception.details["reason"])
        human_grant = self.add_approval(proposal, granted_by="human-owner", channel="host_user_input")
        with self.assertRaises(PolicyError) as ctx:
            self.decisions.accept_decision(decision, by="decision-authority", approval_version=human_grant)
        self.assertEqual("delegation_required", ctx.exception.details["reason"])
        wrong_target = self.add_approval(other)
        with self.assertRaises(PolicyError) as ctx:
            self.decisions.accept_decision(decision, by="decision-authority", approval_version=wrong_target)
        self.assertEqual("approval_version_mismatch", ctx.exception.details["reason"])
        narrow = self.add_approval(proposal, allowed_decisions=["R0"])
        with self.assertRaises(PolicyError) as ctx:
            self.decisions.accept_decision(decision, by="decision-authority", approval_version=narrow)
        self.assertEqual("decision_outside_delegation", ctx.exception.details["reason"])
        unscoped = self.add_approval(proposal, scope="")
        with self.assertRaises(PolicyError) as ctx:
            self.decisions.accept_decision(decision, by="decision-authority", approval_version=unscoped)
        self.assertEqual("scope_not_recorded", ctx.exception.details["reason"])
        self.assertEqual("proposed", self.status_of(decision))

    def test_delegated_acceptance_succeeds_without_execution_permission(self) -> None:
        _, evidence = self.add_artifact()
        node, proposal = self.add_proposal(evidence_refs=[evidence])
        decision = self.add_decision(proposal)
        approval = self.add_approval(proposal)
        result = self.decisions.accept_decision(decision, by="decision-authority", approval_version=approval)
        self.assertIs(False, result["execution_permission"])
        self.assertEqual("accepted", result["status"])
        self.assertEqual("delegation", result["authority_basis"])
        self.assertEqual(["Alternative advocate prefers B."], result["dissent"])
        accepted = result["accepted_version"]
        self.assertNotEqual(decision, accepted)
        decision_node = self.store.get_version(decision)["node_id"]
        self.assertEqual(accepted, self.store.current(decision_node)["version_id"])
        self.assertEqual("accepted", self.store.current(decision_node)["status"])
        record = self.payload_of(accepted)
        self.assertEqual("accepted", record["status"])
        self.assertEqual({"kind": "delegation", "approval_version_id": approval}, record["authority_basis"])
        self.assertEqual(["Alternative advocate prefers B."], record["dissent"])
        self.assertEqual("proposed", self.payload_of(decision)["status"], "earlier versions are never rewritten")
        edges = self.store.edges_from(accepted, "depends_on", status="proposed")
        self.assertEqual({proposal, evidence}, {e["to_version"] for e in edges})
        self.assertTrue(all(e["impact_policy"] == "review" for e in edges))
        event = self.store.events(type="decision.accepted")[-1]
        self.assertIs(False, event.payload["execution_permission"])
        self.assertEqual(approval, event.payload["approval_version"])

    def test_changed_proposal_version_invalidates_approval_at_09(self) -> None:
        node, v1 = self.add_proposal()
        decision = self.add_decision(v1)
        approval = self.add_approval(v1)
        v2 = self.store.put_version(node, {**PROPOSAL, "title": "Revised"}, author_role="workflow-architect")
        self.store.set_current(node, v2, status="proposed")
        with self.assertRaises(PolicyError) as ctx:
            self.decisions.accept_decision(decision, by="decision-authority", approval_version=approval)
        self.assertEqual("proposal_superseded", ctx.exception.details["reason"])
        self.assertEqual(v2, ctx.exception.details["current_version_id"])
        decision_v2 = self.add_decision(v2)
        with self.assertRaises(PolicyError) as ctx:
            self.decisions.accept_decision(decision_v2, by="decision-authority", approval_version=approval)
        self.assertEqual("approval_version_mismatch", ctx.exception.details["reason"])
        self.assertEqual("proposed", self.status_of(decision))
        self.assertEqual("proposed", self.status_of(decision_v2))

    def test_revision_via_challenge_response_invalidates_approval(self) -> None:
        _, v1 = self.add_proposal()
        decision = self.add_decision(v1)
        approval = self.add_approval(v1)
        challenge = self.decisions.open_challenge(self.case_id, self.run_id, {**CHALLENGE, "contested_ref": v1})
        self.decisions.respond_challenge(challenge, {"response": "Revised.", "revision": {**PROPOSAL, "title": "v2"}}, by="workflow-architect")
        with self.assertRaises(PolicyError) as ctx:
            self.decisions.accept_decision(decision, by="decision-authority", approval_version=approval)
        self.assertEqual("proposal_superseded", ctx.exception.details["reason"])

    def test_expired_and_revoked_approvals_are_refused(self) -> None:
        _, proposal = self.add_proposal()
        decision = self.add_decision(proposal)
        expired = self.add_approval(proposal, expires_at=LONG_AGO)
        with self.assertRaises(PolicyError) as ctx:
            self.decisions.accept_decision(decision, by="decision-authority", approval_version=expired)
        self.assertEqual("approval_expired", ctx.exception.details["reason"])
        revoked = self.add_approval(proposal, revoked=True)
        with self.assertRaises(PolicyError) as ctx:
            self.decisions.accept_decision(decision, by="decision-authority", approval_version=revoked)
        self.assertEqual("approval_revoked", ctx.exception.details["reason"])
        later_revoked = self.add_approval(proposal)
        self.decisions.revoke_approval(later_revoked, channel="cli")
        with self.assertRaises(PolicyError) as ctx:
            self.decisions.accept_decision(decision, by="decision-authority", approval_version=later_revoked)
        self.assertEqual("approval_revoked", ctx.exception.details["reason"])
        no_expiry = self.add_approval(proposal, expires_at=None)
        result = self.decisions.accept_decision(decision, by="decision-authority", approval_version=no_expiry)
        self.assertEqual("accepted", result["status"])

    def test_r2_requires_human_and_sets_human_required(self) -> None:
        _, proposal = self.add_proposal(requested_authority="R2")
        decision = self.add_decision(proposal)
        approval = self.add_approval(proposal)
        with self.assertRaises(PolicyError) as ctx:
            self.decisions.accept_decision(decision, by="decision-authority", approval_version=approval)
        self.assertEqual("human_required", ctx.exception.details["reason"])
        self.assertEqual("human_required", self.status_of(decision))
        with self.assertRaises(PolicyError) as ctx:
            self.decisions.accept_decision(decision, by="decision-authority")
        self.assertEqual("human_required", ctx.exception.details["reason"])

    def test_cli_channel_human_input_is_unattested_and_refused(self) -> None:
        _, proposal = self.add_proposal(requested_authority="R2")
        decision = self.add_decision(proposal)
        delegation = self.add_approval(proposal)
        with self.assertRaises(PolicyError):
            self.decisions.accept_decision(decision, by="decision-authority", approval_version=delegation)
        self.assertEqual("human_required", self.status_of(decision))
        cli_grant = self.add_approval(proposal, granted_by="human-owner", channel="cli")
        with self.assertRaises(PolicyError) as ctx:
            self.decisions.accept_decision(decision, by="human-owner", approval_version=cli_grant)
        self.assertEqual("unattested_human_input", ctx.exception.details["reason"])
        self.assertEqual("cli", ctx.exception.details["channel"])
        self.assertEqual("human_required", self.status_of(decision))
        file_grant = self.add_approval(proposal, granted_by="human-owner", channel="file")
        with self.assertRaises(PolicyError) as ctx:
            self.decisions.accept_decision(decision, by="human-owner", approval_version=file_grant)
        self.assertEqual("unattested_human_input", ctx.exception.details["reason"])
        with self.assertRaises(PolicyError) as ctx:
            self.decisions.accept_decision(decision, by="human-owner", approval_version=delegation)
        self.assertEqual("approval_not_from_human", ctx.exception.details["reason"])
        with self.assertRaises(PolicyError) as ctx:
            self.decisions.accept_decision(decision, by="human-owner")
        self.assertEqual("approval_required", ctx.exception.details["reason"])
        self.assertEqual("human_required", self.status_of(decision))

    def test_attested_human_input_accepts_r2_after_independent_review(self) -> None:
        _, proposal = self.add_proposal(requested_authority="R2")
        decision = self.add_decision(proposal)
        host_grant = self.add_approval(proposal, granted_by="human-owner", channel="host_user_input")
        with self.assertRaises(PolicyError) as ctx:
            self.decisions.accept_decision(decision, by="human-owner", approval_version=host_grant)
        self.assertEqual("independent_review_required", ctx.exception.details["reason"])
        self.review([proposal], role="systems-manager", session="sess-mgr")
        with self.assertRaises(PolicyError) as ctx:
            self.decisions.accept_decision(decision, by="human-owner", approval_version=host_grant)
        self.assertEqual("independent_review_required", ctx.exception.details["reason"], "a manager review is not an independent review")
        self.review([proposal], role="security-reviewer", session=None)
        with self.assertRaises(PolicyError):
            self.decisions.accept_decision(decision, by="human-owner", approval_version=host_grant)
        self.review([proposal], role="security-reviewer", session="sess-sec")
        result = self.decisions.accept_decision(decision, by="human-owner", approval_version=host_grant)
        self.assertEqual("accepted", result["status"])
        self.assertEqual("human_input", result["authority_basis"])
        self.assertIs(False, result["execution_permission"])
        self.assertEqual("R2", result["risk_tier"])
        self.assertEqual("accepted", self.status_of(result["accepted_version"]))

    def test_human_accepts_r1_with_attested_input(self) -> None:
        _, proposal = self.add_proposal()
        decision = self.add_decision(proposal)
        host_grant = self.add_approval(proposal, granted_by="human-owner", channel="host_user_input", allowed_decisions=[])
        result = self.decisions.accept_decision(decision, by="human-owner", approval_version=host_grant)
        self.assertEqual("accepted", result["status"])
        self.assertIs(False, result["execution_permission"])

    def test_r3_has_no_accept_path(self) -> None:
        _, proposal = self.add_proposal(requested_authority="R3")
        decision = self.add_decision(proposal)
        host_grant = self.add_approval(proposal, granted_by="human-owner", channel="host_user_input", allowed_decisions=["R3"])
        delegation = self.add_approval(proposal, allowed_decisions=["R3"])
        for by, grant in (("human-owner", host_grant), ("decision-authority", delegation), ("product-director", host_grant)):
            with self.subTest(by=by):
                with self.assertRaises(PolicyError) as ctx:
                    self.decisions.accept_decision(decision, by=by, approval_version=grant)
                self.assertEqual("r3_no_accept_path", ctx.exception.details["reason"])
        self.assertEqual("proposed", self.status_of(decision))
        self.assertEqual([], self.store.events(type="decision.accepted"))

    def test_accept_refuses_stale_or_terminal_decisions(self) -> None:
        _, proposal = self.add_proposal()
        decision = self.add_decision(proposal)
        approval = self.add_approval(proposal)
        node = self.store.get_version(decision)["node_id"]
        self.store.set_current(node, decision, status="rejected")
        with self.assertRaises(TransitionError):
            self.decisions.accept_decision(decision, by="decision-authority", approval_version=approval)
        self.store.set_current(node, decision, status="proposed")
        result = self.decisions.accept_decision(decision, by="decision-authority", approval_version=approval)
        with self.assertRaises(ConflictError) as ctx:
            self.decisions.accept_decision(decision, by="decision-authority", approval_version=approval)
        self.assertEqual("decision_version_not_current", ctx.exception.details["reason"])
        with self.assertRaises(TransitionError):
            self.decisions.accept_decision(result["accepted_version"], by="decision-authority", approval_version=approval)
        with self.assertRaises(ValidationError):
            self.decisions.accept_decision(proposal, by="decision-authority", approval_version=approval)


# --------------------------------------------------------------------------------------------------
# Authority
# --------------------------------------------------------------------------------------------------


class Authority(DecisionsCase):
    def test_execute_on_r3_is_refused_for_everyone(self) -> None:
        roles = ["human-owner", "decision-authority", *sorted(self.registry.agents)]
        for role in roles:
            with self.subTest(role=role):
                with self.assertRaises(PolicyError) as ctx:
                    self.decisions.authority_check(role, "execute", "R3")
                self.assertEqual("tier_not_executable", ctx.exception.details["reason"])

    def test_accept_on_r3_is_refused_for_everyone(self) -> None:
        for role in ("human-owner", "decision-authority", "product-director", "convergence-judge"):
            with self.subTest(role=role):
                with self.assertRaises(PolicyError) as ctx:
                    self.decisions.authority_check(role, "accept", "R3")
                self.assertEqual("r3_no_accept_path", ctx.exception.details["reason"])

    def test_rights_follow_authority_policy(self) -> None:
        self.assertIsNone(self.decisions.authority_check("convergence-judge", "adjudicate", "R1"))
        self.assertIsNone(self.decisions.authority_check("context-analyst", "propose", "R0"))
        self.assertIsNone(self.decisions.authority_check("human-owner", "accept", "R2"))
        self.assertIsNone(self.decisions.authority_check("decision-authority", "accept", "R1"))
        self.assertIsNone(self.decisions.authority_check("prototype-engineer", "execute", "R1"))
        for role, action in (("convergence-judge", "accept"), ("engineering-manager", "accept"), ("context-analyst", "adjudicate"), ("convergence-judge", "execute"), ("review-manager", "execute")):
            with self.subTest(role=role, action=action):
                with self.assertRaises(PolicyError) as ctx:
                    self.decisions.authority_check(role, action, "R1")
                self.assertEqual(f"{action}_not_permitted", ctx.exception.details["reason"])
        with self.assertRaises(PolicyError) as ctx:
            self.decisions.authority_check("nobody", "propose", "R0")
        self.assertEqual("unknown_principal", ctx.exception.details["reason"])
        with self.assertRaises(ValidationError):
            self.decisions.authority_check("human-owner", "deploy", "R0")
        with self.assertRaises(ValidationError):
            self.decisions.authority_check("human-owner", "propose", "R9")

    def test_module_contains_no_execution_primitives(self) -> None:
        source = Path(D.__file__).read_text(encoding="utf-8")
        for forbidden in ("subprocess", "os.system", "os.popen", "os.exec", "urllib", "socket", "shutil.rmtree", "os.remove"):
            self.assertNotIn(forbidden, source, forbidden)


if __name__ == "__main__":
    unittest.main()
