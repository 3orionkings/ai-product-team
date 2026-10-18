"""INCOMPLETE AND UNTESTED (experimental). This module implements ``case_init``, ``run_start`` and
``run_plan`` only; task admission, dispatch attachment, submission, review and run completion described
in docs/architecture/controller-contracts.md section 6 are not written, and there is no test file for it.
Nothing in the shipped agents, skills or workflows depends on it.

Run and task lifecycle controller: planning, admission, budgets, dispatch identity and state machines.

Single responsibility: move runs and tasks through their exact state machines while enforcing the
admission checks, transactional budget reservation and dispatch-identity rules fixed by
``docs/architecture/controller-contracts.md`` section 6. The controller checks structure, references,
versions, authority and transitions. It never judges whether evidence is persuasive, never runs
inference and never performs an external action. A command named in a response is not a command that
ran: observed checks without a receipt are recorded as claims, and a response that claims native
delegation without a matching dispatch record is downgraded to ``sequential`` (AT-08).

Persistence goes through :class:`ai_product_team.storage.CaseStore` only: operational rows in ``runs``,
``tasks``, ``dispatches`` and ``budgets``; artifacts as ``artifact`` nodes; proposed links as edges; every
state change as an event. All multi-row changes run inside one store transaction.
"""

from __future__ import annotations

import dataclasses
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from ai_product_team import ids
from ai_product_team.errors import (
    BudgetExhausted,
    NotFoundError,
    PolicyError,
    TransitionError,
    ValidationError,
)
from ai_product_team.policies import Policies
from ai_product_team.registry import HUMAN_OWNER, Agent, Registry, Stage, Workflow
from ai_product_team.storage import CaseStore
from ai_product_team.validation import ensure_valid

__all__ = [
    "CONTROLLER_ROLE",
    "RUN_TRANSITIONS",
    "TASK_TRANSITIONS",
    "RUN_TERMINAL",
    "TASK_TERMINAL",
    "TASK_ACTIVE",
    "TASK_SETTLED",
    "SNAPSHOT_ROLE_TYPES",
    "CHALLENGE_ROLE_TYPES",
    "NON_WORKER_ROLE_TYPES",
    "DEFAULT_MAX_STEPS",
    "PROHIBITED_ACTIONS",
    "Controller",
]

#: Actor recorded on every controller-originated event.
CONTROLLER_ROLE = "controller"

#: Exact run state machine (contract section 6). ``paused`` returns to the state it left, so its
#: successors are computed from the stored ``paused_from`` plus the two terminal escapes.
RUN_TRANSITIONS: dict[str, frozenset[str]] = {
    "created": frozenset({"scoped", "paused", "cancelled", "failed"}),
    "scoped": frozenset({"planned", "paused", "cancelled", "failed"}),
    "planned": frozenset({"executing", "paused", "cancelled", "failed"}),
    "executing": frozenset({"reviewing", "needs_input", "blocked", "rework", "paused", "cancelled", "failed"}),
    "reviewing": frozenset({"completed", "needs_input", "blocked", "rework", "paused", "cancelled", "failed"}),
    "needs_input": frozenset({"planned", "paused", "cancelled", "failed"}),
    "blocked": frozenset({"planned", "paused", "cancelled", "failed"}),
    "rework": frozenset({"planned", "paused", "cancelled", "failed"}),
    "paused": frozenset({"cancelled", "failed"}),
    "completed": frozenset(),
    "cancelled": frozenset(),
    "failed": frozenset(),
}
RUN_TERMINAL: frozenset[str] = frozenset({"completed", "cancelled", "failed"})

#: Exact task state machine. ``admitted -> submitted`` is the unattached submission path of AT-08: the
#: controller never saw a dispatch, so the response's execution claim is downgraded on the way through.
TASK_TRANSITIONS: dict[str, frozenset[str]] = {
    "planned": frozenset({"ready"}),
    "ready": frozenset({"admitted"}),
    "admitted": frozenset({"running", "submitted", "blocked", "needs_input", "failed", "cancelled"}),
    "running": frozenset({"submitted", "blocked", "needs_input", "failed", "cancelled"}),
    "submitted": frozenset({"reviewed", "blocked", "needs_input", "failed", "cancelled"}),
    "reviewed": frozenset({"accepted", "rejected"}),
    "accepted": frozenset(),
    "blocked": frozenset(),
    "needs_input": frozenset(),
    "rejected": frozenset(),
    "cancelled": frozenset(),
    "failed": frozenset(),
}
TASK_TERMINAL: frozenset[str] = frozenset({"accepted", "blocked", "needs_input", "rejected", "cancelled", "failed"})
#: States that hold a reserved worker slot.
TASK_ACTIVE: frozenset[str] = frozenset({"admitted", "running"})
#: States in which a task's output has been handed back (the run may move to ``reviewing``).
TASK_SETTLED: frozenset[str] = frozenset({"submitted", "reviewed", "accepted"})

