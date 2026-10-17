"""Request routing: classify a request, evaluate workflow predicates and produce a visible route plan.

Single responsibility: turn a request plus the current case state into a ``route-plan`` record (contract
section 10 and its section 14 addendum, architecture sections 5.2, 8.1 and 8.3). The router selects the
closest workflow or a narrow specialist route, raises the risk tier by every applicable policy minimum
(never lowering one), evaluates the closed predicate allowlist, prunes stages that a current accepted
artifact already satisfies, and reports the budget fit. It never dispatches anything: admission in the
controller enforces what the plan proposes.

Algorithm (contract section 10)
    1. An explicit workflow or role wins; otherwise the dated keyword table in ``policies/routing-keywords.json``
       picks the workflow, falling back to the lowest-complexity workflow when nothing matches.
    2. The action kind is ``external_action`` when an external-action keyword or an external risk trigger
       matches; such a request is routed at the top risk tier with ``human_action_request=true`` and no
       executable stage. There is no code path for an R3 action.
    3. The effective risk tier is ``risk_at_least`` over the workflow's ``min_risk``, every matching trigger
       in ``policies/risk.json``, the case's own floor and the protected-scope minimum (R2).
    4. A narrow request (``narrow_request_patterns``) yields only the roles of its ``narrow_routes`` entry,
       never directors, judges or every specialist (AT-06).
    5. For a full workflow every non-conditional stage is included, a conditional stage only when its
       predicate is true, and a stage is pruned (``satisfied_by_version_id``) when a current accepted
       artifact of its ``artifact`` type exists, except ``review`` and ``independence_required`` stages,
       which are never pruned. The director (and the manager, if absent from the stages) is added only when
       ``consequential_or_disputed`` holds.
    6. ``budget_check`` compares the selected worker tasks with ``max_worker_tasks`` for the mode; the plan
       is returned even when it does not fit.

Keyword matching tokenises both the request and the phrase (lower case, alphanumeric runs, a trailing
plural ``s`` dropped from words of four letters or more) and looks for the phrase's token sequence inside
the request's. Matching is deterministic and never reads anything but the request text and the policies.
"""

from __future__ import annotations

import dataclasses
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

from ai_product_team.errors import NotFoundError, ValidationError
from ai_product_team.validation import ensure_valid

__all__ = [
    "ACCEPTED_ARTIFACT_STATUSES",
    "ACTION_KINDS",
    "CONFIDENCES",
    "CHANGE_VERBS",
    "LOCAL_EXECUTION_WORKFLOWS",
    "NARROW_DIFF_CHECK_ROLE",
    "NON_NARROW_ROLE_TYPES",
    "PROTECTED_SCOPE_MIN_RISK",
    "PROTECTED_IMPACT_REASON",
    "FIXTURE_ARTIFACT_KINDS",
    "RETRIEVAL_ARTIFACT_KINDS",
    "RoutePlan",
    "CaseState",
    "Router",
    "tokens",
    "phrase_in",
]

#: A route plan is the JSON object validated against ``schemas/route-plan.schema.json``.
RoutePlan = dict[str, Any]

