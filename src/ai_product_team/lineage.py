"""Evidence and dependency lineage: sources, claims, requirements, typed links, impact traversal, applicability.

Single responsibility: maintain the typed, versioned evidence graph of one case and compute deterministic
change impact over its *declared* dependencies. This module implements ``docs/architecture/controller-
contracts.md`` section 7 and architecture sections 5.4, 6.3, 6.4 and 12.

What it does
    * Records sources, claims, requirements, artifacts and validations as immutable versions with a
      current projection (:class:`ai_product_team.storage.CaseStore`).
    * Proposes, accepts and rejects typed edges. ``depends_on`` edges carry an ``impact_policy``; no
      other relation may.
    * ``contradict`` records a ``contradicts`` edge, marks the claim ``contested`` and returns a review
      task request. It never flips a claim to ``unsupported``; only ``accept_correction`` does, and only
      with a review version bound to the claim.
    * ``impact`` is a reverse breadth-first traversal over **accepted** ``depends_on`` edges in sorted
      order, so the same graph always yields the same list. It reports declared dependents only;
      ``missing_lineage`` reports what has no declared lineage so a caller cannot mistake the traversal
      for complete understanding (AT-13).
    * ``apply_impact`` queues review or invalidates applicability per policy. A protected requirement is
      never retired or invalidated: it is queued ``review_required`` with reason
      ``protected_requirement_implementation_affected``.
    * ``mark_historical`` changes a validation's applicability and leaves its result untouched.

What it never does
    It never judges whether evidence is persuasive, never invents support edges and never resolves a
    contradiction by itself. Every mutation is a store event appended inside a store transaction.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

from ai_product_team.errors import NotFoundError, PolicyError, TransitionError, ValidationError
from ai_product_team.ids import now, sha256_json
from ai_product_team.storage import (
    APPLICABILITIES,
    IMPACT_POLICIES,
    RELATIONS,
    CaseStore,
)

__all__ = [
    "CORRECTION_OUTCOMES",
    "CONTESTABLE_CLAIM_STATUSES",
    "PROTECTED_REQUIREMENT_REASON",
    "QUEUE_STATE_INVALIDATED",
    "QUEUE_STATE_REVIEW_REQUIRED",
    "SOURCE_STATUS",
    "Impact",
    "Lineage",
]

#: Outcomes :meth:`Lineage.accept_correction` may apply to a contested claim.
CORRECTION_OUTCOMES: frozenset[str] = frozenset({"supported", "unsupported", "superseded"})
#: Claim statuses that a contradiction moves to ``contested``. Others are left as they are.
CONTESTABLE_CLAIM_STATUSES: frozenset[str] = frozenset({"proposed", "supported", "contested"})
#: Queue reason used whenever an impact reaches a protected requirement.
PROTECTED_REQUIREMENT_REASON = "protected_requirement_implementation_affected"
#: ``impact_queue.state`` values written by :meth:`Lineage.apply_impact`.
QUEUE_STATE_REVIEW_REQUIRED = "review_required"
QUEUE_STATE_INVALIDATED = "invalidated"
#: Queue reason when an invalidation targets a version that is no longer the node's current version.
STALE_VERSION_REASON = "affected_version_not_current"
#: Sources have no status vocabulary in contract section 3; this is the single status they carry.
SOURCE_STATUS = "observed"

#: Actors that are always accepted as ``by`` besides registry role ids.
_BUILTIN_ACTORS: frozenset[str] = frozenset({"human-owner", "controller"})
#: Queue states considered open when de-duplicating queue rows.
_OPEN_QUEUE_STATES: frozenset[str] = frozenset({QUEUE_STATE_REVIEW_REQUIRED, QUEUE_STATE_INVALIDATED})


@dataclass(frozen=True)
class Impact:
    """One affected version found by :meth:`Lineage.impact`.

    ``path`` lists version ids from the changed version to ``affected_version`` inclusive; ``edge_id``,
    ``impact_policy`` and ``reason`` come from the ``depends_on`` edge that connects the affected version
    to its dependency on that path. ``depth`` is ``len(path) - 1``.
    """

    affected_version: str
    affected_node: str
    kind: str
    changed_version: str
    path: tuple[str, ...]
    impact_policy: str
    reason: str
    edge_id: str
    depth: int
    is_current: bool = field(default=True)

    def to_dict(self) -> dict[str, Any]:
        """Return the impact as a JSON-serialisable object."""
        return {
            "affected_version": self.affected_version,
            "affected_node": self.affected_node,
            "kind": self.kind,
            "changed_version": self.changed_version,
            "path": list(self.path),
            "impact_policy": self.impact_policy,
            "reason": self.reason,
            "edge_id": self.edge_id,
            "depth": self.depth,
            "is_current": self.is_current,
        }

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "Impact":
        """Rebuild an impact from :meth:`to_dict` output (or any mapping with the same keys)."""
        required = ("affected_version", "changed_version", "impact_policy")
        missing = [key for key in required if key not in data]
        if missing:
            raise ValidationError("impact record is incomplete", errors=[f"/{key}: required" for key in missing])
        path = tuple(str(p) for p in data.get("path", (data["changed_version"], data["affected_version"])))
        return cls(
            affected_version=str(data["affected_version"]),
            affected_node=str(data.get("affected_node", "")),
            kind=str(data.get("kind", "")),
            changed_version=str(data["changed_version"]),
            path=path,
            impact_policy=str(data["impact_policy"]),
            reason=str(data.get("reason", "")),
            edge_id=str(data.get("edge_id", "")),
            depth=int(data.get("depth", max(len(path) - 1, 0))),
            is_current=bool(data.get("is_current", True)),
        )


class Lineage:
    """Evidence/dependency service over one :class:`CaseStore`.

    ``registry`` and ``policies`` are optional. With a registry, every ``by`` actor must be a registry
    role id, ``human-owner`` or ``controller``; review requests name the assessor's reviewer. Without one,
    any non-empty actor string is accepted.
    """

    def __init__(self, store: CaseStore, registry: Any | None = None, policies: Any | None = None) -> None:
        """Bind to ``store``; keep ``registry``/``policies`` for actor checks and review-request hints."""
        if not isinstance(store, CaseStore):
            raise ValidationError("store must be a CaseStore", errors=["/store: not a CaseStore"])
        self.store = store
        self.registry = registry
        self.policies = policies

    # ---------------------------------------------------------------------------------------------
    # Records
    # ---------------------------------------------------------------------------------------------

    def add_source(self, case_id: str, payload: dict[str, Any], *, by: str) -> tuple[str, str]:
        """Record a source version and make it current with status ``observed``.

        Returns ``(node_id, version_id)``. The payload is validated against ``schemas/source``.
        """
        return self.add_record(case_id, "source", payload, by=by, status=SOURCE_STATUS)

    def add_claim(self, case_id: str, payload: dict[str, Any], *, by: str) -> tuple[str, str]:
        """Record a claim version; its ``status`` field becomes the current status. Returns ``(node_id, version_id)``."""
        return self.add_record(case_id, "claim", payload, by=by)

    def add_requirement(self, case_id: str, payload: dict[str, Any], *, by: str) -> tuple[str, str]:
        """Record a requirement version; its ``status`` becomes the current status. Returns ``(node_id, version_id)``."""
        return self.add_record(case_id, "requirement", payload, by=by)

    def add_artifact(self, case_id: str, payload: dict[str, Any], *, by: str) -> tuple[str, str]:
        """Record an artifact version; its ``status`` becomes the current status. Returns ``(node_id, version_id)``."""
        return self.add_record(case_id, "artifact", payload, by=by)

    def add_validation(self, case_id: str, payload: dict[str, Any], *, by: str) -> tuple[str, str]:
        """Record a validation version.

        The current status is the payload ``result`` and the current applicability is the payload
        ``applicability``. A ``result`` other than ``not_run`` requires a ``receipt_id`` (PolicyError
        ``result_without_receipt``): a result nobody observed is a claim, not a validation.
        """
        self._check_case(case_id)
        if not isinstance(payload, dict):
            raise ValidationError("validation payload must be a JSON object", errors=["/: not an object"])
        if payload.get("result") != "not_run" and not payload.get("receipt_id"):
            raise PolicyError(
                "a validation result other than not_run requires a receipt_id",
                details={"reason": "result_without_receipt", "result": payload.get("result")},
            )
        return self.add_record(
            case_id,
            "validation",
            payload,
            by=by,
            status=payload.get("result"),
            applicability=payload.get("applicability", "current"),
        )

    def add_record(
        self,
        case_id: str,
        kind: str,
        payload: dict[str, Any],
        *,
        by: str,
        status: str | None = None,
        applicability: str | None = None,
        node_id: str | None = None,
        author_task: str | None = None,
        author_session: str | None = None,
    ) -> tuple[str, str]:
        """Append a version of ``kind`` (a new node unless ``node_id`` is given) and make it current.

        ``status`` defaults to the payload's ``status`` field (``result`` for a validation, ``observed``
        for a source); ``applicability`` defaults to the payload's ``applicability`` or ``current``.
        Everything happens in one transaction and emits ``lineage.record_added`` after the store's own
        ``node.current_changed``.
        """
        self._check_case(case_id)
        self._check_actor(by)
        if not isinstance(payload, dict):
            raise ValidationError(f"{kind} payload must be a JSON object", errors=["/: not an object"])
        if status is None:
            status = _default_status(kind, payload)
        if not isinstance(status, str) or not status:
            raise ValidationError(f"{kind} needs a status", errors=["/status: 'status' is a required property"])
        if applicability is None:
            applicability = payload.get("applicability", "current") if kind == "validation" else "current"
        if applicability not in APPLICABILITIES:
            raise ValidationError(
                f"unknown applicability {applicability!r}",
                errors=[f"/applicability: {applicability!r} is not one of {sorted(APPLICABILITIES)}"],
            )
        with self.store.transaction():
            if node_id is None:
                node_id = self.store.new_node(kind, case_id)
            else:
                node = self.store.get_node(node_id)
                if node["kind"] != kind:
                    raise ValidationError(
                        f"node {node_id!r} is a {node['kind']}, not a {kind}",
                        errors=["/node_id: kind mismatch"],
                        details={"node_id": node_id, "kind": node["kind"], "expected": kind},
                    )
            version_id = self.store.put_version(
                node_id, payload, author_role=by, author_task=author_task, author_session=author_session
            )
            self.store.set_current(node_id, version_id, status=status, applicability=applicability, by=by, actor_task=author_task)
            self._event(
                "lineage.record_added",
                {"node_id": node_id, "version_id": version_id, "kind": kind, "status": status, "applicability": applicability},
                by=by,
                refs=[node_id, version_id],
                key=f"lineage.record_added:{version_id}",
            )
        return node_id, version_id

    # ---------------------------------------------------------------------------------------------
    # Links
    # ---------------------------------------------------------------------------------------------

    def propose_link(
        self,
        from_version: str,
        to_version: str,
        relation: str,
        *,
        impact_policy: str | None = None,
        reason: str,
        by: str,
    ) -> str:
        """Add a ``proposed`` edge ``from_version --relation--> to_version`` and return its id.

        ``depends_on`` requires an ``impact_policy``; any other relation must not carry one (both are
        :class:`ValidationError`). A version cannot link to itself. The edge is not traversed by
        :meth:`impact` until :meth:`accept_link` accepts it.
        """
        self._check_actor(by)
        self._check_link_shape(from_version, to_version, relation, impact_policy, reason)
        with self.store.transaction():
            edge_id = self.store.add_edge(
                from_version, to_version, relation, impact_policy=impact_policy, reason=reason, proposed_by=by, status="proposed"
            )
            self._event(
                "lineage.link_proposed",
                {
                    "edge_id": edge_id,
                    "from_version": from_version,
                    "to_version": to_version,
                    "relation": relation,
                    "impact_policy": impact_policy,
                    "reason": reason,
                },
                by=by,
                refs=[edge_id, from_version, to_version],
                key=f"lineage.link_proposed:{edge_id}",
            )
        return edge_id

    def accept_link(self, edge_id: str, *, by: str) -> dict[str, Any]:
        """Move a ``proposed`` edge to ``accepted`` and return the edge row.

        Accepting an already accepted edge is a no-op; accepting a rejected edge raises
        :class:`TransitionError`. Acceptance only changes the edge: claim statuses are the business of
        :meth:`contradict` and :meth:`accept_correction`.
        """
        return self._set_link_status(edge_id, "accepted", by=by, reason=None)

    def reject_link(self, edge_id: str, *, by: str, reason: str) -> dict[str, Any]:
        """Move a ``proposed`` edge to ``rejected`` with a non-empty ``reason`` and return the edge row.

        Rejecting an already rejected edge is a no-op; rejecting an accepted edge raises
        :class:`TransitionError` (lineage is corrected by superseding, not by erasing acceptance).
        """
        if not isinstance(reason, str) or not reason.strip():
            raise ValidationError("a rejection needs a reason", errors=["/reason: empty"])
        return self._set_link_status(edge_id, "rejected", by=by, reason=reason)

    def _set_link_status(self, edge_id: str, status: str, *, by: str, reason: str | None) -> dict[str, Any]:
        self._check_actor(by)
        edge = self.store.get_edge(edge_id)
        if edge["status"] == status:
            return edge
        if edge["status"] != "proposed":
            raise TransitionError(
                f"edge {edge_id!r} is {edge['status']}; only a proposed edge can become {status}",
                details={"edge_id": edge_id, "from": edge["status"], "to": status},
            )
        with self.store.transaction():
            updated = self.store.set_edge_status(edge_id, status, by)
            payload = {
                "edge_id": edge_id,
                "from_version": edge["from_version"],
                "to_version": edge["to_version"],
                "relation": edge["relation"],
                "impact_policy": edge["impact_policy"],
                "status": status,
            }
            if reason is not None:
                payload["reason"] = reason
            self._event(
                f"lineage.link_{status}",
                payload,
                by=by,
                refs=[edge_id, edge["from_version"], edge["to_version"]],
                key=f"lineage.link_{status}:{edge_id}",
            )
        return updated

    # ---------------------------------------------------------------------------------------------
    # Contradiction and correction
    # ---------------------------------------------------------------------------------------------

    def contradict(self, claim_version: str, contrary_version: str, *, by: str) -> dict[str, Any]:
        """Record that ``contrary_version`` contradicts the claim and return a review task request.

        Adds an accepted ``contrary_version --contradicts--> claim_version`` edge and sets the claim
        node's current status to ``contested`` when it is ``proposed`` or ``supported`` (``contested``
        stays ``contested``; ``unsupported`` and ``superseded`` are left as they are). It never sets
        ``unsupported``: that needs :meth:`accept_correction` with a review. The returned dict carries
        ``edge_id``, the claim and contrary ids, the status before and after, the roles excluded from
        reviewing (assessor, contradictor, contrary author) and a suggested reviewer from the registry.
        """
        self._check_actor(by)
        claim = self.store.get_version(claim_version)
        if claim["kind"] != "claim":
            raise ValidationError(
                f"{claim_version!r} is a {claim['kind']} version, not a claim",
                errors=["/claim_version: not a claim"],
                details={"version_id": claim_version, "kind": claim["kind"]},
            )
        contrary = self.store.get_version(contrary_version)
        if contrary_version == claim_version or contrary["node_id"] == claim["node_id"]:
            raise ValidationError(
                "a claim cannot contradict itself; supersede it with a new version instead",
                errors=["/contrary_version: same node as claim_version"],
            )
        node_id = claim["node_id"]
        current = self.store.current(node_id)
        current_version = current["version_id"] if current else claim_version
        previous_status = current["status"] if current else claim["payload"].get("status", "proposed")
        applicability = current["applicability"] if current else "current"
        new_status = "contested" if previous_status in CONTESTABLE_CLAIM_STATUSES else previous_status
        assessed_by = claim["payload"].get("assessed_by")
        excluded = sorted({r for r in (assessed_by, by, contrary.get("author_role")) if isinstance(r, str) and r})
        request: dict[str, Any] = {
            "kind": "review_request",
            "reason": "claim_contested",
            "case_id": self.store.case_id,
            "claim_node_id": node_id,
            "claim_version_id": claim_version,
            "claim_current_version_id": current_version,
            "contrary_version_id": contrary_version,
            "contrary_kind": contrary["kind"],
            "previous_status": previous_status,
            "status": new_status,
            "requested_by": by,
            "assessed_by": assessed_by,
            "excluded_reviewer_roles": excluded,
            "suggested_reviewer_role": self._suggest_reviewer(assessed_by, excluded),
            "reviewed_refs": [claim_version, contrary_version],
            "allowed_outcomes": sorted(CORRECTION_OUTCOMES),
            "next_step": "accept_correction",
            "requested_at": now(),
        }
        with self.store.transaction():
            edge_id = self.store.add_edge(
                contrary_version,
                claim_version,
                "contradicts",
                reason=f"contradiction recorded by {by}",
                proposed_by=by,
                status="accepted",
            )
            request["edge_id"] = edge_id
            if new_status != previous_status:
                self.store.set_current(node_id, current_version, status=new_status, applicability=applicability, by=by)
            self._event(
                "lineage.claim_contested",
                request,
                by=by,
                refs=[edge_id, node_id, claim_version, contrary_version],
                key=f"lineage.claim_contested:{edge_id}",
            )
        return request

    def accept_correction(
        self,
        claim_version: str,
        *,
        outcome: str,
        by: str,
        review_version_id: str,
    ) -> list[Impact]:
        """Apply a reviewed correction to a contested claim and return the impacts of the change.

        ``outcome`` is ``supported``, ``unsupported`` or ``superseded``. ``review_version_id`` is required
        and must be a ``review`` version whose ``reviewed_refs`` include ``claim_version`` (version
        binding; :class:`PolicyError` ``review_not_bound_to_claim``). The claim must currently be
        ``contested`` (:class:`TransitionError` otherwise). The returned impacts are computed, not
        applied: pass them to :meth:`apply_impact`.
        """
        self._check_actor(by)
        if outcome not in CORRECTION_OUTCOMES:
            raise ValidationError(
                f"unknown correction outcome {outcome!r}",
                errors=[f"/outcome: {outcome!r} is not one of {sorted(CORRECTION_OUTCOMES)}"],
            )
        if not isinstance(review_version_id, str) or not review_version_id:
            raise ValidationError(
                "accept_correction requires a review_version_id",
                errors=["/review_version_id: 'review_version_id' is a required property"],
            )
        claim = self.store.get_version(claim_version)
        if claim["kind"] != "claim":
            raise ValidationError(
                f"{claim_version!r} is a {claim['kind']} version, not a claim",
                errors=["/claim_version: not a claim"],
                details={"version_id": claim_version, "kind": claim["kind"]},
            )
        review = self.store.get_version(review_version_id)
        if review["kind"] != "review":
            raise ValidationError(
                f"{review_version_id!r} is a {review['kind']} version, not a review",
                errors=["/review_version_id: not a review"],
                details={"version_id": review_version_id, "kind": review["kind"]},
            )
        node_id = claim["node_id"]
        current = self.store.current(node_id)
        reviewed_refs = set(review["payload"].get("reviewed_refs", ()))
        bound = {claim_version, node_id}
        if current:
            bound.add(current["version_id"])
        if not (reviewed_refs & bound):
            raise PolicyError(
                "the review does not cover this claim version",
                details={"reason": "review_not_bound_to_claim", "claim_version": claim_version, "review_version_id": review_version_id},
            )
        if review["author_role"] == claim["payload"].get("assessed_by"):
            raise PolicyError(
                "the claim's assessor cannot review the correction of their own claim",
                details={"reason": "author_cannot_review_own_artifact", "role": review["author_role"]},
            )
        if current is None or current["status"] != "contested":
            raise TransitionError(
                "only a contested claim can receive a correction",
                details={"node_id": node_id, "status": current["status"] if current else None, "outcome": outcome},
            )
        current_version = current["version_id"]
        with self.store.transaction():
            self.store.set_current(node_id, current_version, status=outcome, applicability=current["applicability"], by=by)
            self._event(
                "lineage.correction_accepted",
                {
                    "claim_node_id": node_id,
                    "claim_version_id": claim_version,
                    "claim_current_version_id": current_version,
                    "outcome": outcome,
                    "review_version_id": review_version_id,
                    "reviewer_role": review["author_role"],
                },
                by=by,
                refs=[node_id, claim_version, review_version_id],
                key=f"lineage.correction_accepted:{review_version_id}:{current_version}",
            )
        impacts = self.impact(current_version)
        if current_version != claim_version:
            seen = {i.affected_version for i in impacts}
            impacts.extend(i for i in self.impact(claim_version) if i.affected_version not in seen)
        return impacts

    # ---------------------------------------------------------------------------------------------
    # Impact
    # ---------------------------------------------------------------------------------------------

    def impact(self, changed_version_id: str) -> list[Impact]:
        """Reverse breadth-first traversal over accepted ``depends_on`` edges from ``changed_version_id``.

        Every version that declares (directly or transitively) a dependency on the changed version is
        returned once, breadth first, with edges visited in ``(from_version, edge id)`` order so the
        result is deterministic. Only declared dependents are included: use :meth:`missing_lineage` to
        see what has no declared lineage at all.
        """
        self.store.get_version(changed_version_id)
        results: list[Impact] = []
        visited: set[str] = {changed_version_id}
        queue: deque[tuple[str, tuple[str, ...]]] = deque([(changed_version_id, (changed_version_id,))])
        while queue:
            dependency, path = queue.popleft()
            edges = sorted(
                self.store.edges_to(dependency, "depends_on", "accepted"),
                key=lambda e: (e["from_version"], e["id"]),
            )
            for edge in edges:
                dependent = edge["from_version"]
                if dependent in visited:
                    continue
                visited.add(dependent)
                version = self.store.get_version(dependent)
                current = self.store.current(version["node_id"])
                new_path = path + (dependent,)
                results.append(
                    Impact(
                        affected_version=dependent,
                        affected_node=version["node_id"],
                        kind=version["kind"],
                        changed_version=changed_version_id,
                        path=new_path,
                        impact_policy=edge["impact_policy"] or "none",
                        reason=edge["reason"],
                        edge_id=edge["id"],
                        depth=len(new_path) - 1,
                        is_current=bool(current and current["version_id"] == dependent),
                    )
                )
                queue.append((dependent, new_path))
        return results

    def apply_impact(self, impacts: Iterable[Impact | Mapping[str, Any]], *, by: str) -> list[dict[str, Any]]:
        """Queue and apply ``impacts`` per their policy; return the ``impact_queue`` rows written or reused.

        * ``none``: skipped, no row.
        * ``review``: a row with ``state=review_required``.
        * ``invalidate_applicability``: the affected node's current applicability becomes ``invalidated``
          (status untouched) and a row with ``state=invalidated`` is written. When the affected version
          is no longer current, nothing is invalidated and the row is ``review_required`` with reason
          ``affected_version_not_current``.
        * A protected requirement (payload ``protected: true``) is never retired or invalidated under any
          policy: it gets a ``review_required`` row with reason
          ``protected_requirement_implementation_affected``.

        An open row for the same ``(affected_version, changed_version)`` is reused rather than duplicated.
        """
        self._check_actor(by)
        rows: list[dict[str, Any]] = []
        for item in impacts:
            impact = item if isinstance(item, Impact) else Impact.from_mapping(item)
            if impact.impact_policy not in IMPACT_POLICIES:
                raise ValidationError(
                    f"unknown impact_policy {impact.impact_policy!r}",
                    errors=[f"/impact_policy: {impact.impact_policy!r} is not one of {sorted(IMPACT_POLICIES)}"],
                )
            if impact.impact_policy == "none":
                continue
            row = self._apply_one(impact, by=by)
            if row is not None:
                rows.append(row)
        return rows

    def _apply_one(self, impact: Impact, *, by: str) -> dict[str, Any] | None:
        version = self.store.get_version(impact.affected_version)
        node_id = version["node_id"]
        current = self.store.current(node_id)
        is_current = bool(current and current["version_id"] == impact.affected_version)
        protected = version["kind"] == "requirement" and bool(version["payload"].get("protected"))
        state = QUEUE_STATE_REVIEW_REQUIRED
        reason = impact.reason
        invalidate = False
        if protected:
            reason = PROTECTED_REQUIREMENT_REASON
        elif impact.impact_policy == "invalidate_applicability":
            if is_current:
                state = QUEUE_STATE_INVALIDATED
                invalidate = current is not None and current["applicability"] != "invalidated"
            else:
                reason = STALE_VERSION_REASON
        with self.store.transaction():
            existing = self._open_queue_row(impact.affected_version, impact.changed_version)
            if existing is not None and not invalidate:
                return existing
            if invalidate and current is not None:
                self.store.set_current(
                    node_id, current["version_id"], status=current["status"], applicability="invalidated", by=by
                )
            if existing is not None:
                return existing
            row_id = self.store.insert(
                "impact_queue",
                {
                    "affected_version": impact.affected_version,
                    "changed_version": impact.changed_version,
                    "impact_policy": impact.impact_policy,
                    "state": state,
                    "reason": reason,
                    "path": list(impact.path),
                    "affected_node": node_id,
                    "affected_kind": version["kind"],
                    "edge_id": impact.edge_id,
                    "protected": protected,
                    "queued_by": by,
                },
            )
            row = self.store.get("impact_queue", row_id)
            if row is None:  # pragma: no cover - the insert just succeeded inside this transaction
                raise NotFoundError("impact_queue row vanished", details={"id": row_id})
            self._event(
                "lineage.impact_queued",
                {
                    "queue_id": row_id,
                    "affected_version": impact.affected_version,
                    "affected_node": node_id,
                    "kind": version["kind"],
                    "changed_version": impact.changed_version,
                    "impact_policy": impact.impact_policy,
                    "state": state,
                    "reason": reason,
                    "protected": protected,
                    "applicability_invalidated": invalidate,
                },
                by=by,
                refs=[row_id, node_id, impact.affected_version, impact.changed_version],
                key=f"lineage.impact_queued:{row_id}",
            )
        return row

    def _open_queue_row(self, affected_version: str, changed_version: str) -> dict[str, Any] | None:
        for row in self.store.query("impact_queue", affected_version=affected_version, changed_version=changed_version):
            if row.get("state") in _OPEN_QUEUE_STATES and row.get("resolved_at") is None:
                return row
        return None

    # ---------------------------------------------------------------------------------------------
    # Applicability
    # ---------------------------------------------------------------------------------------------

    def mark_historical(self, validation_version: str, *, by: str) -> dict[str, Any]:
        """Set a validation's current applicability to ``historical``; its result stays what was observed.

        ``validation_version`` must be the node's current version (:class:`TransitionError` otherwise:
        an older version is already history). Returns the updated ``node_current`` row.
        """
        self._check_actor(by)
        version = self.store.get_version(validation_version)
        if version["kind"] != "validation":
            raise ValidationError(
                f"{validation_version!r} is a {version['kind']} version, not a validation",
                errors=["/validation_version: not a validation"],
                details={"version_id": validation_version, "kind": version["kind"]},
            )
        node_id = version["node_id"]
        current = self.store.current(node_id)
        if current is None or current["version_id"] != validation_version:
            raise TransitionError(
                "only the current validation version can be marked historical",
                details={"node_id": node_id, "version_id": validation_version, "current_version_id": current["version_id"] if current else None},
            )
        if current["applicability"] == "historical":
            return current
        with self.store.transaction():
            self.store.set_current(node_id, validation_version, status=current["status"], applicability="historical", by=by)
            self._event(
                "lineage.validation_marked_historical",
                {
                    "node_id": node_id,
                    "version_id": validation_version,
                    "result": current["status"],
                    "previous_applicability": current["applicability"],
                    "applicability": "historical",
                },
                by=by,
                refs=[node_id, validation_version],
                key=f"lineage.validation_marked_historical:{validation_version}:{self.store.state_version() + 1}",
            )
        updated = self.store.current(node_id)
        if updated is None:  # pragma: no cover - set_current just wrote the row
            raise NotFoundError("node_current row vanished", details={"node_id": node_id})
        return updated

    # ---------------------------------------------------------------------------------------------
    # Coverage and gaps
    # ---------------------------------------------------------------------------------------------

    def coverage(self, case_id: str) -> dict[str, Any]:
        """Requirement → implements → verifies coverage for every current requirement.

        Per requirement: ``implemented_by`` (artifact versions with an accepted ``implements`` edge to
        the current requirement version), ``verified_by`` (validation versions with an accepted
        ``verifies`` edge to one of those artifacts, with their current result and applicability),
        pending (proposed) edges and open impact-queue rows. The coverage label is structural:

        * ``disputed`` — a verifying validation whose current result is ``failed``, an open impact-queue
          row for the requirement, or a pending ``implements``/``verifies`` edge;
        * ``linked`` — at least one implementing artifact and one verifying validation whose current
          applicability is ``current`` and result is not ``not_run``;
        * ``missing`` — otherwise.

        Whether the linked evidence is persuasive is not decided here.
        """
        self._check_case(case_id)
        rows: list[dict[str, Any]] = []
        summary = {"linked": 0, "missing": 0, "disputed": 0, "total": 0}
        for req in self.store.find_current("requirement"):
            req_version = req["version_id"]
            implements_accepted = self.store.edges_to(req_version, "implements", "accepted")
            implements_pending = self.store.edges_to(req_version, "implements", "proposed")
            implemented_by: list[dict[str, Any]] = []
            verified_by: list[dict[str, Any]] = []
            verifies_pending: list[str] = []
            seen_validations: set[str] = set()
            for edge in sorted(implements_accepted, key=lambda e: (e["from_version"], e["id"])):
                artifact_version = edge["from_version"]
                artifact = self.store.get_version(artifact_version)
                art_current = self.store.current(artifact["node_id"])
                implemented_by.append(
                    {
                        "version_id": artifact_version,
                        "node_id": artifact["node_id"],
                        "kind": artifact["kind"],
                        "edge_id": edge["id"],
                        "status": art_current["status"] if art_current else None,
                        "is_current": bool(art_current and art_current["version_id"] == artifact_version),
                    }
                )
                verifies_pending.extend(e["id"] for e in self.store.edges_to(artifact_version, "verifies", "proposed"))
                for vedge in sorted(self.store.edges_to(artifact_version, "verifies", "accepted"), key=lambda e: (e["from_version"], e["id"])):
                    validation_version = vedge["from_version"]
                    if validation_version in seen_validations:
                        continue
                    seen_validations.add(validation_version)
                    validation = self.store.get_version(validation_version)
                    val_current = self.store.current(validation["node_id"])
                    verified_by.append(
                        {
                            "version_id": validation_version,
                            "node_id": validation["node_id"],
                            "kind": validation["kind"],
                            "edge_id": vedge["id"],
                            "verifies_version": artifact_version,
                            "result": val_current["status"] if val_current else validation["payload"].get("result"),
                            "applicability": val_current["applicability"] if val_current else validation["payload"].get("applicability"),
                            "is_current": bool(val_current and val_current["version_id"] == validation_version),
                        }
                    )
            open_impacts = [
                row["id"]
                for row in self.store.query("impact_queue", affected_version=req_version)
                if row.get("state") in _OPEN_QUEUE_STATES and row.get("resolved_at") is None
            ]
            pending_edges = sorted([e["id"] for e in implements_pending] + verifies_pending)
            failed = [v["version_id"] for v in verified_by if v["result"] == "failed"]
            applicable = [
                v["version_id"] for v in verified_by if v["applicability"] == "current" and v["result"] not in ("not_run", None)
            ]
            if failed or open_impacts or pending_edges:
                label = "disputed"
            elif implemented_by and applicable:
                label = "linked"
            else:
                label = "missing"
            summary[label] += 1
            summary["total"] += 1
            rows.append(
                {
                    "node_id": req["node_id"],
                    "version_id": req_version,
                    "statement": req["payload"].get("statement"),
                    "status": req["status"],
                    "applicability": req["applicability"],
                    "protected": bool(req["payload"].get("protected")),
                    "coverage": label,
                    "implemented_by": implemented_by,
                    "verified_by": verified_by,
                    "applicable_validations": applicable,
                    "failed_validations": failed,
                    "pending_edges": pending_edges,
                    "open_impacts": open_impacts,
                }
            )
        return {"case_id": case_id, "requirements": rows, "summary": summary}

    def missing_lineage(self, case_id: str) -> list[dict[str, Any]]:
        """Current records with no declared lineage, so :meth:`impact` is never mistaken for completeness.

        Reports artifacts with no accepted ``depends_on`` edge, requirements with no accepted
        ``implements`` edge pointing at them, and validations with no accepted ``verifies`` edge. Each
        entry carries ``pending_edges`` (proposed edges of that relation) so a caller can tell "nothing
        declared" from "declared but not yet accepted". Order follows node creation.
        """
        self._check_case(case_id)
        gaps: list[dict[str, Any]] = []
        checks: tuple[tuple[str, str, str], ...] = (
            ("artifact", "depends_on", "from"),
            ("requirement", "implements", "to"),
            ("validation", "verifies", "from"),
        )
        for kind, relation, direction in checks:
            for record in self.store.find_current(kind):
                version_id = record["version_id"]
                lookup = self.store.edges_from if direction == "from" else self.store.edges_to
                if lookup(version_id, relation, "accepted"):
                    continue
                pending = [e["id"] for e in lookup(version_id, relation, "proposed")]
                gaps.append(
                    {
                        "kind": kind,
                        "node_id": record["node_id"],
                        "version_id": version_id,
                        "status": record["status"],
                        "applicability": record["applicability"],
                        "missing": relation,
                        "direction": "outgoing" if direction == "from" else "incoming",
                        "pending_edges": pending,
                        "protected": bool(record["payload"].get("protected")) if kind == "requirement" else False,
                    }
                )
        return gaps

    # ---------------------------------------------------------------------------------------------
    # Internals
    # ---------------------------------------------------------------------------------------------

    def _check_case(self, case_id: str) -> None:
        if case_id != self.store.case_id:
            raise NotFoundError(
                f"unknown case {case_id!r}; this store holds {self.store.case_id!r}",
                details={"case_id": case_id, "store_case_id": self.store.case_id},
            )

    def _check_actor(self, by: str) -> None:
        if not isinstance(by, str) or not by:
            raise ValidationError("by must be a non-empty actor id", errors=["/by: empty"])
        agents = getattr(self.registry, "agents", None)
        if agents is not None and by not in agents and by not in _BUILTIN_ACTORS:
            raise PolicyError(
                f"unknown actor {by!r}: not a registry role, human-owner or controller",
                details={"reason": "unknown_actor", "by": by},
            )

    def _check_link_shape(
        self, from_version: str, to_version: str, relation: str, impact_policy: str | None, reason: str
    ) -> None:
        if relation not in RELATIONS:
            raise ValidationError(f"unknown relation {relation!r}", errors=[f"/relation: {relation!r} is not one of {sorted(RELATIONS)}"])
        if relation == "depends_on":
            if impact_policy is None:
                raise ValidationError(
                    "a depends_on edge must declare an impact_policy",
                    errors=["/impact_policy: 'impact_policy' is required for depends_on"],
                )
            if impact_policy not in IMPACT_POLICIES:
                raise ValidationError(
                    f"unknown impact_policy {impact_policy!r}",
                    errors=[f"/impact_policy: {impact_policy!r} is not one of {sorted(IMPACT_POLICIES)}"],
                )
        elif impact_policy is not None:
            raise ValidationError(
                f"a {relation} edge must not carry an impact_policy",
                errors=[f"/impact_policy: not allowed on relation {relation!r}"],
            )
        if not isinstance(reason, str) or not reason.strip():
            raise ValidationError("a link needs a reason", errors=["/reason: empty"])
        if from_version == to_version:
            raise ValidationError("a version cannot link to itself", errors=["/to_version: equals from_version"])
        self.store.get_version(from_version)
        self.store.get_version(to_version)

    def _suggest_reviewer(self, assessed_by: str | None, excluded: Sequence[str]) -> str | None:
        agents = getattr(self.registry, "agents", None)
        if not agents or not assessed_by:
            return None
        agent = agents.get(assessed_by)
        candidate = getattr(agent, "reviewed_by", None) if agent is not None else None
        if isinstance(candidate, str) and candidate and candidate not in excluded:
            return candidate
        return None

    def _event(
        self,
        type: str,
        payload: dict[str, Any],
        *,
        by: str,
        refs: Sequence[str] = (),
        key: str | None = None,
    ) -> Any:
        """Append a lineage event at the store's current state version with a stable idempotency key."""
        sv = self.store.state_version()
        idempotency_key = key or f"{type}:{sv + 1}:{sha256_json(payload)[:16]}"
        return self.store.append_event(
            type, payload, actor_role=by, expected_state_version=sv, idempotency_key=idempotency_key, payload_refs=list(refs)
        )


def _default_status(kind: str, payload: Mapping[str, Any]) -> Any:
    """The current-projection status a record of ``kind`` carries when the caller gives none."""
    if kind == "validation":
        return payload.get("result")
    if kind == "source":
        return SOURCE_STATUS
    return payload.get("status")