#: Role types whose tasks must carry a recorded target snapshot before admission (check 4).
SNAPSHOT_ROLE_TYPES: frozenset[str] = frozenset({"builder", "auditor"})
#: Role types whose tasks consume a challenge round (check 2).
CHALLENGE_ROLE_TYPES: frozenset[str] = frozenset({"challenger"})
#: Role types that never occupy a worker slot (the root orchestrator; the human owner is handled by id).
NON_WORKER_ROLE_TYPES: frozenset[str] = frozenset({"orchestrator"})

#: Default maximum investigation steps written into a task envelope when the planner gives none.
DEFAULT_MAX_STEPS = 25
#: Actions no task envelope ever permits; there is no R3 code path in this package.
PROHIBITED_ACTIONS: tuple[str, ...] = (
    "publish",
    "deploy",
    "send",
    "pay",
    "delete_production_data",
    "broaden_access",
    "write_state_database_directly",
    "simulate_unavailable_tools",
    "dispatch_followup_work_orders",
)
_STOP_CONDITIONS: tuple[str, ...] = (
    "material_missing_user_input",
    "unavailable_required_evidence",
    "unauthorized_action_requested",
    "independent_review_conflict",
    "budget_exhausted",
    "timeout_s_reached",
)
_UNAVAILABLE_TOOLS: tuple[str, ...] = ("network", "publish", "deploy", "send", "pay")
_TOOLS_BY_SCOPE: dict[str, tuple[str, ...]] = {
    "proposal-only": ("read_sources", "write_proposals"),
    "assigned-worktree": ("read_sources", "write_assigned_worktree", "run_authorized_checks"),
    "verification-sandbox": ("read_sources", "run_authorized_checks"),
}
_EXECUTION_MODES: frozenset[str] = frozenset({"native", "sequential", "manual_handoff", "fixture_replay"})
_OBSERVATION_SOURCES: frozenset[str] = frozenset({"native", "controller", "agent_reported"})
_WRITE_SCOPES: frozenset[str] = frozenset({"proposal-only", "assigned-worktree", "verification-sandbox"})
_PASSING_REVIEW_RESULTS: frozenset[str] = frozenset({"ready", "pass"})
_PROPOSALS_PREFIX = "proposals/"


def _blank(value: Any) -> bool:
    return not isinstance(value, str) or not value.strip()