#: Artifact statuses that count as *accepted* for pruning and for ``missing_current_artifact``.
ACCEPTED_ARTIFACT_STATUSES: frozenset[str] = frozenset({"verified_for_scope"})
CONFIDENCES: tuple[str, ...] = ("exact", "keyword", "fallback")
ACTION_KINDS: tuple[str, ...] = ("analysis", "proposed_change", "local_execution", "external_action")
#: Workflows whose normal course runs code or evaluations locally (builders, runners).
LOCAL_EXECUTION_WORKFLOWS: frozenset[str] = frozenset({"W04", "W05", "W07"})
#: Verbs that mark a request as a proposed change rather than analysis (matched as whole tokens).
CHANGE_VERBS: frozenset[str] = frozenset(
    {"fix", "change", "rewrite", "reword", "update", "edit", "modify", "revise", "correct", "amend", "replace", "adjust", "tweak"}
)
#: Added to a narrow proposed-change route as the "narrow diff check" of architecture section 8.3.
NARROW_DIFF_CHECK_ROLE = "change-impact-analyst"
#: Role types a narrow route may never activate (AT-06: no compulsory director/manager/judge ladder).
NON_NARROW_ROLE_TYPES: frozenset[str] = frozenset({"leader", "manager", "adversarial_orchestrator", "judge", "decision_maker"})
#: Protected requirements, authority rules, sensitive data flows and release criteria are R2 at minimum.
PROTECTED_SCOPE_MIN_RISK = "R2"
#: ``impact_queue.reason`` written by lineage when a protected requirement's implementation is affected.
PROTECTED_IMPACT_REASON = "protected_requirement_implementation_affected"
#: Accepted artifacts whose presence means evaluation fixtures or held-out cases exist.
FIXTURE_ARTIFACT_KINDS: frozenset[str] = frozenset({"dataset-manifest.json", "evaluation-plan.json"})
#: Accepted artifacts whose presence means retrieval is part of the accepted design.
RETRIEVAL_ARTIFACT_KINDS: frozenset[str] = frozenset({"retrieval-contract.md"})
_RETRIEVAL_STEM = "retriev"
_ORCHESTRATOR_TYPE = "orchestrator"
_HUMAN_OWNER = "human-owner"
_SETTLED_DECISION_STATUSES: frozenset[str] = frozenset({"accepted", "rejected", "superseded"})
_OPEN_CHALLENGE_STATES: frozenset[str] = frozenset({"open", "unresolved"})
_TOKEN_RE = re.compile(r"[a-z0-9]+")


# --------------------------------------------------------------------------------------------------
# Tokenising
# --------------------------------------------------------------------------------------------------


def tokens(text: str) -> tuple[str, ...]:
    """Normalised word tokens of ``text``: lower case alphanumeric runs, trailing plural ``s`` dropped.

    The plural rule applies to words of four or more letters not ending in ``ss`` so that ``requirements``
    and ``requirement`` (or ``traces`` and ``trace``) compare equal. Both the request and every policy
    phrase go through this function, so the comparison is symmetric.
    """
    out: list[str] = []
    for tok in _TOKEN_RE.findall(text.lower()):
        if len(tok) >= 4 and tok.endswith("s") and not tok.endswith("ss"):
            tok = tok[:-1]
        out.append(tok)
    return tuple(out)


def phrase_in(phrase: str, request_tokens: Sequence[str]) -> bool:
    """True when the token sequence of ``phrase`` occurs contiguously in ``request_tokens``."""
    needle = tokens(phrase)
    n = len(needle)
    if n == 0 or n > len(request_tokens):
        return False
    hay = tuple(request_tokens)
    return any(hay[i : i + n] == needle for i in range(len(hay) - n + 1))


