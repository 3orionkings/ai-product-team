"""Reviews, independence, challenges, rulings, proposals, approvals, decisions and authority checks.

Single responsibility: record the review-and-decision records of a case and enforce the *structural*
rules around them (contract section 8; architecture sections 9 and 10). The module checks who may do
what, whether a reviewer is independent of the author, whether a challenge is material and within the
round budget, whether an approval binds the exact proposal version and is still live, and whether a
decision may move to ``accepted``. It never judges whether evidence is persuasive.

Records are stored as immutable node versions through :class:`~ai_product_team.storage.CaseStore`:
``review`` (reviews and, per architecture section 6.1 "Review / Judgment", judge rulings), ``challenge``,
``decision`` and ``approval``. Status lives in the ``node_current`` projection; every change emits an
event.

Guarantees that hold on every code path
    * The author of an artifact cannot review it; a shared session or native child id is a conflict;
      an unknown session is recorded as ``unverified`` and never promoted.
    * A ``pass`` review cites only observed checks that carry a receipt stored in this case.
    * ``provenance.attested`` on an approval is derived from the channel; the caller cannot set it.
    * Accepting a decision is **not** execution permission: the returned dict says
      ``execution_permission: False`` and nothing here runs, publishes, deploys, sends, pays or deletes.
    * There is no accept or execute path for the top risk tier (R3).
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from ai_product_team.errors import (
    BudgetExhausted,
    ConflictError,
    NotFoundError,
    PolicyError,
    TransitionError,
    ValidationError,
)
from ai_product_team.ids import now, parse_time
from ai_product_team.policies import Policies
from ai_product_team.registry import HUMAN_OWNER, Registry
from ai_product_team.storage import CaseStore

__all__ = [
    "APPROVAL_CHANNELS",
    "ATTESTING_CHANNEL",
    "CHALLENGE_MATERIAL_FIELDS",
    "DECISION_ACCEPTABLE_FROM",
    "DECISION_AUTHORITY",
    "REVIEW_PASSING",
    "RULING_FIELDS",
    "RULING_OUTCOMES",
    "RULING_RESULT_MAP",
    "Decisions",
]

#: Channels an approval can arrive through (approval schema ``provenance.channel``).
APPROVAL_CHANNELS: tuple[str, ...] = ("cli", "host_user_input", "file")
#: The only channel the controller treats as attesting that a human produced the input.
ATTESTING_CHANNEL: str = "host_user_input"
#: The five fields that make a challenge material; each must be a non-blank string.
CHALLENGE_MATERIAL_FIELDS: tuple[str, ...] = (
    "contested_ref",
    "premise",
    "counterevidence_or_gap",
    "consequence",
    "resolving_test",
)
#: Every ruling carries these fields (architecture section 10.4).
RULING_FIELDS: tuple[str, ...] = (
    "criteria",
    "admissible_evidence",
    "findings_per_objection",
    "option_comparison",
    "outcome",
    "uncertainty",
    "next_checks",
    "dissent_preserved",
    "scope",
)
#: ``ruling_outcome`` enumeration (contract section 3).
RULING_OUTCOMES: tuple[str, ...] = (
    "option_acceptable",
    "option_rejected",
    "insufficient_evidence",
    "unresolved",
    "next_test_required",
)
#: How a ruling outcome is projected onto the ``review_result`` vocabulary when the ruling is stored as a
#: ``review`` record. The full ruling (with its own outcome) is kept verbatim inside ``findings``.
RULING_RESULT_MAP: dict[str, str] = {
    "option_acceptable": "pass",
    "option_rejected": "fail",
    "insufficient_evidence": "blocked",
    "unresolved": "escalate",
    "next_test_required": "revise",
}
#: Decision statuses from which ``accept_decision`` may move to ``accepted``.
DECISION_ACCEPTABLE_FROM: frozenset[str] = frozenset({"proposed", "under_review", "human_required", "deferred"})
#: Review results that count as a favourable review for an independence gate.
REVIEW_PASSING: frozenset[str] = frozenset({"ready", "pass"})
#: Special principal id of the Decision Authority agent.
DECISION_AUTHORITY: str = "decision-authority"

_RULING_RECORD_TYPE = "ruling"
_ANSWERED = "answered"
_OPEN = "open"


class Decisions:
    """Review, challenge, ruling, approval and decision service over one :class:`CaseStore`.

    ``controller`` is optional: when given, an eligible review submitted with a ``task_id`` calls
    ``controller.task_mark_reviewed(task_id, review_version_id)`` (contract section 6) inside the same
    transaction as the review record.
    """

    def __init__(self, store: CaseStore, registry: Registry, policies: Policies, *, controller: Any | None = None) -> None:
        """Bind the service to a store, the registry (role types, reporting lines) and the policies."""
        self.store = store
        self.registry = registry
        self.policies = policies
        self.controller = controller

    # ---------------------------------------------------------------------------------------------
    # Reviews and independence
    # ---------------------------------------------------------------------------------------------

    def submit_review(
        self,
        case_id: str,
        *,
        reviewed_refs: Sequence[str],
        reviewer_role: str,
        reviewer_session: str | None,
        payload: Mapping[str, Any],
        task_id: str | None = None,
    ) -> str:
        """Record a review of exact versions after the independence and receipt checks; return its version id.

        Independence (policies/review-independence.json): the reviewer being the producer role of any
        reviewed version raises ``PolicyError`` (``author_cannot_review_own_artifact``); a reviewer session
        equal to the producer's session or native child id raises ``PolicyError`` (``same_session_conflict``);
        an unknown producer or reviewer session is stored as ``conflict_check="unverified"``; otherwise
        ``verified``. A manager reviewing an artifact of their own team is stored with ``independent=false``.
        The caller cannot set ``conflict_check`` or ``independent``.

        ``payload`` holds the review fields (``findings``, ``evidence_sufficiency``, ``result``, ``unresolved``,
        optional ``evidence_refs``) and may carry ``observed_checks`` (``{command, claimed_exit_status?,
        receipt_id?}``); findings shaped like an observed check count as cited checks too. A ``pass`` result
        requires every cited check to name a receipt stored in this case, else ``PolicyError``
        (``review_cites_unexecuted_check``). With ``task_id``, the task must be assigned to ``reviewer_role``.
        """
        self._require_case(case_id)
        refs = [str(r) for r in reviewed_refs]
        if not refs:
            raise ValidationError("a review must name at least one reviewed version", errors=["/reviewed_refs: must not be empty"])
        self._principal(reviewer_role)
        versions = [self._version(ref) for ref in refs]
        conflict_check, independent, manager_review = self._independence(reviewer_role, reviewer_session, versions)

        body = dict(payload or {})
        if "conflict_check" in body or "independent" in body:
            body.pop("conflict_check", None)
            body.pop("independent", None)
        cited = self._cited_checks(body)
        if body.get("result") == "pass":
            self._require_receipts(cited)
        evidence_refs = self._merge_refs(body.get("evidence_refs", []), [c.get("receipt_id") for c in cited])
        self._check_evidence_refs(evidence_refs)

        if task_id is not None:
            task = self.store.get("tasks", task_id)
            if task is None:
                raise NotFoundError(f"no task {task_id!r}", details={"task_id": task_id})
            assigned = task.get("role_id")
            if assigned is not None and assigned != reviewer_role:
                raise PolicyError(
                    "review_not_assigned",
                    details={"reason": "review_not_assigned", "task_id": task_id, "assigned_role": assigned, "reviewer_role": reviewer_role},
                )
        self.authority_check(reviewer_role, "review", self._tier_of(versions))

        record: dict[str, Any] = {
            **body,
            "reviewed_refs": refs,
            "reviewer_role": reviewer_role,
            "reviewer_session": reviewer_session,
            "conflict_check": conflict_check,
            "independent": independent,
        }
        record.setdefault("findings", [])
        record.setdefault("unresolved", [])
        record.setdefault("evidence_sufficiency", "not_assessed")
        if evidence_refs:
            record["evidence_refs"] = evidence_refs

        with self.store.transaction():
            node_id = self.store.new_node("review", case_id)
            version_id = self.store.put_version(
                node_id, record, author_role=reviewer_role, author_task=task_id, author_session=reviewer_session
            )
            self.store.set_current(node_id, version_id, status=record["result"], by=reviewer_role, actor_task=task_id)
            self._event(
                "review.submitted",
                {
                    "review_node": node_id,
                    "review_version": version_id,
                    "reviewed_refs": refs,
                    "reviewer_role": reviewer_role,
                    "result": record["result"],
                    "conflict_check": conflict_check,
                    "independent": independent,
                    "manager_review": manager_review,
                    "cited_receipts": [c.get("receipt_id") for c in cited],
                    "task_id": task_id,
                },
                actor_role=reviewer_role,
                actor_task=task_id,
                key=f"review.submitted:{version_id}",
                refs=[version_id, *refs],
            )
            if self.controller is not None and task_id is not None:
                self.controller.task_mark_reviewed(task_id, version_id)
        return version_id

    # ---------------------------------------------------------------------------------------------
    # Challenges
    # ---------------------------------------------------------------------------------------------

    def open_challenge(self, case_id: str, run_id: str, payload: Mapping[str, Any]) -> str:
        """Open a material challenge inside ``run_id``'s round budget; return the challenge version id.

        All five material fields must be non-blank strings (``ValidationError`` otherwise). ``round``
        defaults to the next round; it must not exceed ``max_challenge_rounds`` for the run's budget mode
        (``BudgetExhausted``, ``details.reason == "max_challenge_rounds"``) and rounds must be consecutive.
        ``contested_ref`` must be an existing version. The challenge is stored with ``state="open"``.
        """
        self._require_case(case_id)
        run = self.store.get("runs", run_id)
        if run is None:
            raise NotFoundError(f"no run {run_id!r}", details={"run_id": run_id})
        mode = run.get("mode")
        if not isinstance(mode, str) or not mode:
            raise ValidationError(f"run {run_id!r} has no budget mode", errors=["/mode: missing"], details={"run_id": run_id})
        max_rounds = int(self.policies.mode(mode)["max_challenge_rounds"])

        body = dict(payload or {})
        for field in CHALLENGE_MATERIAL_FIELDS:
            value = body.get(field)
            if not isinstance(value, str) or not value.strip():
                raise ValidationError(
                    f"challenge is not material: {field!r} is empty",
                    errors=[f"/{field}: must be a non-empty string"],
                    details={"reason": "empty_material_field", "field": field},
                )
        contested = self._version(body["contested_ref"])
        proposer = body.get("proposer_role")
        if not isinstance(proposer, str) or not proposer:
            raise ValidationError("challenge needs a proposer_role", errors=["/proposer_role: missing"])
        self._principal(proposer)

        used = self.rounds_used(run_id)
        round_ = body.get("round", used + 1)
        if isinstance(round_, bool) or not isinstance(round_, int) or round_ < 1:
            raise ValidationError("challenge round must be a positive integer", errors=["/round: must be an integer >= 1"])
        if round_ > max_rounds:
            raise BudgetExhausted(
                f"challenge round {round_} exceeds max_challenge_rounds={max_rounds} for mode {mode!r}",
                partial_state={"run_id": run_id, "mode": mode, "max_challenge_rounds": max_rounds, "rounds_used": used, "requested_round": round_},
                details={"reason": "max_challenge_rounds", "run_id": run_id, "mode": mode, "max_challenge_rounds": max_rounds, "rounds_used": used},
            )
        if round_ > used + 1:
            raise ValidationError(
                f"challenge round {round_} skips rounds: {used} used so far",
                errors=["/round: rounds must be consecutive"],
                details={"reason": "round_not_consecutive", "rounds_used": used},
            )
        body["round"] = round_
        body["state"] = _OPEN
        self.authority_check(proposer, "propose", self._tier_of([contested]))

        with self.store.transaction():
            node_id = self.store.new_node("challenge", case_id)
            version_id = self.store.put_version(node_id, body, author_role=proposer)
            self.store.set_current(node_id, version_id, status=_OPEN, by=proposer)
            self._event(
                "challenge.opened",
                {
                    "run_id": run_id,
                    "challenge_node": node_id,
                    "challenge_version": version_id,
                    "round": round_,
                    "contested_ref": body["contested_ref"],
                    "proposer_role": proposer,
                },
                actor_role=proposer,
                key=f"challenge.opened:{version_id}",
                refs=[version_id, body["contested_ref"]],
            )
            self._sync_budget_rounds(run_id)
        return version_id

    def respond_challenge(self, challenge_version: str, response_payload: Mapping[str, Any], *, by: str) -> dict[str, Any]:
        """Answer an open challenge as the proposal owner; optionally revise the contested proposal.

        ``by`` must be the owner of the contested version (its author or producer role) or the human owner,
        else ``PolicyError`` (``not_proposal_owner``). ``response_payload`` carries ``response`` (non-empty
        text) and optionally ``revision``: a full proposal payload stored as a new version of the contested
        proposal node, linked by an accepted ``supersedes`` edge and made current. A revision can never lower
        the proposal's ``requested_authority``. Returns ``{"challenge_version", "proposal_version", "state"}``.
        """
        challenge = self._version(challenge_version, "challenge")
        node_id = challenge["node_id"]
        current = self.store.current(node_id)
        if current is not None and current["version_id"] != challenge_version:
            raise ConflictError(
                "challenge version is not current",
                details={"reason": "challenge_version_not_current", "current_version": current["version_id"]},
            )
        state = challenge["payload"].get("state")
        if state != _OPEN:
            raise TransitionError(f"challenge in state {state!r} cannot be answered", details={"state": state, "challenge_version": challenge_version})
        contested = self._version(challenge["payload"]["contested_ref"])
        owner, _, _ = self._producer_of(contested)
        if by != owner and by != HUMAN_OWNER:
            raise PolicyError("not_proposal_owner", details={"reason": "not_proposal_owner", "owner": owner, "by": by})

        body = dict(response_payload or {})
        text = body.get("response")
        if not isinstance(text, str) or not text.strip():
            raise ValidationError("a response needs non-empty text", errors=["/response: must be a non-empty string"])
        revision = body.get("revision")

        with self.store.transaction():
            new_proposal_version: str | None = None
            if revision is not None:
                if contested["kind"] != "proposal":
                    raise ValidationError(
                        "only a proposal can be revised in a challenge response",
                        errors=["/revision: contested version is not a proposal"],
                        details={"kind": contested["kind"]},
                    )
                if not isinstance(revision, Mapping):
                    raise ValidationError("revision must be a proposal payload", errors=["/revision: not an object"])
                rev = dict(revision)
                rev.setdefault("author_role", by)
                if rev["author_role"] != by:
                    raise PolicyError("revision_author_mismatch", details={"reason": "revision_author_mismatch", "author_role": rev["author_role"], "by": by})
                old_tier = contested["payload"]["requested_authority"]
                rev["requested_authority"] = self.policies.risk_at_least(old_tier, rev.get("requested_authority", old_tier))
                self._check_proposal_options(rev)
                new_proposal_version = self.store.put_version(contested["node_id"], rev, author_role=by)
                self.store.add_edge(
                    new_proposal_version,
                    contested["id"],
                    "supersedes",
                    reason=f"proposal revised in response to challenge {challenge_version}",
                    proposed_by=by,
                    status="accepted",
                )
                self.store.set_current(contested["node_id"], new_proposal_version, status="proposed", by=by)
            answered = {**challenge["payload"], "state": _ANSWERED, "response": text, "responded_by": by}
            new_challenge_version = self.store.put_version(node_id, answered, author_role=by)
            self.store.set_current(node_id, new_challenge_version, status=_ANSWERED, by=by)
            self._event(
                "challenge.answered",
                {
                    "challenge_node": node_id,
                    "challenge_version": new_challenge_version,
                    "previous_version": challenge_version,
                    "responded_by": by,
                    "proposal_version": new_proposal_version,
                },
                actor_role=by,
                key=f"challenge.answered:{new_challenge_version}",
                refs=[new_challenge_version, challenge_version] + ([new_proposal_version] if new_proposal_version else []),
            )
        return {"challenge_version": new_challenge_version, "proposal_version": new_proposal_version, "state": _ANSWERED}

    # ---------------------------------------------------------------------------------------------
    # Rulings
    # ---------------------------------------------------------------------------------------------

    def submit_ruling(self, case_id: str, *, judge_role: str, payload: Mapping[str, Any]) -> str:
        """Record a judge's ruling; return its version id. A ruling changes no other record's status.

        ``judge_role`` must be a registry agent of type ``judge`` (``PolicyError`` ``not_a_judge``). ``payload``
        carries every field in :data:`RULING_FIELDS`; ``outcome`` is a :data:`RULING_OUTCOMES` value and
        ``scope`` names the ruled versions (``{"question": ..., "refs": [...]}``, a list of version ids, or
        ``proposal_version_id``). A judge may not have authored any ruled proposal or record
        (``PolicyError`` ``judge_authored_proposal``). Optional ``judge_session`` feeds the independence check.

        Stored as a ``review`` record (architecture section 6.1 "Review / Judgment") whose single finding is
        ``{"record_type": "ruling", ...payload}``; ``result`` is :data:`RULING_RESULT_MAP` of the outcome and
        the current status is the outcome itself.
        """
        self._require_case(case_id)
        agent = self.registry.agents.get(judge_role)
        if agent is None or agent.type != "judge":
            raise PolicyError(
                "not_a_judge",
                details={"reason": "not_a_judge", "role": judge_role, "type": agent.type if agent is not None else None},
            )
        body = dict(payload or {})
        judge_session = body.pop("judge_session", None)
        missing = [field for field in RULING_FIELDS if field not in body]
        if missing:
            raise ValidationError(
                f"ruling is missing fields: {missing}",
                errors=[f"/{field}: '{field}' is a required property" for field in missing],
            )
        outcome = body["outcome"]
        if outcome not in RULING_OUTCOMES:
            raise ValidationError(
                f"unknown ruling outcome {outcome!r}",
                errors=[f"/outcome: {outcome!r} is not one of {list(RULING_OUTCOMES)}"],
            )
        refs = self._ruling_refs(body["scope"])
        if not refs:
            raise ValidationError(
                "ruling scope must name the ruled version ids",
                errors=["/scope: needs 'refs' (or 'proposal_version_id') naming existing versions"],
            )
        versions = [self._version(ref) for ref in refs]
        for version in versions:
            role, _, _ = self._producer_of(version)
            if role == judge_role or version["author_role"] == judge_role:
                raise PolicyError(
                    "judge_authored_proposal",
                    details={"reason": "judge_authored_proposal", "judge_role": judge_role, "version_id": version["id"], "kind": version["kind"]},
                )
        self.authority_check(judge_role, "adjudicate", self._tier_of(versions))
        conflict_check, independent, _ = self._independence(judge_role, judge_session, versions)

        evidence = body["admissible_evidence"]
        evidence_refs = [e for e in evidence if isinstance(e, str)] if isinstance(evidence, list) else []
        self._check_evidence_refs(evidence_refs)
        if outcome == "insufficient_evidence":
            sufficiency = "insufficient"
        elif outcome in ("option_acceptable", "option_rejected"):
            sufficiency = "sufficient"
        else:
            sufficiency = "not_assessed"

        record: dict[str, Any] = {
            "reviewed_refs": refs,
            "reviewer_role": judge_role,
            "reviewer_session": judge_session,
            "findings": [{"record_type": _RULING_RECORD_TYPE, **{field: body[field] for field in RULING_FIELDS}}],
            "evidence_sufficiency": sufficiency,
            "result": RULING_RESULT_MAP[outcome],
            "conflict_check": conflict_check,
            "unresolved": _as_items(body["next_checks"]) + _as_items(body["dissent_preserved"]),
            "independent": independent,
        }
        if evidence_refs:
            record["evidence_refs"] = evidence_refs

        with self.store.transaction():
            node_id = self.store.new_node("review", case_id)
            version_id = self.store.put_version(node_id, record, author_role=judge_role, author_session=judge_session)
            self.store.set_current(node_id, version_id, status=outcome, by=judge_role)
            self._event(
                "ruling.submitted",
                {
                    "ruling_node": node_id,
                    "ruling_version": version_id,
                    "judge_role": judge_role,
                    "outcome": outcome,
                    "reviewed_refs": refs,
                    "conflict_check": conflict_check,
                    "changes_other_status": False,
                },
                actor_role=judge_role,
                key=f"ruling.submitted:{version_id}",
                refs=[version_id, *refs],
            )
        return version_id

    # ---------------------------------------------------------------------------------------------
    # Decisions and approvals
    # ---------------------------------------------------------------------------------------------

    def propose_decision(self, case_id: str, payload: Mapping[str, Any], *, by: str) -> str:
        """Store a decision record in status ``proposed``; return its version id.

        ``proposal_version_id`` must be an existing proposal version; ``selected_option`` (when not null) must
        be one of its option ids and is required when ``outcome == "accepted"``. ``requested_authority`` is
        raised to at least the proposal's own tier (a model cannot lower an explicit minimum). ``status`` is
        forced to ``proposed``; ``authority_basis`` defaults to an unbound delegation.
        """
        self._require_case(case_id)
        self._principal(by)
        body = dict(payload or {})
        proposal_version = body.get("proposal_version_id")
        if not isinstance(proposal_version, str) or not proposal_version:
            raise ValidationError("decision needs a proposal_version_id", errors=["/proposal_version_id: missing"])
        proposal = self._version(proposal_version, "proposal")
        option_ids = {option["id"] for option in proposal["payload"]["options"]}
        selected = body.get("selected_option")
        if selected is not None and selected not in option_ids:
            raise ValidationError(
                f"selected_option {selected!r} is not an option of the proposal",
                errors=[f"/selected_option: {selected!r} is not one of {sorted(option_ids)}"],
            )
        if body.get("outcome") == "accepted" and selected is None:
            raise ValidationError("an accepted outcome needs a selected_option", errors=["/selected_option: required when outcome is accepted"])
        proposal_tier = proposal["payload"]["requested_authority"]
        tier = self.policies.risk_at_least(proposal_tier, body.get("requested_authority", proposal_tier))
        body["requested_authority"] = tier
        body["status"] = "proposed"
        body.setdefault("authority_basis", {"kind": "delegation", "approval_version_id": None})
        body.setdefault("dissent", [])
        self.authority_check(by, "propose", tier)

        with self.store.transaction():
            node_id = self.store.new_node("decision", case_id)
            version_id = self.store.put_version(node_id, body, author_role=by)
            self.store.set_current(node_id, version_id, status="proposed", by=by)
            self._event(
                "decision.proposed",
                {
                    "decision_node": node_id,
                    "decision_version": version_id,
                    "proposal_version": proposal_version,
                    "outcome": body.get("outcome"),
                    "requested_authority": tier,
                    "proposed_by": by,
                },
                actor_role=by,
                key=f"decision.proposed:{version_id}",
                refs=[version_id, proposal_version],
            )
        return version_id

    def record_user_input(self, case_id: str, approval_payload: Mapping[str, Any], *, channel: str) -> str:
        """Record an approval or delegation that arrived through ``channel``; return its version id.

        ``provenance`` is rewritten by the controller: ``channel`` as given and
        ``attested = (channel == "host_user_input")``. Whatever the caller put in ``provenance.attested`` is
        ignored (and noted in the event). ``bound_version_id`` must be an existing version. The record's
        current status is ``attested``, ``unverified_claim`` or ``revoked``.
        """
        self._require_case(case_id)
        if channel not in APPROVAL_CHANNELS:
            raise ValidationError(
                f"unknown approval channel {channel!r}",
                errors=[f"/channel: {channel!r} is not one of {list(APPROVAL_CHANNELS)}"],
            )
        body = dict(approval_payload or {})
        caller_prov = body.get("provenance")
        caller_attested = caller_prov.get("attested") if isinstance(caller_prov, Mapping) else None
        provenance: dict[str, Any] = {"channel": channel, "attested": channel == ATTESTING_CHANNEL}
        note = caller_prov.get("note") if isinstance(caller_prov, Mapping) else None
        if isinstance(note, str) and note:
            provenance["note"] = note
        body["provenance"] = provenance
        body.setdefault("granted_by", HUMAN_OWNER)
        body.setdefault("revoked", False)
        body.setdefault("expires_at", None)
        body.setdefault("allowed_actions", [])
        body.setdefault("allowed_decisions", [])
        body.setdefault("limits", None)
        bound = body.get("bound_version_id")
        if not isinstance(bound, str) or not bound:
            raise ValidationError("an approval must bind an exact version", errors=["/bound_version_id: missing"])
        self._version(bound)
        return self._store_approval(case_id, None, body, caller_attested=caller_attested)

    def revoke_approval(self, approval_version: str, *, channel: str, note: str | None = None) -> str:
        """Append a revoked version of an approval and make it current; return the new version id.

        Revocation is accepted from any channel (refusing is the safe direction); its provenance records the
        channel it came through like any other approval record.
        """
        if channel not in APPROVAL_CHANNELS:
            raise ValidationError(
                f"unknown approval channel {channel!r}",
                errors=[f"/channel: {channel!r} is not one of {list(APPROVAL_CHANNELS)}"],
            )
        approval = self._version(approval_version, "approval")
        body = dict(approval["payload"])
        body["revoked"] = True
        provenance: dict[str, Any] = {"channel": channel, "attested": channel == ATTESTING_CHANNEL}
        if isinstance(note, str) and note:
            provenance["note"] = note
        body["provenance"] = provenance
        return self._store_approval(approval["case_id"], approval["node_id"], body, caller_attested=None, previous=approval_version)

    def accept_decision(self, decision_version: str, *, by: str, approval_version: str | None = None) -> dict[str, Any]:
        """Move a current decision to ``accepted`` under a live, exactly bound approval; return a summary dict.

        Role: ``by`` must have an ``accept`` right in policies/authority.json. Judges, managers, specialists
        and every other role without one raise ``PolicyError`` (``role_cannot_accept``). The top tier (R3)
        has no accept path for anyone (``r3_no_accept_path``).

        ``decision-authority`` (right ``delegation_only``): needs ``approval_version`` with
        ``granted_by="delegation"``, ``bound_version_id`` equal to the decision's ``proposal_version_id``,
        a proposal that has not been revised since, not revoked (in the record or a later version), not
        expired, a recorded scope, and the decision's tier inside ``allowed_decisions``. A tier requiring
        human acceptance (R2) raises ``PolicyError`` (``human_required``) and sets the status to
        ``human_required``.

        ``human-owner`` (right ``true``): needs ``approval_version`` with ``granted_by="human-owner"`` and
        ``provenance.attested == true``; an unattested record raises ``PolicyError`` (``unattested_human_input``)
        and the status stays ``human_required``. The same binding, revocation and expiry rules apply, and an
        R2 decision additionally needs a verified independent review (``independent_review_required``).

        On success a new decision version with ``status="accepted"`` and the approval in ``authority_basis``
        becomes current, ``depends_on`` edges from it to the proposal and its evidence are proposed, dissent
        is carried verbatim and an event is recorded. The result carries ``"execution_permission": False``:
        acceptance is never permission to act.
        """
        decision = self._version(decision_version, "decision")
        node_id = decision["node_id"]
        payload = decision["payload"]
        current = self.store.current(node_id)
        if current is None or current["version_id"] != decision_version:
            raise ConflictError(
                "decision version is not the current version of its node",
                details={
                    "reason": "decision_version_not_current",
                    "decision_version": decision_version,
                    "current_version": current["version_id"] if current else None,
                },
            )
        status = current["status"]
        if status not in DECISION_ACCEPTABLE_FROM:
            raise TransitionError(
                f"a decision in status {status!r} cannot be accepted",
                details={"status": status, "allowed_from": sorted(DECISION_ACCEPTABLE_FROM)},
            )
        proposal_version = payload["proposal_version_id"]
        proposal = self._version(proposal_version, "proposal")
        tier = self.policies.risk_at_least(payload.get("requested_authority", "R0"), proposal["payload"]["requested_authority"])
        requires = list(self.policies.tier(tier).get("requires", []))

        path = self._accept_path(by)
        if not self.policies.executable(tier) or "human_action_request" in requires:
            raise PolicyError(
                "r3_no_accept_path",
                details={"reason": "r3_no_accept_path", "risk_tier": tier, "requires": requires, "next": "human_action_request"},
            )

        if path == "delegation":
            if "human_acceptance" in requires or self.policies.risk_rank(tier) >= self.policies.risk_rank("R2"):
                self._set_status(node_id, decision_version, "human_required", by)
                raise PolicyError(
                    "human_required",
                    details={"reason": "human_required", "risk_tier": tier, "requires": requires, "decision_version": decision_version},
                )
            approval = self._require_approval(approval_version, missing_code="delegation_required")
            grant = approval["payload"]
            if grant["granted_by"] != "delegation":
                raise PolicyError(
                    "delegation_required",
                    details={"reason": "delegation_required", "granted_by": grant["granted_by"], "approval_version": approval_version},
                )
            self._check_approval_binding(approval, proposal_version, proposal)
            if tier not in grant.get("allowed_decisions", []):
                raise PolicyError(
                    "decision_outside_delegation",
                    details={"reason": "decision_outside_delegation", "risk_tier": tier, "allowed_decisions": grant.get("allowed_decisions", [])},
                )
            if "recorded_scope" in requires and not grant.get("scope"):
                raise PolicyError("scope_not_recorded", details={"reason": "scope_not_recorded", "approval_version": approval_version})
            basis_kind = "delegation"
        else:
            approval = self._require_approval(approval_version, missing_code="approval_required")
            grant = approval["payload"]
            if grant["granted_by"] != HUMAN_OWNER:
                raise PolicyError(
                    "approval_not_from_human",
                    details={"reason": "approval_not_from_human", "granted_by": grant["granted_by"], "approval_version": approval_version},
                )
            if grant["provenance"].get("attested") is not True:
                self._set_status(node_id, decision_version, "human_required", by)
                raise PolicyError(
                    "unattested_human_input",
                    details={
                        "reason": "unattested_human_input",
                        "channel": grant["provenance"].get("channel"),
                        "approval_version": approval_version,
                        "decision_version": decision_version,
                    },
                )
            self._check_approval_binding(approval, proposal_version, proposal)
            if path == "explicit_human_delegation" and tier not in grant.get("allowed_decisions", []):
                raise PolicyError(
                    "decision_outside_delegation",
                    details={"reason": "decision_outside_delegation", "risk_tier": tier, "allowed_decisions": grant.get("allowed_decisions", [])},
                )
            if "independent_review" in requires and not self._has_independent_review([proposal_version, decision_version]):
                raise PolicyError(
                    "independent_review_required",
                    details={"reason": "independent_review_required", "risk_tier": tier, "proposal_version": proposal_version},
                )
            basis_kind = "human_input"

        dissent = payload.get("dissent", [])
        accepted = {
            **payload,
            "status": "accepted",
            "requested_authority": tier,
            "authority_basis": {"kind": basis_kind, "approval_version_id": approval_version},
            "dissent": dissent,
        }
        with self.store.transaction():
            accepted_version = self.store.put_version(node_id, accepted, author_role=by)
            self.store.set_current(node_id, accepted_version, status="accepted", by=by)
            edges = [
                self.store.add_edge(
                    accepted_version,
                    proposal_version,
                    "depends_on",
                    impact_policy="review",
                    reason="decision binds this exact proposal version",
                    proposed_by=by,
                )
            ]
            for ref in proposal["payload"].get("evidence_refs", []):
                try:
                    self.store.get_version(ref)
                except NotFoundError:
                    continue
                edges.append(
                    self.store.add_edge(
                        accepted_version,
                        ref,
                        "depends_on",
                        impact_policy="review",
                        reason="decision relies on this evidence",
                        proposed_by=by,
                    )
                )
            self._event(
                "decision.accepted",
                {
                    "decision_node": node_id,
                    "decision_version": decision_version,
                    "accepted_version": accepted_version,
                    "proposal_version": proposal_version,
                    "approval_version": approval_version,
                    "accepted_by": by,
                    "authority_basis": basis_kind,
                    "risk_tier": tier,
                    "execution_permission": False,
                    "dissent": dissent,
                    "edges": edges,
                },
                actor_role=by,
                key=f"decision.accepted:{accepted_version}",
                refs=[accepted_version, decision_version, proposal_version, approval_version],
            )
        return {
            "decision_node": node_id,
            "decision_version": decision_version,
            "accepted_version": accepted_version,
            "proposal_version": proposal_version,
            "approval_version": approval_version,
            "status": "accepted",
            "accepted_by": by,
            "authority_basis": basis_kind,
            "risk_tier": tier,
            "selected_option": payload.get("selected_option"),
            "dissent": dissent,
            "edges": edges,
            "execution_permission": False,
        }

    # ---------------------------------------------------------------------------------------------
    # Authority and budgets
    # ---------------------------------------------------------------------------------------------

    def authority_check(self, role_id: str, action: str, risk_tier: str) -> None:
        """Raise ``PolicyError`` unless ``role_id`` holds the ``action`` right at ``risk_tier``; return None.

        The principal is the special id (``human-owner``, ``decision-authority`` ...) or the agent's role type
        in policies/authority.json; an unknown id raises ``PolicyError`` (``unknown_principal``). A right of
        ``false`` refuses; a qualifier string (``assigned_only`` ...) passes here and is enforced by the method
        that performs the action. ``execute`` at a tier that is not executable in v0.1, and ``accept`` at the
        tier that requires a human action request, are refused for every principal, the human owner included:
        there is no R3 code path.
        """
        self.policies.risk_rank(risk_tier)
        principal = self._principal(role_id)
        right = self.policies.right(principal, action)
        tier = self.policies.tier(risk_tier)
        if action == "execute" and not self.policies.executable(risk_tier):
            raise PolicyError(
                "tier_not_executable",
                details={"reason": "tier_not_executable", "risk_tier": risk_tier, "role": role_id, "note": "no execution path exists for this tier in v0.1"},
            )
        if action == "accept" and (not self.policies.executable(risk_tier) or "human_action_request" in tier.get("requires", [])):
            raise PolicyError(
                "r3_no_accept_path",
                details={"reason": "r3_no_accept_path", "risk_tier": risk_tier, "role": role_id},
            )
        if right is False:
            raise PolicyError(
                f"{action}_not_permitted",
                details={"reason": f"{action}_not_permitted", "role": role_id, "principal": principal, "action": action, "risk_tier": risk_tier},
            )
        return None

    def rounds_used(self, run_id: str) -> int:
        """Number of challenge rounds opened in ``run_id`` (the highest round of its ``challenge.opened`` events)."""
        rounds = 0
        for event in self.store.events(type="challenge.opened"):
            if event.payload.get("run_id") == run_id:
                rounds = max(rounds, int(event.payload.get("round", 0)))
        return rounds

    # ---------------------------------------------------------------------------------------------
    # Internals
    # ---------------------------------------------------------------------------------------------

    def _sync_budget_rounds(self, run_id: str) -> None:
        """Raise ``budgets.used_rounds`` for the run to the rounds opened here; never lowers it."""
        used = self.rounds_used(run_id)
        for row in self.store.query("budgets", run_id=run_id):
            current = int(row.get("used_rounds") or 0)
            if used > current:
                self.store.update("budgets", row["id"], {"used_rounds": used, "updated_at": now()})

    def _require_case(self, case_id: str) -> None:
        if case_id != self.store.case_id:
            raise NotFoundError(f"unknown case {case_id!r}; this store holds {self.store.case_id!r}", details={"case_id": case_id})

    def _version(self, version_id: Any, kind: str | None = None) -> dict[str, Any]:
        if not isinstance(version_id, str) or not version_id:
            raise ValidationError("a version id is required", errors=["/version_id: must be a non-empty string"])
        version = self.store.get_version(version_id)
        if kind is not None and version["kind"] != kind:
            raise ValidationError(
                f"version {version_id!r} is a {version['kind']}, not a {kind}",
                errors=[f"/version_id: expected kind {kind!r}, found {version['kind']!r}"],
                details={"version_id": version_id, "kind": version["kind"], "expected": kind},
            )
        return version

    def _principal(self, role_id: Any) -> str:
        """Special id or role type used in policies/authority.json; unknown ids raise ``PolicyError``."""
        if isinstance(role_id, str) and role_id in self.policies.authority.get("special", {}):
            return role_id
        agent = self.registry.agents.get(role_id) if isinstance(role_id, str) else None
        if agent is not None:
            return agent.type
        raise PolicyError("unknown_principal", details={"reason": "unknown_principal", "role": role_id})

    def _producer_of(self, version: Mapping[str, Any]) -> tuple[str, str | None, str | None]:
        """``(role, session, task)`` that produced a version, resolving the session via dispatch rows."""
        payload = version["payload"]
        kind = version["kind"]
        if kind == "artifact":
            role = payload["producer_role"]
            session = payload.get("producer_session") or version.get("author_session")
            task = payload.get("producer_task") or version.get("author_task")
        elif kind == "proposal":
            role = payload["author_role"]
            session = payload.get("author_session") or version.get("author_session")
            task = version.get("author_task")
        elif kind == "claim":
            role = payload.get("assessed_by") or version["author_role"]
            session = version.get("author_session")
            task = version.get("author_task")
        else:
            role = version["author_role"]
            session = version.get("author_session")
            task = version.get("author_task")
        if session is None and task:
            for dispatch in self.store.query("dispatches", task_id=task):
                child = dispatch.get("native_child_id")
                if child:
                    session = child
                    break
        return role, session, task

    def _independence(
        self, reviewer_role: str, reviewer_session: str | None, versions: Sequence[Mapping[str, Any]]
    ) -> tuple[str, bool, bool]:
        """``(conflict_check, independent, manager_review)`` for a reviewer over the given versions."""
        conflict_check = "verified"
        manager_review = False
        for version in versions:
            role, session, _ = self._producer_of(version)
            if role == reviewer_role:
                raise PolicyError(
                    "author_cannot_review_own_artifact",
                    details={
                        "reason": "author_cannot_review_own_artifact",
                        "conflict_check": "conflict",
                        "reviewer_role": reviewer_role,
                        "version_id": version["id"],
                        "kind": version["kind"],
                    },
                )
            if reviewer_session is not None and session is not None and reviewer_session == session:
                raise PolicyError(
                    "same_session_conflict",
                    details={
                        "reason": "same_session_conflict",
                        "conflict_check": "conflict",
                        "reviewer_session": reviewer_session,
                        "version_id": version["id"],
                        "producer_role": role,
                    },
                )
            if reviewer_session is None or session is None:
                conflict_check = "unverified"
            if self._is_manager_of(reviewer_role, role):
                manager_review = True
        independent = conflict_check == "verified" and not manager_review
        return conflict_check, independent, manager_review

    def _is_manager_of(self, reviewer_role: str, producer_role: str) -> bool:
        agent = self.registry.agents.get(producer_role)
        if agent is None:
            return False
        if agent.reports_to == reviewer_role:
            return True
        return self.registry.manager_of(producer_role) == reviewer_role

    def _cited_checks(self, body: dict[str, Any]) -> list[dict[str, Any]]:
        cited: list[dict[str, Any]] = []
        raw = body.pop("observed_checks", None)
        if raw is not None:
            if not isinstance(raw, list):
                raise ValidationError("observed_checks must be a list", errors=["/observed_checks: not an array"])
            for item in raw:
                if not isinstance(item, Mapping) or "command" not in item:
                    raise ValidationError("each observed check needs a command", errors=["/observed_checks: item lacks 'command'"])
                cited.append(dict(item))
        for finding in body.get("findings", []) or []:
            if isinstance(finding, Mapping) and "command" in finding:
                cited.append(dict(finding))
        return cited

    def _require_receipts(self, cited: Sequence[Mapping[str, Any]]) -> None:
        for check in cited:
            receipt_id = check.get("receipt_id")
            if not isinstance(receipt_id, str) or not receipt_id:
                raise PolicyError(
                    "review_cites_unexecuted_check",
                    details={"reason": "review_cites_unexecuted_check", "cause": "missing_receipt_id", "command": check.get("command")},
                )
            if self.store.get_receipt(receipt_id) is None:
                raise PolicyError(
                    "review_cites_unexecuted_check",
                    details={"reason": "review_cites_unexecuted_check", "cause": "unknown_receipt", "receipt_id": receipt_id, "command": check.get("command")},
                )

    @staticmethod
    def _merge_refs(*groups: Sequence[Any]) -> list[str]:
        seen: dict[str, None] = {}
        for group in groups:
            for ref in group or []:
                if isinstance(ref, str) and ref:
                    seen.setdefault(ref, None)
        return list(seen)

    def _check_evidence_refs(self, refs: Sequence[str]) -> None:
        for ref in refs:
            try:
                self.store.get_version(ref)
                continue
            except NotFoundError:
                pass
            if self.store.get_receipt(ref) is None:
                raise NotFoundError(f"evidence ref {ref!r} is neither a version nor a receipt", details={"ref": ref})

    def _tier_of(self, versions: Sequence[Mapping[str, Any]]) -> str:
        tier = self.policies.risk_order()[0]
        for version in versions:
            requested = version["payload"].get("requested_authority") if version["kind"] in ("proposal", "decision") else None
            if isinstance(requested, str):
                tier = self.policies.risk_at_least(tier, requested)
        return tier

    @staticmethod
    def _check_proposal_options(proposal: Mapping[str, Any]) -> None:
        options = proposal.get("options")
        if not isinstance(options, list):
            raise ValidationError("proposal options must be a list", errors=["/options: not an array"])
        ids = [option.get("id") for option in options if isinstance(option, Mapping)]
        if proposal.get("recommended_option") not in ids:
            raise ValidationError(
                "recommended_option must name one of the options",
                errors=[f"/recommended_option: {proposal.get('recommended_option')!r} is not one of {ids}"],
            )

    @staticmethod
    def _ruling_refs(scope: Any) -> list[str]:
        if isinstance(scope, str):
            return [scope] if scope.startswith("ver_") else []
        if isinstance(scope, list):
            return [s for s in scope if isinstance(s, str) and s]
        if isinstance(scope, Mapping):
            refs: list[str] = []
            proposal_version = scope.get("proposal_version_id")
            if isinstance(proposal_version, str) and proposal_version:
                refs.append(proposal_version)
            for key in ("refs", "reviewed_refs"):
                for ref in scope.get(key, []) or []:
                    if isinstance(ref, str) and ref and ref not in refs:
                        refs.append(ref)
            return refs
        return []

    def _accept_path(self, by: str) -> str:
        principal = self._principal(by)
        right = self.policies.right(principal, "accept")
        if right is True:
            return "human"
        if right == "delegation_only":
            return "delegation"
        if right == "explicit_human_delegation_only":
            return "explicit_human_delegation"
        raise PolicyError(
            "role_cannot_accept",
            details={"reason": "role_cannot_accept", "role": by, "principal": principal, "accept_right": right},
        )

    def _require_approval(self, approval_version: str | None, *, missing_code: str) -> dict[str, Any]:
        if approval_version is None:
            raise PolicyError(missing_code, details={"reason": missing_code, "approval_version": None})
        return self._version(approval_version, "approval")

    def _check_approval_binding(self, approval: Mapping[str, Any], proposal_version: str, proposal: Mapping[str, Any]) -> None:
        grant = approval["payload"]
        if grant["bound_version_id"] != proposal_version:
            raise PolicyError(
                "approval_version_mismatch",
                details={
                    "reason": "approval_version_mismatch",
                    "bound_version_id": grant["bound_version_id"],
                    "proposal_version_id": proposal_version,
                },
            )
        latest = self.store.versions_of(proposal["node_id"])[-1]
        current = self.store.current(proposal["node_id"])
        newer = latest["id"] if latest["id"] != proposal_version else None
        if current is not None and current["version_id"] != proposal_version:
            newer = current["version_id"]
        if newer is not None:
            raise PolicyError(
                "proposal_superseded",
                details={"reason": "proposal_superseded", "bound_version_id": proposal_version, "current_version_id": newer},
            )
        if grant.get("revoked") is True:
            raise PolicyError("approval_revoked", details={"reason": "approval_revoked", "approval_version": approval["id"]})
        approval_current = self.store.current(approval["node_id"])
        if approval_current is not None and approval_current["version_id"] != approval["id"]:
            latest_grant = self.store.get_version(approval_current["version_id"])["payload"]
            code = "approval_revoked" if latest_grant.get("revoked") is True else "approval_superseded"
            raise PolicyError(
                code,
                details={"reason": code, "approval_version": approval["id"], "current_version": approval_current["version_id"]},
            )
        expires_at = grant.get("expires_at")
        if expires_at is not None and parse_time(expires_at) <= parse_time(now()):
            raise PolicyError(
                "approval_expired",
                details={"reason": "approval_expired", "expires_at": expires_at, "approval_version": approval["id"]},
            )

    def _has_independent_review(self, version_ids: Sequence[str]) -> bool:
        wanted = set(version_ids)
        for row in self.store.find_current("review"):
            record = row["payload"]
            if record.get("conflict_check") != "verified" or record.get("independent") is False:
                continue
            if record.get("result") not in REVIEW_PASSING:
                continue
            if any(isinstance(f, Mapping) and f.get("record_type") == _RULING_RECORD_TYPE for f in record.get("findings", [])):
                continue
            if wanted & set(record.get("reviewed_refs", [])):
                return True
        return False

    def _store_approval(
        self,
        case_id: str,
        node_id: str | None,
        body: dict[str, Any],
        *,
        caller_attested: Any,
        previous: str | None = None,
    ) -> str:
        provenance = body["provenance"]
        if body.get("revoked") is True:
            status = "revoked"
        elif provenance["attested"]:
            status = "attested"
        else:
            status = "unverified_claim"
        with self.store.transaction():
            if node_id is None:
                node_id = self.store.new_node("approval", case_id)
            version_id = self.store.put_version(node_id, body, author_role=HUMAN_OWNER)
            self.store.set_current(node_id, version_id, status=status, by="controller")
            self._event(
                "approval.recorded",
                {
                    "approval_node": node_id,
                    "approval_version": version_id,
                    "previous_version": previous,
                    "channel": provenance["channel"],
                    "attested": provenance["attested"],
                    "caller_supplied_attested": caller_attested,
                    "granted_by": body["granted_by"],
                    "bound_version_id": body["bound_version_id"],
                    "revoked": body.get("revoked", False),
                    "status": status,
                },
                actor_role="controller",
                key=f"approval.recorded:{version_id}",
                refs=[version_id, body["bound_version_id"]],
            )
        return version_id

    def _set_status(self, node_id: str, version_id: str, status: str, by: str) -> None:
        self.store.set_current(node_id, version_id, status=status, by=by)

    def _event(
        self,
        type: str,
        payload: dict[str, Any],
        *,
        actor_role: str,
        key: str,
        actor_task: str | None = None,
        refs: Sequence[str | None] = (),
    ) -> None:
        self.store.append_event(
            type,
            payload,
            actor_role=actor_role,
            actor_task=actor_task,
            expected_state_version=self.store.state_version(),
            idempotency_key=key,
            payload_refs=[r for r in refs if r],
        )


def _as_items(value: Any) -> list[Any]:
    """Coerce a ruling field into a list of strings or objects acceptable as review ``unresolved`` items."""
    if value is None:
        return []
    if isinstance(value, list):
        return [item if isinstance(item, (str, Mapping)) else str(item) for item in value]
    if isinstance(value, (str, Mapping)):
        return [value]
    return [str(value)]
