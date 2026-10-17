"""Unit tests for ai_product_team.lineage (contract section 7, section 13 "test_lineage").

Covers: depends_on requires impact_policy (and other relations refuse one); impact reaches declared,
accepted dependents only, in deterministic order; invalidate vs review vs none; a protected requirement
survives a failed implementation (AT-13); contradiction -> contested, never unsupported; accept_correction
needs a bound review; mark_historical keeps the result; coverage and missing_lineage; every mutation is an
event inside a transaction. Every test uses a real CaseStore in tempfile.TemporaryDirectory(), the real
Registry and the real Policies loaded from the repository; nothing writes into the repository tree.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ai_product_team import lineage as L
from ai_product_team.errors import ConflictError, NotFoundError, PolicyError, TransitionError, ValidationError
from ai_product_team.policies import Policies
from ai_product_team.registry import Registry
from ai_product_team.storage import CaseStore

REPO = Path(__file__).resolve().parents[2]
TS = "2026-10-16T12:00:00Z"

SOURCE = {
    "id": "src-isolation-spec",
    "title": "Workspace isolation spec",
    "locator": "docs/isolation.md",
    "locator_type": "local",
    "observed_at": TS,
    "content_hash": "ab" * 32,
    "access_scope": "synthetic",
    "authority_type": "primary",
    "limitations": [],
}
CLAIM = {
    "statement": "Retrieval only exposes documents authorised for the requesting workspace.",
    "claim_type": "fact",
    "status": "supported",
    "supporting_refs": [],
    "contrary_refs": [],
    "confidence_label": "high",
    "assessed_by": "claim-checker",
}
REQUIREMENT = {
    "statement": "Retrieval must not expose documents outside the requesting workspace.",
    "owner": "human-owner",
    "acceptance_criteria": ["Cross-workspace negative test passes."],
    "protected": True,
    "originating_refs": [],
    "status": "approved",
}
ARTIFACT = {
    "kind": "implementation",
    "path": "src/retrieval/filter.py",
    "content_hash": "cd" * 32,
    "producer_role": "integration-engineer",
    "producer_task": "task_impl",
    "write_scope": "assigned-worktree",
    "implements_refs": [],
    "status": "implemented_not_verified",
    "access_classification": "synthetic",
}
VALIDATION = {
    "method": "pytest tests/test_isolation.py",
    "target_refs": [],
    "receipt_id": "rcpt_positive",
    "result": "passed",
    "rubric": None,
    "coverage": "positive path only",
    "applicability": "current",
}
REVIEW = {
    "reviewed_refs": [],
    "reviewer_role": "research-manager",
    "reviewer_session": "sess_review_1",
    "findings": ["Negative test demonstrates leakage."],
    "evidence_sufficiency": "sufficient",
    "result": "revise",
    "conflict_check": "verified",
    "unresolved": [],
}
DECISION = {
    "proposal_version_id": "ver_proposal",
    "outcome": "accepted",
    "selected_option": "A",
    "criteria": ["Fits"],
    "rationale": "Reversible.",
    "dissent": [],
    "authority_basis": {"kind": "delegation", "approval_version_id": "ver_approval"},
    "revisit_conditions": [],
    "status": "accepted",
}


class LineageCase(unittest.TestCase):
    """One temporary store per test; real registry and policies shared across the class."""

    registry: Registry
    policies: Policies

    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = Registry.load(REPO)
        cls.policies = Policies.load(REPO)

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.store = CaseStore.create(
            self.tmp / "case", {"objective": "Synthetic support copilot", "owner": "human-owner", "source_scope": ["docs/"]}
        )
        self.case_id = self.store.case_id
        self.lineage = L.Lineage(self.store, self.registry, self.policies)

    def tearDown(self) -> None:
        self.store.close()
        self._tmp.cleanup()

    # -- fixture helpers -------------------------------------------------------------------------------

    def source(self, **overrides) -> tuple[str, str]:
        return self.lineage.add_source(self.case_id, {**SOURCE, **overrides}, by="context-analyst")

    def claim(self, **overrides) -> tuple[str, str]:
        return self.lineage.add_claim(self.case_id, {**CLAIM, **overrides}, by="claim-checker")

    def requirement(self, **overrides) -> tuple[str, str]:
        return self.lineage.add_requirement(self.case_id, {**REQUIREMENT, **overrides}, by="human-owner")

    def artifact(self, **overrides) -> tuple[str, str]:
        return self.lineage.add_artifact(self.case_id, {**ARTIFACT, **overrides}, by="integration-engineer")

    def validation(self, **overrides) -> tuple[str, str]:
        return self.lineage.add_validation(self.case_id, {**VALIDATION, **overrides}, by="test-engineer")

    def review(self, reviewed_refs: list[str], *, by: str = "research-manager", **overrides) -> str:
        node = self.store.new_node("review", self.case_id)
        version = self.store.put_version(node, {**REVIEW, "reviewed_refs": reviewed_refs, "reviewer_role": by, **overrides}, author_role=by)
        self.store.set_current(node, version, status="revise")
        return version

    def decision(self) -> tuple[str, str]:
        return self.lineage.add_record(self.case_id, "decision", dict(DECISION), by="decision-authority")

    def link(self, from_version: str, to_version: str, relation: str, *, impact_policy: str | None = None, accept: bool = True) -> str:
        edge = self.lineage.propose_link(
            from_version, to_version, relation, impact_policy=impact_policy, reason=f"{relation} declared in test", by="dependency-steward"
        )
        if accept:
            self.lineage.accept_link(edge, by="review-manager")
        return edge

    def event_types(self) -> list[str]:
        return [e.type for e in self.store.events()]


# --------------------------------------------------------------------------------------------------
# Records
# --------------------------------------------------------------------------------------------------


class Records(LineageCase):
    def test_add_source_claim_requirement_set_current_and_emit_events(self):
        src_node, src_version = self.source()
        claim_node, claim_version = self.claim()
        req_node, req_version = self.requirement()
        self.assertEqual("observed", self.store.current(src_node)["status"])
        self.assertEqual("supported", self.store.current(claim_node)["status"])
        current_req = self.store.current(req_node)
        self.assertEqual(("approved", "current", req_version), (current_req["status"], current_req["applicability"], current_req["version_id"]))
        self.assertEqual("claim", self.store.get_version(claim_version)["kind"])
        self.assertEqual("context-analyst", self.store.get_version(src_version)["author_role"])
        types = self.event_types()
        self.assertEqual(3, types.count("lineage.record_added"))
        self.assertEqual(3, types.count("node.current_changed"))
        self.assertEqual(6, self.store.state_version())

    def test_invalid_payload_is_refused_and_leaves_no_partial_write(self):
        with self.assertRaises(ValidationError):
            self.lineage.add_claim(self.case_id, {**CLAIM, "status": "done"}, by="claim-checker")
        self.assertEqual([], self.store.find_current("claim"))
        self.assertEqual(0, self.store.state_version())
        self.assertEqual(0, self.store.connection.execute("SELECT COUNT(*) FROM nodes").fetchone()[0])

    def test_unknown_case_and_unknown_actor_are_refused(self):
        with self.assertRaises(NotFoundError):
            self.lineage.add_claim("case_other", dict(CLAIM), by="claim-checker")
        with self.assertRaises(PolicyError) as ctx:
            self.lineage.add_claim(self.case_id, dict(CLAIM), by="nobody-in-registry")
        self.assertEqual("unknown_actor", ctx.exception.details["reason"])
        with self.assertRaises(ValidationError):
            self.lineage.add_claim(self.case_id, dict(CLAIM), by="")
        # human-owner and controller are always accepted actors.
        self.lineage.add_claim(self.case_id, dict(CLAIM), by="human-owner")
        self.lineage.add_claim(self.case_id, dict(CLAIM), by="controller")

    def test_validation_result_without_receipt_is_a_claim_not_a_validation(self):
        with self.assertRaises(PolicyError) as ctx:
            self.validation(receipt_id=None)
        self.assertEqual("result_without_receipt", ctx.exception.details["reason"])
        node, _ = self.validation(receipt_id=None, result="not_run")
        self.assertEqual("not_run", self.store.current(node)["status"])

    def test_add_record_new_version_of_existing_node(self):
        node, v1 = self.claim()
        node2, v2 = self.lineage.add_record(self.case_id, "claim", {**CLAIM, "confidence_label": "medium"}, by="claim-checker", node_id=node)
        self.assertEqual(node, node2)
        self.assertNotEqual(v1, v2)
        self.assertEqual(v2, self.store.current(node)["version_id"])
        self.assertEqual([v1, v2], [v["id"] for v in self.store.versions_of(node)])
        with self.assertRaises(ValidationError):
            self.lineage.add_record(self.case_id, "requirement", dict(REQUIREMENT), by="human-owner", node_id=node)


# --------------------------------------------------------------------------------------------------
# Links
# --------------------------------------------------------------------------------------------------


class Links(LineageCase):
    def test_depends_on_requires_impact_policy(self):
        _, claim_version = self.claim()
        _, src_version = self.source()
        with self.assertRaises(ValidationError) as ctx:
            self.lineage.propose_link(claim_version, src_version, "depends_on", reason="rests on", by="dependency-steward")
        self.assertTrue(any("impact_policy" in e for e in ctx.exception.errors))
        self.assertEqual([], self.store.edges_from(claim_version, status=None))
        with self.assertRaises(ValidationError):
            self.lineage.propose_link(
                claim_version, src_version, "depends_on", impact_policy="explode", reason="rests on", by="dependency-steward"
            )
        edge = self.lineage.propose_link(
            claim_version, src_version, "depends_on", impact_policy="review", reason="rests on", by="dependency-steward"
        )
        self.assertEqual("proposed", self.store.get_edge(edge)["status"])

    def test_other_relations_must_not_carry_impact_policy(self):
        _, claim_version = self.claim()
        _, src_version = self.source()
        for relation in ("supports", "contradicts", "implements", "verifies", "derived_from", "supersedes"):
            with self.assertRaises(ValidationError, msg=relation):
                self.lineage.propose_link(src_version, claim_version, relation, impact_policy="review", reason="x", by="dependency-steward")
        edge = self.lineage.propose_link(src_version, claim_version, "supports", reason="source states it", by="dependency-steward")
        self.assertIsNone(self.store.get_edge(edge)["impact_policy"])

    def test_link_shape_checks(self):
        _, claim_version = self.claim()
        _, src_version = self.source()
        with self.assertRaises(ValidationError):
            self.lineage.propose_link(claim_version, claim_version, "supports", reason="self", by="dependency-steward")
        with self.assertRaises(ValidationError):
            self.lineage.propose_link(claim_version, src_version, "supports", reason="  ", by="dependency-steward")
        with self.assertRaises(ValidationError):
            self.lineage.propose_link(claim_version, src_version, "causes", reason="x", by="dependency-steward")
        with self.assertRaises(NotFoundError):
            self.lineage.propose_link(claim_version, "ver_missing", "supports", reason="x", by="dependency-steward")
        self.assertEqual(0, len(self.store.events(type="lineage.link_proposed")))

    def test_accept_and_reject_transitions(self):
        _, claim_version = self.claim()
        _, src_version = self.source()
        edge = self.lineage.propose_link(src_version, claim_version, "supports", reason="states it", by="claim-checker")
        accepted = self.lineage.accept_link(edge, by="review-manager")
        self.assertEqual(("accepted", "review-manager"), (accepted["status"], accepted["status_changed_by"]))
        self.assertEqual(accepted, self.lineage.accept_link(edge, by="review-manager"))  # idempotent
        with self.assertRaises(TransitionError):
            self.lineage.reject_link(edge, by="review-manager", reason="changed mind")
        other = self.lineage.propose_link(src_version, claim_version, "derived_from", reason="derived", by="claim-checker")
        with self.assertRaises(ValidationError):
            self.lineage.reject_link(other, by="review-manager", reason="")
        rejected = self.lineage.reject_link(other, by="review-manager", reason="wrong direction")
        self.assertEqual("rejected", rejected["status"])
        self.assertEqual(rejected, self.lineage.reject_link(other, by="review-manager", reason="again"))
        with self.assertRaises(TransitionError):
            self.lineage.accept_link(other, by="review-manager")
        with self.assertRaises(NotFoundError):
            self.lineage.accept_link("edge_missing", by="review-manager")
        types = self.event_types()
        self.assertEqual(2, types.count("lineage.link_proposed"))
        self.assertEqual(1, types.count("lineage.link_accepted"))
        self.assertEqual(1, types.count("lineage.link_rejected"))
        rejected_event = self.store.events(type="lineage.link_rejected")[0]
        self.assertEqual("wrong direction", rejected_event.payload["reason"])


# --------------------------------------------------------------------------------------------------
# Impact traversal
# --------------------------------------------------------------------------------------------------


class ImpactTraversal(LineageCase):
    def test_impact_reaches_declared_accepted_dependents_only(self):
        _, src_version = self.source()
        _, claim_version = self.claim()
        _, undeclared_claim = self.claim(statement="Undeclared dependent.")
        _, proposed_only = self.claim(statement="Proposed dependent.")
        _, supporter = self.claim(statement="Supports relation only.")
        _, req_version = self.requirement()
        self.link(claim_version, src_version, "depends_on", impact_policy="review")
        self.link(proposed_only, src_version, "depends_on", impact_policy="review", accept=False)
        self.link(supporter, src_version, "supports")
        self.link(req_version, claim_version, "depends_on", impact_policy="invalidate_applicability")
        rejected = self.link(undeclared_claim, src_version, "depends_on", impact_policy="review", accept=False)
        self.lineage.reject_link(rejected, by="review-manager", reason="not a real dependency")

        impacts = self.lineage.impact(src_version)
        self.assertEqual([claim_version, req_version], [i.affected_version for i in impacts])
        self.assertEqual([(src_version, claim_version), (src_version, claim_version, req_version)], [i.path for i in impacts])
        self.assertEqual(["review", "invalidate_applicability"], [i.impact_policy for i in impacts])
        self.assertEqual([1, 2], [i.depth for i in impacts])
        self.assertEqual(["claim", "requirement"], [i.kind for i in impacts])
        self.assertTrue(all(i.changed_version == src_version for i in impacts))
        self.assertTrue(all(i.is_current for i in impacts))
        # Reverse direction: the source depends on nothing, so a change to the requirement affects nothing.
        self.assertEqual([], self.lineage.impact(req_version))
        with self.assertRaises(NotFoundError):
            self.lineage.impact("ver_missing")

    def test_impact_order_is_deterministic_and_cycle_safe(self):
        _, src_version = self.source()
        dependents = [self.claim(statement=f"Dependent {i}.")[1] for i in range(5)]
        # Declare in reverse creation order so traversal order cannot be insertion order by accident.
        for version in reversed(dependents):
            self.link(version, src_version, "depends_on", impact_policy="review")
        # A cycle back to the source must not loop and must not re-report the source.
        self.link(src_version, dependents[0], "depends_on", impact_policy="none")
        first = [i.affected_version for i in self.lineage.impact(src_version)]
        self.assertEqual(sorted(dependents), first)
        self.assertEqual(first, [i.affected_version for i in self.lineage.impact(src_version)])
        self.assertNotIn(src_version, first)
        # A diamond reports each affected version once, via the first (sorted) path.
        _, top = self.claim(statement="Diamond top.")
        self.link(top, dependents[0], "depends_on", impact_policy="review")
        self.link(top, dependents[1], "depends_on", impact_policy="invalidate_applicability")
        affected = [i for i in self.lineage.impact(src_version) if i.affected_version == top]
        self.assertEqual(1, len(affected))
        self.assertEqual((src_version, min(dependents[0], dependents[1]), top), affected[0].path)

    def test_impact_record_round_trips_through_dict(self):
        _, src_version = self.source()
        _, claim_version = self.claim()
        self.link(claim_version, src_version, "depends_on", impact_policy="review")
        impact = self.lineage.impact(src_version)[0]
        self.assertEqual(impact, L.Impact.from_mapping(impact.to_dict()))
        with self.assertRaises(ValidationError):
            L.Impact.from_mapping({"affected_version": "x"})


# --------------------------------------------------------------------------------------------------
# Applying impact
# --------------------------------------------------------------------------------------------------


class ApplyImpact(LineageCase):
    def test_invalidate_vs_review_vs_none(self):
        _, src_version = self.source()
        review_node, review_version = self.claim(statement="Needs review.")
        inval_node, inval_version = self.validation()
        none_node, none_version = self.claim(statement="Does not care.")
        self.link(review_version, src_version, "depends_on", impact_policy="review")
        self.link(inval_version, src_version, "depends_on", impact_policy="invalidate_applicability")
        self.link(none_version, src_version, "depends_on", impact_policy="none")

        impacts = self.lineage.impact(src_version)
        self.assertEqual(3, len(impacts))
        rows = self.lineage.apply_impact(impacts, by="controller")
        by_version = {row["affected_version"]: row for row in rows}
        self.assertEqual({review_version, inval_version}, set(by_version))
        self.assertEqual("review_required", by_version[review_version]["state"])
        self.assertEqual("invalidated", by_version[inval_version]["state"])
        self.assertEqual(src_version, by_version[inval_version]["changed_version"])
        self.assertEqual([src_version, inval_version], by_version[inval_version]["path"])
        # review: nothing about the node changed; invalidate: applicability only; none: untouched.
        self.assertEqual(("supported", "current"), (self.store.current(review_node)["status"], self.store.current(review_node)["applicability"]))
        self.assertEqual(("passed", "invalidated"), (self.store.current(inval_node)["status"], self.store.current(inval_node)["applicability"]))
        self.assertEqual(("supported", "current"), (self.store.current(none_node)["status"], self.store.current(none_node)["applicability"]))
        queued = self.store.query("impact_queue")
        self.assertEqual(2, len(queued))
        self.assertEqual(2, len(self.store.events(type="lineage.impact_queued")))
        # Re-applying reuses the open rows instead of duplicating them.
        again = self.lineage.apply_impact(impacts, by="controller")
        self.assertEqual(sorted(r["id"] for r in rows), sorted(r["id"] for r in again))
        self.assertEqual(2, len(self.store.query("impact_queue")))

    def test_apply_accepts_dict_impacts_and_refuses_unknown_policy(self):
        _, src_version = self.source()
        _, claim_version = self.claim()
        self.link(claim_version, src_version, "depends_on", impact_policy="review")
        rows = self.lineage.apply_impact([i.to_dict() for i in self.lineage.impact(src_version)], by="controller")
        self.assertEqual(1, len(rows))
        with self.assertRaises(ValidationError):
            self.lineage.apply_impact(
                [{"affected_version": claim_version, "changed_version": src_version, "impact_policy": "delete"}], by="controller"
            )
        with self.assertRaises(PolicyError):
            self.lineage.apply_impact([], by="not-a-role")

    def test_protected_requirement_survives_failed_implementation(self):
        """AT-13: new negative evidence must not retire or invalidate the protected requirement."""
        _, src_version = self.source()
        claim_node, claim_version = self.claim()
        req_node, req_version = self.requirement(protected=True)
        art_node, art_version = self.artifact()
        pos_node, pos_version = self.validation()
        dec_node, dec_version = self.decision()
        self.link(claim_version, src_version, "depends_on", impact_policy="review")
        self.link(req_version, claim_version, "depends_on", impact_policy="invalidate_applicability")
        self.link(art_version, req_version, "implements")
        self.link(art_version, req_version, "depends_on", impact_policy="review")
        self.link(pos_version, art_version, "verifies")
        self.link(pos_version, art_version, "depends_on", impact_policy="invalidate_applicability")
        self.link(dec_version, claim_version, "depends_on", impact_policy="review")

        # A cross-workspace negative test fails and contradicts the isolation claim.
        _, neg_version = self.validation(method="pytest tests/test_cross_workspace.py", receipt_id="rcpt_negative", result="failed")
        request = self.lineage.contradict(claim_version, neg_version, by="test-engineer")
        self.assertEqual("contested", self.store.current(claim_node)["status"])
        review_version = self.review([claim_version, neg_version], by=request["suggested_reviewer_role"])
        impacts = self.lineage.accept_correction(claim_version, outcome="unsupported", by="review-manager", review_version_id=review_version)
        self.assertEqual("unsupported", self.store.current(claim_node)["status"])
        # Declared dependents only, transitively: requirement and decision directly, then the
        # implementation (depends on the requirement) and the positive test (depends on the implementation).
        self.assertEqual({req_version, dec_version, art_version, pos_version}, {i.affected_version for i in impacts})
        self.assertEqual([1, 1, 2, 3], sorted(i.depth for i in impacts))

        rows = self.lineage.apply_impact(impacts, by="controller")
        by_version = {row["affected_version"]: row for row in rows}
        req_row = by_version[req_version]
        self.assertEqual("review_required", req_row["state"])
        self.assertEqual(L.PROTECTED_REQUIREMENT_REASON, req_row["reason"])
        self.assertTrue(req_row["protected"])
        self.assertEqual("review_required", by_version[dec_version]["state"])
        self.assertEqual("review_required", by_version[art_version]["state"])
        self.assertEqual("invalidated", by_version[pos_version]["state"])
        # The protected requirement is still approved and current: not retired, not superseded, not invalidated.
        current_req = self.store.current(req_node)
        self.assertEqual(("approved", "current", req_version), (current_req["status"], current_req["applicability"], current_req["version_id"]))
        self.assertEqual(1, len(self.store.versions_of(req_node)))
        # The old positive test is still a genuine pass: only its applicability changed, never its result.
        self.assertEqual(("passed", "invalidated"), (self.store.current(pos_node)["status"], self.store.current(pos_node)["applicability"]))
        self.assertEqual("passed", self.store.get_version(pos_version)["payload"]["result"])
        # The implementation keeps its status; review was queued, nothing was changed for it.
        self.assertEqual("implemented_not_verified", self.store.current(art_node)["status"])
        # A corrected implementation version is a new change: the positive test is queued again (new changed
        # version) and the protected requirement is still untouched.
        _, art_v2 = self.lineage.add_record(self.case_id, "artifact", {**ARTIFACT, "content_hash": "ef" * 32}, by="integration-engineer", node_id=art_node)
        self.link(art_v2, art_version, "supersedes")
        rows = self.lineage.apply_impact(self.lineage.impact(art_version), by="controller")
        self.assertEqual({pos_version}, {row["affected_version"] for row in rows})
        self.assertEqual(art_version, rows[0]["changed_version"])
        self.assertEqual(("passed", "invalidated"), (self.store.current(pos_node)["status"], self.store.current(pos_node)["applicability"]))
        self.assertEqual(("approved", "current"), (self.store.current(req_node)["status"], self.store.current(req_node)["applicability"]))
        # The gap list still names what has no declared lineage (the requirement has an implements edge; the
        # negative test verifies nothing yet), so the traversal is not mistaken for complete understanding.
        self.assertIn(neg_version, {gap["version_id"] for gap in self.lineage.missing_lineage(self.case_id)})

    def test_protected_requirement_under_review_policy_also_gets_protected_reason(self):
        _, src_version = self.source()
        req_node, req_version = self.requirement(protected=True)
        _, plain_req = self.requirement(statement="Ordinary requirement.", protected=False)
        self.link(req_version, src_version, "depends_on", impact_policy="review")
        self.link(plain_req, src_version, "depends_on", impact_policy="invalidate_applicability")
        rows = self.lineage.apply_impact(self.lineage.impact(src_version), by="controller")
        by_version = {row["affected_version"]: row for row in rows}
        self.assertEqual(L.PROTECTED_REQUIREMENT_REASON, by_version[req_version]["reason"])
        self.assertEqual("review_required", by_version[req_version]["state"])
        self.assertEqual("invalidated", by_version[plain_req]["state"])
        self.assertEqual("current", self.store.current(req_node)["applicability"])

    def test_invalidating_a_stale_version_queues_review_instead(self):
        _, src_version = self.source()
        node, v1 = self.validation()
        self.link(v1, src_version, "depends_on", impact_policy="invalidate_applicability")
        _, v2 = self.lineage.add_record(self.case_id, "validation", {**VALIDATION, "receipt_id": "rcpt_2"}, by="test-engineer", node_id=node)
        rows = self.lineage.apply_impact(self.lineage.impact(src_version), by="controller")
        self.assertEqual(1, len(rows))
        self.assertEqual(("review_required", L.STALE_VERSION_REASON), (rows[0]["state"], rows[0]["reason"]))
        self.assertEqual((v2, "current"), (self.store.current(node)["version_id"], self.store.current(node)["applicability"]))


# --------------------------------------------------------------------------------------------------
# Contradiction and correction
# --------------------------------------------------------------------------------------------------


class Contradiction(LineageCase):
    def test_contradiction_sets_contested_not_unsupported(self):
        claim_node, claim_version = self.claim(status="supported")
        _, contrary = self.validation(result="failed", receipt_id="rcpt_neg")
        request = self.lineage.contradict(claim_version, contrary, by="test-engineer")
        current = self.store.current(claim_node)
        self.assertEqual("contested", current["status"])
        self.assertEqual(claim_version, current["version_id"])
        self.assertEqual("review_request", request["kind"])
        self.assertEqual("claim_contested", request["reason"])
        self.assertEqual(("supported", "contested"), (request["previous_status"], request["status"]))
        self.assertEqual([claim_version, contrary], request["reviewed_refs"])
        self.assertIn("accept_correction", request["next_step"])
        self.assertEqual(sorted(L.CORRECTION_OUTCOMES), request["allowed_outcomes"])
        self.assertIn("claim-checker", request["excluded_reviewer_roles"])
        self.assertIn("test-engineer", request["excluded_reviewer_roles"])
        # The registry says who reviews the assessor; the suggestion is never one of the excluded roles.
        self.assertEqual(self.registry.agents["claim-checker"].reviewed_by, request["suggested_reviewer_role"])
        self.assertNotIn(request["suggested_reviewer_role"], request["excluded_reviewer_roles"])
        edge = self.store.get_edge(request["edge_id"])
        self.assertEqual((contrary, claim_version, "contradicts", "accepted", None), (edge["from_version"], edge["to_version"], edge["relation"], edge["status"], edge["impact_policy"]))
        self.assertEqual(1, len(self.store.events(type="lineage.claim_contested")))
        # A second contradiction keeps the claim contested; it never moves on to unsupported.
        _, contrary2 = self.source(id="src-2", title="Another source")
        request2 = self.lineage.contradict(claim_version, contrary2, by="context-analyst")
        self.assertEqual("contested", self.store.current(claim_node)["status"])
        self.assertEqual(("contested", "contested"), (request2["previous_status"], request2["status"]))
        self.assertEqual(2, len(self.store.edges_to(claim_version, "contradicts")))
        self.assertNotIn("unsupported", [e.payload["status"] for e in self.store.events(type="node.current_changed")])

    def test_contradiction_leaves_unsupported_and_superseded_alone(self):
        for status in ("unsupported", "superseded"):
            node, version = self.claim(status=status)
            _, contrary = self.source(id=f"src-{status}")
            request = self.lineage.contradict(version, contrary, by="context-analyst")
            self.assertEqual(status, self.store.current(node)["status"])
            self.assertEqual(status, request["status"])
            self.assertEqual("accepted", self.store.get_edge(request["edge_id"])["status"])

    def test_contradict_shape_checks(self):
        _, claim_version = self.claim()
        _, other_claim = self.claim(statement="Other.")
        _, src_version = self.source()
        with self.assertRaises(ValidationError):
            self.lineage.contradict(src_version, claim_version, by="context-analyst")  # not a claim
        with self.assertRaises(ValidationError):
            self.lineage.contradict(claim_version, claim_version, by="context-analyst")  # self
        with self.assertRaises(NotFoundError):
            self.lineage.contradict(claim_version, "ver_missing", by="context-analyst")
        with self.assertRaises(PolicyError):
            self.lineage.contradict(claim_version, src_version, by="ghost")
        self.assertEqual([], self.store.edges_to(claim_version, "contradicts", None))
        # Another claim may contradict this one.
        request = self.lineage.contradict(claim_version, other_claim, by="claim-checker")
        self.assertEqual("claim", request["contrary_kind"])

    def test_accept_correction_requires_bound_review(self):
        claim_node, claim_version = self.claim()
        _, contrary = self.validation(result="failed", receipt_id="rcpt_neg")
        self.lineage.contradict(claim_version, contrary, by="test-engineer")
        with self.assertRaises(ValidationError):
            self.lineage.accept_correction(claim_version, outcome="unsupported", by="review-manager", review_version_id="")
        with self.assertRaises(TypeError):
            self.lineage.accept_correction(claim_version, outcome="unsupported", by="review-manager")  # type: ignore[call-arg]
        with self.assertRaises(NotFoundError):
            self.lineage.accept_correction(claim_version, outcome="unsupported", by="review-manager", review_version_id="ver_missing")
        with self.assertRaises(ValidationError):
            self.lineage.accept_correction(claim_version, outcome="unsupported", by="review-manager", review_version_id=contrary)  # not a review
        unrelated = self.review([contrary])
        with self.assertRaises(PolicyError) as ctx:
            self.lineage.accept_correction(claim_version, outcome="unsupported", by="review-manager", review_version_id=unrelated)
        self.assertEqual("review_not_bound_to_claim", ctx.exception.details["reason"])
        own = self.review([claim_version], by="claim-checker")
        with self.assertRaises(PolicyError) as ctx:
            self.lineage.accept_correction(claim_version, outcome="unsupported", by="review-manager", review_version_id=own)
        self.assertEqual("author_cannot_review_own_artifact", ctx.exception.details["reason"])
        bound = self.review([claim_version])
        with self.assertRaises(ValidationError):
            self.lineage.accept_correction(claim_version, outcome="retracted", by="review-manager", review_version_id=bound)
        self.assertEqual("contested", self.store.current(claim_node)["status"])
        impacts = self.lineage.accept_correction(claim_version, outcome="unsupported", by="review-manager", review_version_id=bound)
        self.assertEqual([], impacts)
        self.assertEqual("unsupported", self.store.current(claim_node)["status"])
        event = self.store.events(type="lineage.correction_accepted")[0]
        self.assertEqual((bound, "unsupported"), (event.payload["review_version_id"], event.payload["outcome"]))
        # A correction needs a contested claim; an unsupported one cannot be corrected again without a new contest.
        with self.assertRaises(TransitionError):
            self.lineage.accept_correction(claim_version, outcome="supported", by="review-manager", review_version_id=bound)

    def test_correction_can_restore_support_and_returns_impacts(self):
        _, src_version = self.source()
        claim_node, claim_version = self.claim()
        _, dependent = self.claim(statement="Depends on the contested claim.")
        self.link(dependent, claim_version, "depends_on", impact_policy="review")
        self.lineage.contradict(claim_version, src_version, by="context-analyst")
        review_version = self.review([claim_version])
        impacts = self.lineage.accept_correction(claim_version, outcome="supported", by="review-manager", review_version_id=review_version)
        self.assertEqual("supported", self.store.current(claim_node)["status"])
        self.assertEqual([dependent], [i.affected_version for i in impacts])
        self.assertEqual([], self.store.query("impact_queue"))  # computed, not applied


# --------------------------------------------------------------------------------------------------
# Applicability
# --------------------------------------------------------------------------------------------------


class Historical(LineageCase):
    def test_mark_historical_keeps_result(self):
        for result in ("passed", "failed"):
            node, version = self.validation(result=result, receipt_id=f"rcpt_{result}")
            updated = self.lineage.mark_historical(version, by="dependency-steward")
            self.assertEqual((result, "historical", version), (updated["status"], updated["applicability"], updated["version_id"]))
            stored = self.store.current(node)
            self.assertEqual((result, "historical"), (stored["status"], stored["applicability"]))
            self.assertEqual(result, self.store.get_version(version)["payload"]["result"])
            self.assertEqual(1, len(self.store.versions_of(node)))
        events = self.store.events(type="lineage.validation_marked_historical")
        self.assertEqual(["passed", "failed"], [e.payload["result"] for e in events])
        self.assertEqual(["current", "current"], [e.payload["previous_applicability"] for e in events])

    def test_mark_historical_is_idempotent_and_checks_kind_and_currency(self):
        node, v1 = self.validation()
        before = self.store.state_version()
        self.lineage.mark_historical(v1, by="dependency-steward")
        after = self.store.state_version()
        self.assertEqual(after, before + 2)  # node.current_changed + lineage event
        self.lineage.mark_historical(v1, by="dependency-steward")
        self.assertEqual(after, self.store.state_version())
        _, claim_version = self.claim()
        with self.assertRaises(ValidationError):
            self.lineage.mark_historical(claim_version, by="dependency-steward")
        _, v2 = self.lineage.add_record(self.case_id, "validation", {**VALIDATION, "receipt_id": "rcpt_2"}, by="test-engineer", node_id=node)
        with self.assertRaises(TransitionError):
            self.lineage.mark_historical(v1, by="dependency-steward")
        self.assertEqual((v2, "current"), (self.store.current(node)["version_id"], self.store.current(node)["applicability"]))


# --------------------------------------------------------------------------------------------------
# Coverage and missing lineage
# --------------------------------------------------------------------------------------------------


class Coverage(LineageCase):
    def test_coverage_labels_linked_missing_disputed(self):
        _, linked_req = self.requirement(statement="Linked.")
        _, missing_req = self.requirement(statement="Missing.", protected=False)
        _, implemented_only = self.requirement(statement="Implemented, unverified.", protected=False)
        _, disputed_req = self.requirement(statement="Disputed.", protected=False)
        _, pending_req = self.requirement(statement="Pending link.", protected=False)
        _, art_linked = self.artifact(path="src/a.py")
        _, art_only = self.artifact(path="src/b.py")
        _, art_disputed = self.artifact(path="src/c.py")
        _, art_pending = self.artifact(path="src/d.py")
        _, val_pass = self.validation(receipt_id="rcpt_pass")
        _, val_fail = self.validation(receipt_id="rcpt_fail", result="failed")
        self.link(art_linked, linked_req, "implements")
        self.link(val_pass, art_linked, "verifies")
        self.link(art_only, implemented_only, "implements")
        self.link(art_disputed, disputed_req, "implements")
        self.link(val_fail, art_disputed, "verifies")
        self.link(art_pending, pending_req, "implements", accept=False)

        report = self.lineage.coverage(self.case_id)
        by_version = {row["version_id"]: row for row in report["requirements"]}
        self.assertEqual("linked", by_version[linked_req]["coverage"])
        self.assertEqual("missing", by_version[missing_req]["coverage"])
        self.assertEqual("missing", by_version[implemented_only]["coverage"])
        self.assertEqual("disputed", by_version[disputed_req]["coverage"])
        self.assertEqual("disputed", by_version[pending_req]["coverage"])
        self.assertEqual({"linked": 1, "missing": 2, "disputed": 2, "total": 5}, report["summary"])
        self.assertEqual([art_linked], [a["version_id"] for a in by_version[linked_req]["implemented_by"]])
        self.assertEqual([val_pass], [v["version_id"] for v in by_version[linked_req]["verified_by"]])
        self.assertEqual(("passed", "current"), (by_version[linked_req]["verified_by"][0]["result"], by_version[linked_req]["verified_by"][0]["applicability"]))
        self.assertTrue(by_version[linked_req]["protected"])
        self.assertEqual([val_fail], by_version[disputed_req]["failed_validations"])
        self.assertEqual(1, len(by_version[pending_req]["pending_edges"]))
        self.assertEqual(self.case_id, report["case_id"])
        with self.assertRaises(NotFoundError):
            self.lineage.coverage("case_other")

    def test_coverage_reflects_applicability_and_open_impacts(self):
        _, src_version = self.source()
        _, req_version = self.requirement()
        val_node, val_version = self.validation()
        _, art_version = self.artifact()
        self.link(art_version, req_version, "implements")
        self.link(val_version, art_version, "verifies")
        self.assertEqual("linked", self.lineage.coverage(self.case_id)["requirements"][0]["coverage"])
        # The only verifying validation becomes historical: the requirement is no longer covered by current evidence.
        self.lineage.mark_historical(val_version, by="dependency-steward")
        row = self.lineage.coverage(self.case_id)["requirements"][0]
        self.assertEqual("missing", row["coverage"])
        self.assertEqual("historical", row["verified_by"][0]["applicability"])
        # An open impact row on the requirement makes it disputed until resolved.
        self.link(req_version, src_version, "depends_on", impact_policy="review")
        rows = self.lineage.apply_impact(self.lineage.impact(src_version), by="controller")
        report_row = self.lineage.coverage(self.case_id)["requirements"][0]
        self.assertEqual("disputed", report_row["coverage"])
        self.assertEqual([rows[0]["id"]], report_row["open_impacts"])

    def test_missing_lineage_reports_each_gap_separately_from_impact(self):
        _, src_version = self.source()
        _, req_linked = self.requirement(statement="Implemented.")
        _, req_bare = self.requirement(statement="Nothing implements me.", protected=False)
        _, art_linked = self.artifact(path="src/linked.py")
        _, art_bare = self.artifact(path="src/bare.py")
        _, val_linked = self.validation(receipt_id="rcpt_linked")
        _, val_bare = self.validation(receipt_id="rcpt_bare")
        _, val_pending = self.validation(receipt_id="rcpt_pending")
        self.link(art_linked, req_linked, "implements")
        self.link(art_linked, src_version, "depends_on", impact_policy="review")
        self.link(val_linked, art_linked, "verifies")
        pending_edge = self.link(val_pending, art_linked, "verifies", accept=False)

        gaps = self.lineage.missing_lineage(self.case_id)
        by_version = {gap["version_id"]: gap for gap in gaps}
        self.assertEqual({req_bare, art_bare, val_bare, val_pending}, set(by_version))
        self.assertEqual(("requirement", "implements", "incoming"), (by_version[req_bare]["kind"], by_version[req_bare]["missing"], by_version[req_bare]["direction"]))
        self.assertEqual(("artifact", "depends_on", "outgoing"), (by_version[art_bare]["kind"], by_version[art_bare]["missing"], by_version[art_bare]["direction"]))
        self.assertEqual(("validation", "verifies", "outgoing"), (by_version[val_bare]["kind"], by_version[val_bare]["missing"], by_version[val_bare]["direction"]))
        self.assertEqual([pending_edge], by_version[val_pending]["pending_edges"])
        self.assertEqual([], by_version[val_bare]["pending_edges"])
        self.assertFalse(by_version[art_bare]["protected"])
        # Deterministic order: kinds in artifact, requirement, validation order; node creation order within a kind.
        self.assertEqual([art_bare, req_bare, val_bare, val_pending], [gap["version_id"] for gap in gaps])
        # AT-13: impact() over the source says nothing about art_bare; the gap list is where that shows.
        self.assertEqual([art_linked], [i.affected_version for i in self.lineage.impact(src_version)])
        self.assertIn(art_bare, by_version)
        with self.assertRaises(NotFoundError):
            self.lineage.missing_lineage("case_other")


# --------------------------------------------------------------------------------------------------
# Transactions and events
# --------------------------------------------------------------------------------------------------


class TransactionsAndEvents(LineageCase):
    def test_every_mutation_is_an_event_and_reads_are_not(self):
        _, src_version = self.source()
        claim_node, claim_version = self.claim()
        _, val_version = self.validation()
        edge = self.lineage.propose_link(claim_version, src_version, "depends_on", impact_policy="invalidate_applicability", reason="rests on", by="dependency-steward")
        self.lineage.accept_link(edge, by="review-manager")
        self.lineage.impact(src_version)
        self.lineage.coverage(self.case_id)
        self.lineage.missing_lineage(self.case_id)
        before = self.store.state_version()
        self.lineage.impact(src_version)
        self.assertEqual(before, self.store.state_version())
        self.lineage.apply_impact(self.lineage.impact(src_version), by="controller")
        self.lineage.mark_historical(val_version, by="dependency-steward")
        self.lineage.contradict(claim_version, val_version, by="test-engineer")
        types = self.event_types()
        for expected in (
            "lineage.record_added",
            "lineage.link_proposed",
            "lineage.link_accepted",
            "lineage.impact_queued",
            "lineage.validation_marked_historical",
            "lineage.claim_contested",
            "node.current_changed",
        ):
            self.assertIn(expected, types)
        self.assertEqual(len(types), self.store.state_version())
        self.assertTrue(all(e.actor_role for e in self.store.events()))
        seqs = [e.seq for e in self.store.events()]
        self.assertEqual(list(range(1, len(seqs) + 1)), seqs)
        self.assertEqual([], self.store.integrity_check())

    def test_failure_inside_an_operation_rolls_back_everything(self):
        claim_node, claim_version = self.claim()
        _, contrary = self.source()
        events_before = len(self.store.events())
        original = self.store.append_event

        def exploding(*args, **kwargs):
            raise ConflictError("simulated failure", details={"reason": "test"})

        self.store.append_event = exploding  # type: ignore[method-assign]
        try:
            with self.assertRaises(ConflictError):
                self.lineage.contradict(claim_version, contrary, by="test-engineer")
        finally:
            self.store.append_event = original  # type: ignore[method-assign]
        # Neither the edge nor the status change survived.
        self.assertEqual([], self.store.edges_to(claim_version, "contradicts", None))
        self.assertEqual("supported", self.store.current(claim_node)["status"])
        self.assertEqual(events_before, len(self.store.events()))
        self.assertFalse(self.store.connection.in_transaction)

    def test_lineage_without_registry_accepts_any_actor(self):
        bare = L.Lineage(self.store)
        node, _ = bare.add_claim(self.case_id, dict(CLAIM), by="anyone")
        self.assertEqual("supported", self.store.current(node)["status"])
        with self.assertRaises(ValidationError):
            L.Lineage(object())  # type: ignore[arg-type]


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