# --------------------------------------------------------------------------------------------------
# Case state
# --------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class CaseState:
    """The slice of case state the router reads. Build it with :meth:`from_store` or directly in tests.

    ``current_artifacts`` maps an artifact kind (a workflow stage ``artifact``) to the version id of the
    current, accepted artifact of that kind. The boolean and count fields feed the predicates; ``risk_floor``
    is the case's own minimum tier, which the router only ever raises. ``source_scope`` is the case's
    authorised source scope, carried into explicit-role plans.
    """

    current_artifacts: dict[str, str] = field(default_factory=dict)
    has_retrieval: bool = False
    protected_scope_touched: bool = False
    material_conflicts: int = 0
    unresolved_dissent: int = 0
    risk_floor: str = "R0"
    evidence_points_to_code: bool = False
    rework_required: bool = False
    revalidation_required: bool = False
    improvement_has_fixtures: bool = False
    source_scope: tuple[str, ...] = ()
    case_id: str | None = None

    @classmethod
    def from_store(cls, store: Any, case_id: str) -> "CaseState":
        """Derive the routing view of ``case_id`` from a :class:`~ai_product_team.storage.CaseStore`.

        Derivations (all from the current-state projection and the operational tables; nothing is judged):

        * ``current_artifacts``: current artifacts with applicability ``current`` and a status in
          :data:`ACCEPTED_ARTIFACT_STATUSES`, keyed by payload ``kind`` (newest node wins).
        * ``has_retrieval``: case flag, an accepted artifact in :data:`RETRIEVAL_ARTIFACT_KINDS`, or an
          approved current requirement whose statement mentions retrieval.
        * ``protected_scope_touched``: case flag, or an unresolved ``impact_queue`` row that carries
          :data:`PROTECTED_IMPACT_REASON` or targets a current protected requirement version.
        * ``material_conflicts``: current claims whose projected status is ``contested``.
        * ``unresolved_dissent``: current challenges in ``open``/``unresolved`` plus current decisions that
          record dissent and are not yet accepted, rejected or superseded.
        * ``rework_required``: case flag, an invalidated current artifact or requirement, or an artifact in
          ``changes_required``. ``revalidation_required``: case flag, an invalidated current validation, or
          an artifact in ``revalidation_required``. ``improvement_has_fixtures``: case flag or an accepted
          artifact in :data:`FIXTURE_ARTIFACT_KINDS`. ``evidence_points_to_code``: case flag only.

        Case flags are booleans under the case payload's ``flags`` object (or top-level keys of the same
        name). ``risk_floor`` and ``source_scope`` are read from the payload. Raises
        :class:`~ai_product_team.errors.NotFoundError` when the store holds a different case.
        """
        if case_id != store.case_id:
            raise NotFoundError(
                f"store holds case {store.case_id!r}, not {case_id!r}",
                details={"case_id": case_id, "store_case_id": store.case_id},
            )
        payload = store.case()["payload"]
        if not isinstance(payload, dict):
            payload = {}
        raw_flags = payload.get("flags")
        flags: Mapping[str, Any] = raw_flags if isinstance(raw_flags, dict) else {}

        def flag(name: str) -> bool:
            value = flags.get(name, payload.get(name))
            return value is True

        artifacts = store.find_current("artifact")
        current_artifacts: dict[str, str] = {}
        artifact_invalidated = False
        changes_required = False
        revalidation_flagged = False
        for rec in artifacts:
            kind = rec["payload"].get("kind") if isinstance(rec.get("payload"), dict) else None
            if rec.get("applicability") == "invalidated":
                artifact_invalidated = True
            if rec.get("status") == "changes_required":
                changes_required = True
            if rec.get("status") == "revalidation_required":
                revalidation_flagged = True
            if isinstance(kind, str) and kind and rec.get("applicability") == "current" and rec.get("status") in ACCEPTED_ARTIFACT_STATUSES:
                current_artifacts[kind] = rec["version_id"]

        requirements = store.find_current("requirement")
        protected_versions: set[str] = set()
        requirement_invalidated = False
        requirement_mentions_retrieval = False
        for rec in requirements:
            rec_payload = rec.get("payload") if isinstance(rec.get("payload"), dict) else {}
            if rec_payload.get("protected") is True and rec.get("applicability") == "current":
                protected_versions.add(rec["version_id"])
            if rec.get("applicability") == "invalidated":
                requirement_invalidated = True
            statement = rec_payload.get("statement")
            if rec.get("status") == "approved" and rec.get("applicability") == "current" and isinstance(statement, str):
                if _RETRIEVAL_STEM in statement.lower():
                    requirement_mentions_retrieval = True

        queue_rows = store.query("impact_queue")
        protected_touched = flag("protected_scope_touched")
        for row in queue_rows:
            if row.get("resolved_at") is not None:
                continue
            if row.get("reason") == PROTECTED_IMPACT_REASON or row.get("affected_version") in protected_versions:
                protected_touched = True
                break

        material_conflicts = sum(1 for rec in store.find_current("claim") if rec.get("status") == "contested")

        unresolved = sum(1 for rec in store.find_current("challenge") if rec.get("status") in _OPEN_CHALLENGE_STATES)
        for rec in store.find_current("decision"):
            rec_payload = rec.get("payload") if isinstance(rec.get("payload"), dict) else {}
            dissent = rec_payload.get("dissent")
            has_dissent = bool(dissent) if isinstance(dissent, (list, str)) else False
            if has_dissent and rec.get("status") not in _SETTLED_DECISION_STATUSES:
                unresolved += 1

        validation_invalidated = any(rec.get("applicability") == "invalidated" for rec in store.find_current("validation"))

        risk_floor = payload.get("risk_floor")
        if not isinstance(risk_floor, str) or not risk_floor:
            risk_floor = "R0"
        raw_scope = payload.get("source_scope")
        source_scope = tuple(item for item in raw_scope if isinstance(item, str)) if isinstance(raw_scope, list) else ()

        return cls(
            current_artifacts=current_artifacts,
            has_retrieval=flag("has_retrieval")
            or requirement_mentions_retrieval
            or any(kind in current_artifacts for kind in RETRIEVAL_ARTIFACT_KINDS),
            protected_scope_touched=protected_touched,
            material_conflicts=material_conflicts,
            unresolved_dissent=unresolved,
            risk_floor=risk_floor,
            evidence_points_to_code=flag("evidence_points_to_code"),
            rework_required=flag("rework_required") or artifact_invalidated or requirement_invalidated or changes_required,
            revalidation_required=flag("revalidation_required") or validation_invalidated or revalidation_flagged,
            improvement_has_fixtures=flag("improvement_has_fixtures") or any(kind in current_artifacts for kind in FIXTURE_ARTIFACT_KINDS),
            source_scope=source_scope,
            case_id=store.case_id,
        )