def _str_list(value: Any, pointer: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
        raise ValidationError(f"{pointer} must be a list of strings", errors=[f"{pointer}: not a list of strings"])
    return list(value)


def _under(path: str, root: str, base: str) -> bool:
    """True when ``path`` (resolved against ``base`` if relative) lies inside ``root`` (same resolution)."""
    full = os.path.normpath(os.path.join(base, path))
    top = os.path.normpath(os.path.join(base, root))
    return full == top or full.startswith(top.rstrip(os.sep) + os.sep)


def _illegal(kind: str, key: str, from_state: str, to_state: str) -> TransitionError:
    return TransitionError(
        f"illegal {kind} transition {from_state!r} -> {to_state!r} for {key}",
        details={"reason": f"illegal_{kind}_transition", kind: key, "from": from_state, "to": to_state},
    )


class Controller:
    """Runs, tasks, admission, budgets and dispatch records over one :class:`CaseStore`."""

    def __init__(self, store: CaseStore, registry: Registry, policies: Policies) -> None:
        """Bind the controller to an open store, a loaded registry and the validated policy set."""
        self.store = store
        self.registry = registry
        self.policies = policies

    # ---------------------------------------------------------------------------------------------
    # Case
    # ---------------------------------------------------------------------------------------------

    def case_init(self, project_root: Path, brief: Mapping[str, Any]) -> dict[str, Any]:
        """Record the case brief (objective, protected_constraints, source_scope, owner) and authorized roots.

        The store already holds the case row; the brief is recorded as a ``case.initialized`` event whose
        payload overlays the stored payload (see :meth:`case`). ``project_root`` becomes the first
        authorized root; ``brief["roots"]`` may add more (relative to the project root). Returns the
        effective case record.
        """
        if not isinstance(brief, Mapping):
            raise ValidationError("brief must be a JSON object", errors=["/: brief is not an object"])
        errors: list[str] = []
        if _blank(brief.get("objective")):
            errors.append("/objective: non-empty string required")
        if _blank(brief.get("owner")):
            errors.append("/owner: non-empty string required")
        for key in ("protected_constraints", "source_scope", "roots"):
            value = brief.get(key, [])
            if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
                errors.append(f"/{key}: list of strings required")
        if errors:
            raise ValidationError("invalid case brief", errors=errors)
        root = str(Path(project_root))
        payload = {
            "id": self.store.case_id,
            "objective": brief["objective"],
            "owner": brief["owner"],
            "protected_constraints": list(brief.get("protected_constraints", [])),
            "source_scope": list(brief.get("source_scope", [])),
            "project_root": root,
            "roots": [root] + [str(r) for r in brief.get("roots", [])],
        }
        with self.store.transaction():
            self._event("case.initialized", payload, refs=[self.store.case_id])
        return self.case()

    def case(self) -> dict[str, Any]:
        """Effective case record: the stored payload overlaid with the latest ``case.initialized`` event."""
        record = self.store.case()
        effective: dict[str, Any] = dict(record["payload"])
        effective["id"] = record["id"]
        for event in self.store.events(type="case.initialized"):
            effective.update(event.payload)
        effective.setdefault("source_scope", [])
        effective.setdefault("protected_constraints", [])
        effective.setdefault("roots", [])
        effective.setdefault("objective", "")
        return effective

    # ---------------------------------------------------------------------------------------------
    # Runs
    # ---------------------------------------------------------------------------------------------

    def run_start(
        self,
        case_id: str,
        workflow: str,
        mode: str,
        *,
        host: str | None,
        host_version: str | None,
    ) -> dict[str, Any]:
        """Create a run for ``workflow`` (id or name) in budget ``mode``; it is returned in state ``scoped``.

        A budgets row is created with the mode's limits and zero usage. The run's risk tier starts at the
        workflow's ``min_risk`` and is only ever raised by the route plan.
        """
        self._check_case(case_id)
        wf = self.registry.workflow(workflow)
        limits = self.policies.mode(mode)
        from ai_product_team import __version__ as package_version

        stamp = ids.now()
        run_id = ids.new_id("run")
        with self.store.transaction():
            self.store.insert(
                "budgets",
                {
                    "run_id": run_id,
                    "mode": mode,
                    "max_worker_tasks": int(limits["max_worker_tasks"]),
                    "concurrent_workers": int(limits["concurrent_workers"]),
                    "max_challenge_rounds": int(limits["max_challenge_rounds"]),
                    "used_tasks": 0,
                    "running": 0,
                    "used_rounds": 0,
                    "wallclock_limit_s": int(limits["wallclock_limit_s"]),
                    "updated_at": stamp,
                },
            )
            self.store.insert(
                "runs",
                {
                    "id": run_id,
                    "workflow_id": wf.id,
                    "workflow_name": wf.name,
                    "mode": mode,
                    "state": "created",
                    "risk_tier": wf.min_risk,
                    "host": host,
                    "host_version": host_version,
                    "package_version": package_version,
                    "execution_mode": None,
                    "started_at": stamp,
                    "ended_at": None,
                    "budget": dict(limits),
                    "limitations": [],
                    "paused_from": None,
                    "plan": None,
                    "stage_tasks": {},
                    "satisfied_stages": {},
                    "question": None,
                    "reason": None,
                },
            )
            self._event("run.started", {"id": run_id, "workflow_id": wf.id, "mode": mode, "host": host}, refs=[run_id])
            self._set_run_state(self._run(run_id), "scoped", reason="run_start")
        return self._run(run_id)

    def run_plan(self, run_id: str, route_plan: Mapping[str, Any]) -> list[dict[str, Any]]:
        """Build the run's task list from a route plan (``schemas/route-plan.schema.json``); run -> ``planned``.

        Legal from ``scoped`` and from ``needs_input``/``blocked``/``rework`` (a replan). Each included
        stage gets a task (``planned``; ``ready`` once its dependencies are accepted or absent). Stages
        pruned by ``satisfied_by_version_id`` get no task and count as satisfied for ``run_complete``.
        On a replan, stages whose current task is still live or accepted keep it; others get a new
        attempt (``attempt + 1``). Tasks depend on the previous included stage's task, in plan order.
        """
        run = self._run(run_id)
        if "planned" not in self._run_successors(run):
            raise _illegal("run", run_id, run["state"], "planned")
        plan = dict(route_plan)
        ensure_valid(plan, "route-plan")
        wf = self.registry.workflow(run["workflow_id"])
        if plan["workflow_id"] not in (wf.id, wf.name):
            raise ValidationError(
                f"route plan is for workflow {plan['workflow_id']!r}, run is {wf.id} ({wf.name})",
                errors=[f"/workflow_id: {plan['workflow_id']!r} does not match run workflow {wf.id!r}"],
            )
        if plan["mode"] != run["mode"]:
            raise ValidationError(
                f"route plan mode {plan['mode']!r} does not match run mode {run['mode']!r}",
                errors=[f"/mode: {plan['mode']!r} does not match run mode {run['mode']!r}"],
            )
        risk_tier = self.policies.risk_at_least(run["risk_tier"], plan["risk_tier"])
        case = self.case()
        stage_tasks: dict[str, str] = dict(run.get("stage_tasks") or {})
        satisfied: dict[str, str] = {}
        limitations = list(run.get("limitations") or [])
        with self.store.transaction():
            previous_task_id: str | None = None
            ordered: list[dict[str, Any]] = []
            for position, decision in enumerate(plan["stages"]):
                stage = wf.stage(decision["stage_id"])
                satisfied_by = decision.get("satisfied_by_version_id")
                if satisfied_by:
                    self.store.get_version(satisfied_by)
                    satisfied[stage.id] = satisfied_by
                    continue
                if not decision["included"]:
                    continue
                role_id = decision["role_id"]
                if not self.registry.is_role(role_id):
                    raise ValidationError(
                        f"stage {stage.id!r} names unknown role {role_id!r}",
                        errors=[f"/stages/{position}/role_id: {role_id!r} is not a registry role or human-owner"],
                    )
                deps = [previous_task_id] if previous_task_id else []
                existing = self.store.get("tasks", stage_tasks[stage.id]) if stage.id in stage_tasks else None
                if existing is not None and existing["state"] not in TASK_TERMINAL - {"accepted"}:
                    task = existing
                else:
                    attempt = (existing["attempt"] + 1) if existing else 1
                    task = self._new_task(run, case, wf, stage, role_id, risk_tier, attempt, deps, position)
                    stage_tasks[stage.id] = task["id"]
                ordered.append(task)
                previous_task_id = task["id"]
            if plan.get("human_action_request"):
                limitations.append("human_action_request: external action requested; no executable stage was planned")
            for omitted in plan.get("omitted_roles", []):
                note = f"omitted_role:{omitted['role_id']}: {omitted['reason']}"
                if note not in limitations:
                    limitations.append(note)
            self.store.update(
                "runs",
                run_id,
                {
                    "risk_tier": risk_tier,
                    "plan": plan,
                    "stage_tasks": stage_tasks,
                    "satisfied_stages": satisfied,
                    "limitations": limitations,
                    "question": None,
                },
            )
            self._event("run.planned", {"id": run_id, "task_ids": [t["id"] for t in ordered], "satisfied_stages": satisfied}, refs=[run_id])
            self._set_run_state(self._run(run_id), "planned", reason="run_plan")
            self._promote_ready(run_id)
        return [self._task(t["id"]) for t in ordered]

    def _new_task(
        self,
        run: dict[str, Any],
        case: dict[str, Any],
        wf: Workflow,
        stage: Stage,
        role_id: str,
        risk_tier: str,
        attempt: int,
        deps: list[str],
        position: int,
    ) -> dict[str, Any]:
        agent = self.registry.agents.get(role_id)
        write_scope = stage.write_scope or (agent.write_scope if agent else "proposal-only")
        if write_scope not in _WRITE_SCOPES:
            raise ValidationError(f"unknown write scope {write_scope!r}", errors=[f"/write_scope: {write_scope!r}"])
        output_paths = [_PROPOSALS_PREFIX] if write_scope == "proposal-only" else []
        stamp = ids.now()
        task_id = ids.new_id("task")
        self.store.insert(
            "tasks",
            {
                "id": task_id,
                "run_id": run["id"],
                "role_id": role_id,
                "stage_id": stage.id,
                "state": "planned",
                "attempt": attempt,
                "write_scope": write_scope,
                "risk_tier": risk_tier,
                "updated_at": stamp,
                "dependencies": deps,
                "input_refs": [],
                "output_paths": output_paths,
                "snapshot": None,
                "envelope": None,
                "position": position,
                "review": bool(stage.review),
                "independence_required": bool(stage.independence_required),
                "conditional": stage.conditional,
                "artifact_kind": stage.artifact,
                "allowed_sources": list(case.get("source_scope", [])),
                "max_steps": DEFAULT_MAX_STEPS,
                "timeout_s": self.policies.task_timeout_s(),
                "work_order_id": None,
                "execution_mode": None,
                "observed_by": None,
                "claimed_native_unobserved": False,
                "partial": False,
                "question": None,
                "reason": None,
                "review_version_id": None,
                "artifact_version_ids": [],
                "edge_ids": [],
                "observed_checks": [],
                "scope_violations": [],
                "response": None,
                "admitted_at": None,
                "running_since": None,
                "ended_at": None,
            },
        )
        self._event(
            "task.planned",
            {"id": task_id, "run_id": run["id"], "stage_id": stage.id, "role_id": role_id, "attempt": attempt, "dependencies": deps},
            actor_task=task_id,
            refs=[task_id],
        )
        return self._task(task_id)