# --------------------------------------------------------------------------------------------------
# Router
# --------------------------------------------------------------------------------------------------


def _risk_rank(policies: Any, tier: str) -> int:
    return int(policies.risk_rank(tier))


def _pred_missing_current_artifact(router: "Router", state: CaseState, artifact: str | None) -> bool:
    if artifact is None:
        raise ValidationError(
            "missing_current_artifact needs the stage artifact type",
            errors=["/artifact: required to evaluate 'missing_current_artifact'"],
        )
    return artifact not in state.current_artifacts


def _pred_requires_retrieval(router: "Router", state: CaseState, artifact: str | None) -> bool:
    return state.has_retrieval


def _pred_changes_protected_scope(router: "Router", state: CaseState, artifact: str | None) -> bool:
    return state.protected_scope_touched


def _pred_material_conflict(router: "Router", state: CaseState, artifact: str | None) -> bool:
    return state.material_conflicts > 0


def _pred_independent_review_required(router: "Router", state: CaseState, artifact: str | None) -> bool:
    policies = router.policies
    return _risk_rank(policies, state.risk_floor) >= _risk_rank(policies, PROTECTED_SCOPE_MIN_RISK)


def _pred_consequential_or_disputed(router: "Router", state: CaseState, artifact: str | None) -> bool:
    return _pred_independent_review_required(router, state, artifact) or state.unresolved_dissent > 0


def _pred_evidence_points_to_code(router: "Router", state: CaseState, artifact: str | None) -> bool:
    return state.evidence_points_to_code


def _pred_rework_required(router: "Router", state: CaseState, artifact: str | None) -> bool:
    return state.rework_required


def _pred_revalidation_required(router: "Router", state: CaseState, artifact: str | None) -> bool:
    return state.revalidation_required


def _pred_improvement_needs_evaluation(router: "Router", state: CaseState, artifact: str | None) -> bool:
    return state.improvement_has_fixtures


_PREDICATE_EVALUATORS: dict[str, Callable[["Router", CaseState, str | None], bool]] = {
    "missing_current_artifact": _pred_missing_current_artifact,
    "requires_retrieval": _pred_requires_retrieval,
    "changes_protected_scope": _pred_changes_protected_scope,
    "material_conflict": _pred_material_conflict,
    "independent_review_required": _pred_independent_review_required,
    "consequential_or_disputed": _pred_consequential_or_disputed,
    "evidence_points_to_code": _pred_evidence_points_to_code,
    "rework_required": _pred_rework_required,
    "revalidation_required": _pred_revalidation_required,
    "improvement_needs_evaluation": _pred_improvement_needs_evaluation,
}


class Router:
    """Deterministic request router over a :class:`~ai_product_team.registry.Registry` and :class:`~ai_product_team.policies.Policies`.

    Construction checks that the routing policy is consistent with the registry: every keyword workflow id
    and the fallback resolve, every narrow route names an existing agent of a permitted type, and every
    narrow request pattern has a route. Inconsistency raises :class:`~ai_product_team.errors.ValidationError`
    so an edited policy file cannot silently route to nothing.
    """

    def __init__(self, registry: Any, policies: Any) -> None:
        """Bind the router to a loaded registry and policy set and validate the routing table."""
        self.registry = registry
        self.policies = policies
        self._keyword_table: dict[str, list[str]] = policies.workflow_keywords()
        self._external_keywords: list[str] = policies.external_action_keywords()
        self._narrow_patterns: list[str] = policies.narrow_request_patterns()
        raw_routes = policies.routing_keywords.get("narrow_routes")
        self._narrow_routes: dict[str, list[str]] = {
            str(k): list(v) for k, v in raw_routes.items() if isinstance(v, list)
        } if isinstance(raw_routes, dict) else {}
        fallback = policies.routing_keywords.get("fallback")
        self._fallback_workflow: str = fallback.get("workflow_id", "W01") if isinstance(fallback, dict) else "W01"
        self._validate_table()

    # -- construction checks -------------------------------------------------------------------------

    def _validate_table(self) -> None:
        errors: list[str] = []
        for workflow_id in self._keyword_table:
            if workflow_id not in self.registry.workflows:
                errors.append(f"/workflows/{workflow_id}: not a registry workflow")
        if self._fallback_workflow not in self.registry.workflows:
            errors.append(f"/fallback/workflow_id: {self._fallback_workflow!r} is not a registry workflow")
        for pattern in self._narrow_patterns:
            if pattern not in self._narrow_routes:
                errors.append(f"/narrow_routes/{pattern}: narrow request pattern has no route")
        for pattern, roles in self._narrow_routes.items():
            if not roles:
                errors.append(f"/narrow_routes/{pattern}: route is empty")
            for role_id in roles:
                agent = self.registry.agents.get(role_id)
                if agent is None:
                    errors.append(f"/narrow_routes/{pattern}: {role_id!r} is not a registry agent")
                elif agent.type in NON_NARROW_ROLE_TYPES:
                    errors.append(f"/narrow_routes/{pattern}: {role_id!r} is a {agent.type}; narrow routes never activate directors, managers or judges")
        if errors:
            raise ValidationError("routing-keywords.json is inconsistent with the registry", errors=errors, details={"file": "policies/routing-keywords.json"})

    # -- helpers -------------------------------------------------------------------------------------

    @staticmethod
    def _require_text(request: Any) -> str:
        if not isinstance(request, str) or not request.strip():
            raise ValidationError("request must be a non-empty string", errors=["/request: non-empty string required"])
        return request

    def _top_tier(self) -> str:
        return self.policies.risk_order()[-1]

    def _agent(self, role_id: Any) -> Any:
        if not isinstance(role_id, str) or role_id not in self.registry.agents:
            raise NotFoundError(f"unknown role {role_id!r}", details={"role_id": role_id})
        return self.registry.agents[role_id]

    def _agent_type(self, role_id: str) -> str | None:
        agent = self.registry.agents.get(role_id)
        return agent.type if agent is not None else None

    def _match_workflow(self, request_tokens: Sequence[str]) -> tuple[str, str, list[str]]:
        """Return ``(workflow_id, confidence, matched_phrases)`` for the keyword stage."""
        best_id: str | None = None
        best_score: tuple[int, int] = (0, 0)
        best_phrases: list[str] = []
        for workflow_id, phrases in self._keyword_table.items():
            matched = [p for p in phrases if phrase_in(p, request_tokens)]
            if not matched:
                continue
            score = (len(matched), sum(len(tokens(p)) for p in matched))
            if best_id is None or score > best_score:
                best_id, best_score, best_phrases = workflow_id, score, matched
        if best_id is None:
            return self._fallback_workflow, "fallback", []
        workflow = self.registry.workflow(best_id)
        exact = phrase_in(workflow.name, request_tokens) or workflow.id.lower() in request_tokens
        return best_id, ("exact" if exact else "keyword"), best_phrases

    def _narrow_matches(self, request_tokens: Sequence[str]) -> tuple[list[str], list[str]]:
        """Return ``(patterns, roles)`` for every narrow request pattern present, roles de-duplicated in order."""
        patterns = [p for p in self._narrow_patterns if phrase_in(p, request_tokens)]
        roles: list[str] = []
        for pattern in patterns:
            for role_id in self._narrow_routes.get(pattern, []):
                if role_id not in roles:
                    roles.append(role_id)
        return patterns, roles

    def _action_kind(self, request_tokens: Sequence[str], workflow_id: str, external: Sequence[str], triggers: Sequence[Mapping[str, Any]]) -> str:
        if external or any(t.get("action_kind") == "external_action" for t in triggers):
            return "external_action"
        if any(t.get("action_kind") == "proposed_change" for t in triggers) or any(tok in CHANGE_VERBS for tok in request_tokens):
            return "proposed_change"
        if workflow_id in LOCAL_EXECUTION_WORKFLOWS:
            return "local_execution"
        return "analysis"

    # -- public API ----------------------------------------------------------------------------------

    def classify(self, request: str) -> dict[str, Any]:
        """Classify ``request`` without case state.

        Returns ``workflow_id``, ``workflow_name``, ``confidence`` (``exact`` when the request names the
        workflow, ``keyword`` when the dated table matched, ``fallback`` otherwise), ``action_kind``,
        ``risk_tier`` (the workflow's ``min_risk`` raised by every matching trigger; the top tier for an
        external action) and the evidence: ``matched_phrases``, ``external_action_keywords``,
        ``risk_triggers``, ``narrow_patterns`` and ``narrow_roles``.
        """
        text = self._require_text(request)
        request_tokens = tokens(text)
        external = [k for k in self._external_keywords if phrase_in(k, request_tokens)]
        triggers = self.policies.risk_triggers(text)
        narrow_patterns, narrow_roles = self._narrow_matches(request_tokens)
        workflow_id, confidence, matched = self._match_workflow(request_tokens)
        workflow = self.registry.workflow(workflow_id)
        action_kind = self._action_kind(request_tokens, workflow.id, external, triggers)
        risk = self.policies.risk_at_least(workflow.min_risk, self.policies.risk_floor(text))
        if action_kind == "external_action":
            risk = self.policies.risk_at_least(risk, self._top_tier())
        return {
            "workflow_id": workflow.id,
            "workflow_name": workflow.name,
            "confidence": confidence,
            "action_kind": action_kind,
            "risk_tier": risk,
            "matched_phrases": matched,
            "external_action_keywords": external,
            "risk_triggers": [t["keyword"] for t in triggers],
            "narrow_patterns": narrow_patterns,
            "narrow_roles": narrow_roles,
        }

    def evaluate_predicate(self, name: str, case_state: CaseState, *, artifact: str | None = None) -> bool:
        """Evaluate one predicate from the closed allowlist in ``registry/workflows.json`` against ``case_state``.

        ``missing_current_artifact`` is stage-specific and needs ``artifact`` (the stage's output type).
        A name outside the registry's predicates, or one this router has no evaluator for, raises
        :class:`~ai_product_team.errors.ValidationError`; predicates are never arbitrary code.
        """
        if not isinstance(case_state, CaseState):
            raise ValidationError("case_state must be a CaseState", errors=["/case_state: not a CaseState"])
        known = self.registry.predicates
        if not isinstance(name, str) or name not in known:
            raise ValidationError(
                f"unknown predicate {name!r}",
                errors=[f"/conditional: {name!r} is not one of {sorted(known)}"],
                details={"predicate": name},
            )
        evaluator = _PREDICATE_EVALUATORS.get(name)
        if evaluator is None:
            raise ValidationError(
                f"predicate {name!r} has no evaluator in the router",
                errors=[f"/conditional: {name!r} is declared but not evaluable"],
                details={"predicate": name},
            )
        return bool(evaluator(self, case_state, artifact))

    def route(
        self,
        request: str,
        *,
        case_state: CaseState,
        mode: str,
        explicit_workflow: str | None = None,
        explicit_role: str | None = None,
    ) -> RoutePlan:
        """Produce a route plan for ``request`` and return it as a validated ``route-plan`` dict.

        ``mode`` is a budget mode (``focused``, ``standard``, ``deep``). ``explicit_workflow`` (id or name)
        and ``explicit_role`` (agent id) win over classification; an explicit role yields a one-stage plan
        carrying the role's write scope and the case's source scope under ``explicit``. An external action
        request, explicit or not, is returned at the top tier with ``human_action_request=true`` and no
        included stage. Unknown mode, workflow or role raise :class:`~ai_product_team.errors.NotFoundError`.
        """
        text = self._require_text(request)
        if not isinstance(case_state, CaseState):
            raise ValidationError("case_state must be a CaseState", errors=["/case_state: not a CaseState"])
        budget = self.policies.mode(mode)
        classification = self.classify(text)

        explicit: bool | dict[str, Any] = False
        if explicit_workflow is not None:
            workflow = self.registry.workflow(explicit_workflow)
            confidence = "exact"
            explicit = {"workflow": workflow.id}
        else:
            workflow = self.registry.workflow(classification["workflow_id"])
            confidence = classification["confidence"]
        role = None
        if explicit_role is not None:
            role = self._agent(explicit_role)
            explicit = dict(explicit) if isinstance(explicit, dict) else {}
            explicit.update({"role": role.id, "write_scope": role.write_scope, "source_scope": list(case_state.source_scope)})

        policies = self.policies
        risk = policies.risk_at_least(workflow.min_risk, classification["risk_tier"])
        risk = policies.risk_at_least(risk, case_state.risk_floor)
        if case_state.protected_scope_touched:
            risk = policies.risk_at_least(risk, PROTECTED_SCOPE_MIN_RISK)
        action_kind = classification["action_kind"]
        external = action_kind == "external_action" or not policies.executable(risk)
        if external:
            risk = policies.risk_at_least(risk, self._top_tier())
            action_kind = "external_action"
        state = dataclasses.replace(case_state, risk_floor=risk)
        predicates = self._evaluate_all(state, workflow)

        if role is not None:
            stages, omitted = self._explicit_role_stages(role, workflow)
        elif explicit_workflow is None and classification["narrow_roles"]:
            stages, omitted = self._narrow_stages(classification, action_kind, workflow)
        else:
            stages, omitted = self._workflow_stages(workflow, state, predicates)

        if external:
            reason = f"external action ({risk}): outside autonomous execution; a human action request is returned instead"
            for decision in stages:
                decision["included"] = False
                decision["reason"] = reason
                decision.pop("satisfied_by_version_id", None)
            omitted = self._omitted_from_stages(stages, [], reason)

        selected_roles = self._selected_roles(stages)
        selected_tasks = sum(1 for d in stages if d["included"] and self._agent_type(d["role_id"]) != _ORCHESTRATOR_TYPE)
        max_tasks = int(budget["max_worker_tasks"])
        plan: RoutePlan = {
            "request": text,
            "workflow_id": workflow.id,
            "mode": mode,
            "risk_tier": risk,
            "selected_roles": selected_roles,
            "omitted_roles": [o for o in omitted if o["role_id"] not in selected_roles],
            "stages": stages,
            "predicates": predicates,
            "budget_check": {
                "fits": selected_tasks <= max_tasks,
                "selected_tasks": selected_tasks,
                "max_worker_tasks": max_tasks,
                "overflow": max(0, selected_tasks - max_tasks),
            },
            "explicit": explicit,
            "confidence": confidence,
            "action_kind": action_kind,
            "human_action_request": external,
        }
        ensure_valid(plan, "route-plan")
        return plan

    # -- plan builders -------------------------------------------------------------------------------

    def _evaluate_all(self, state: CaseState, workflow: Any) -> dict[str, bool]:
        """Every stage-independent predicate, plus ``missing_current_artifact`` over the workflow's stage artifacts."""
        out: dict[str, bool] = {}
        for name in self.registry.predicates:
            if name == "missing_current_artifact":
                out[name] = any(stage.artifact not in state.current_artifacts for stage in workflow.stages)
            elif name in _PREDICATE_EVALUATORS:
                out[name] = self.evaluate_predicate(name, state)
        return out

    def _workflow_stages(self, workflow: Any, state: CaseState, predicates: Mapping[str, bool]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        stages: list[dict[str, Any]] = []
        for stage in workflow.stages:
            decision: dict[str, Any] = {"stage_id": stage.id, "role_id": stage.role, "included": True, "reason": ""}
            gate = stage.review or stage.independence_required
            if stage.conditional:
                value = self.evaluate_predicate(stage.conditional, state, artifact=stage.artifact)
                if not value:
                    decision["included"] = False
                    decision["reason"] = f"conditional stage: predicate {stage.conditional!r} is false"
                    stages.append(decision)
                    continue
                decision["reason"] = f"conditional stage: predicate {stage.conditional!r} is true"
            if not gate:
                satisfied_by = state.current_artifacts.get(stage.artifact)
                if satisfied_by is not None:
                    decision["included"] = False
                    decision["satisfied_by_version_id"] = satisfied_by
                    decision["reason"] = f"pruned: current accepted artifact {stage.artifact!r} already exists"
                    stages.append(decision)
                    continue
                if not decision["reason"]:
                    decision["reason"] = f"required stage; no current accepted {stage.artifact!r}"
            else:
                gate_kind = "independence-required review gate" if stage.independence_required else "review gate"
                suffix = "; never pruned" if stage.artifact in state.current_artifacts else ""
                decision["reason"] = (decision["reason"] + "; " if decision["reason"] else "") + f"{gate_kind}{suffix}"
            stages.append(decision)

        stage_roles = {stage.role for stage in workflow.stages}
        consequential = bool(predicates.get("consequential_or_disputed"))
        omitted: list[dict[str, Any]] = []
        director = self.registry.director_of(workflow.manager) if workflow.manager in self.registry.agents else None
        if consequential:
            if workflow.manager in self.registry.agents and workflow.manager not in stage_roles:
                stages.append({"stage_id": "manager-review", "role_id": workflow.manager, "included": True, "reason": "manager review: consequential or disputed"})
            if director is not None and director not in stage_roles:
                stages.append({"stage_id": "director-review", "role_id": director, "included": True, "reason": "director review: consequential or disputed"})
        elif director is not None and director not in stage_roles:
            omitted.append({"role_id": director, "reason": "director review not required: not consequential or disputed"})
        for role_id in workflow.conditional_specialists:
            omitted.append({"role_id": role_id, "reason": "conditional specialist: not triggered by the request or case state"})
        omitted = self._omitted_from_stages(stages, omitted, None)
        return stages, omitted

    def _narrow_stages(self, classification: Mapping[str, Any], action_kind: str, workflow: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        patterns = ", ".join(repr(p) for p in classification["narrow_patterns"])
        roles = list(classification["narrow_roles"])
        if action_kind == "proposed_change" and NARROW_DIFF_CHECK_ROLE in self.registry.agents and NARROW_DIFF_CHECK_ROLE not in roles:
            roles.append(NARROW_DIFF_CHECK_ROLE)
        stages = [
            {
                "stage_id": f"narrow-{role_id}",
                "role_id": role_id,
                "included": True,
                "reason": (
                    f"narrow request ({patterns}): {role_id} only"
                    if role_id != NARROW_DIFF_CHECK_ROLE or role_id in classification["narrow_roles"]
                    else "narrow diff check for a proposed change"
                ),
            }
            for role_id in roles
        ]
        omitted: list[dict[str, Any]] = []
        seen: set[str] = set(roles)
        for stage in workflow.stages:
            if stage.role not in seen and self.registry.is_role(stage.role):
                seen.add(stage.role)
                omitted.append({"role_id": stage.role, "reason": f"narrow request: full workflow {workflow.id} not required"})
        director = self.registry.director_of(workflow.manager) if workflow.manager in self.registry.agents else None
        if director is not None and director not in seen:
            seen.add(director)
            omitted.append({"role_id": director, "reason": "narrow request: no director review"})
        for role_id in workflow.conditional_specialists:
            if role_id not in seen:
                seen.add(role_id)
                omitted.append({"role_id": role_id, "reason": "narrow request: conditional specialist not needed"})
        return stages, omitted

    def _explicit_role_stages(self, role: Any, workflow: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        stage = {
            "stage_id": f"explicit-{role.id}",
            "role_id": role.id,
            "included": True,
            "reason": f"explicit role selection; write scope {role.write_scope!r}; classified workflow {workflow.id} not expanded",
        }
        return [stage], []

    # -- plan assembly -------------------------------------------------------------------------------

    def _selected_roles(self, stages: Sequence[Mapping[str, Any]]) -> list[str]:
        out: list[str] = []
        for decision in stages:
            role_id = decision["role_id"]
            if decision["included"] and role_id not in out and self.registry.is_role(role_id):
                out.append(role_id)
        return out

    def _omitted_from_stages(self, stages: Sequence[Mapping[str, Any]], base: Sequence[Mapping[str, Any]], reason: str | None) -> list[dict[str, Any]]:
        """Merge ``base`` with the roles of excluded stages (first reason wins), skipping roles that are included."""
        included = {d["role_id"] for d in stages if d["included"]}
        out: list[dict[str, Any]] = []
        seen: set[str] = set()
        for decision in stages:
            role_id = decision["role_id"]
            if decision["included"] or role_id in included or role_id in seen or not self.registry.is_role(role_id):
                continue
            seen.add(role_id)
            out.append({"role_id": role_id, "reason": reason if reason is not None else decision["reason"]})
        for entry in base:
            role_id = entry["role_id"]
            if role_id in included or role_id in seen or not self.registry.is_role(role_id):
                continue
            seen.add(role_id)
            out.append({"role_id": role_id, "reason": reason if reason is not None else entry["reason"]})
        return out
