---
name: aipt-method-milestone-planning
description: Milestone planning, work orders, execution order, write sets, dependencies, acceptance checks. Use when approved requirements and an authorizing decision exist and the work must be split into bounded controller work orders that a builder can implement and verify in one loop. Produces a dependency-ordered plan in which each order declares scope, write set, prerequisites, acceptance checks and the receipts it must produce. Not for writing requirements, implementing a change or staging a release.
license: MIT
metadata:
  aipt_skill_id: "S08"
  aipt_provenance: "adapt"
  aipt_version: "0.1.0"
---

# Milestone planning

Break approved work into bounded work orders, each with scope, write set, dependencies, acceptance checks and the evidence it must produce, ordered so that the smallest order that unlocks the rest comes first.

## Purpose

The plan is the single source of truth for execution order. It turns approved requirements into units that one builder can implement and one auditor can verify in a single loop, and it states for every unit what is in scope, what is out of scope and how completion will be proven. A work order is the bounded task packet the controller admits: `{id, task_id, role_id, envelope}`, where the envelope carries the objective, input references, write scope, output paths, prohibited actions, budget, acceptance criteria and return instruction. A receipt is the controller's record that a command ran with a given exit status (see `aipt-method-evaluation-execution-and-receipts`). The plan proposes work orders; the controller mints and admits them, and the plan leaves completion to controller state.

## Use when

- An accepted `decision` authorizes a change and the `requirement` records it covers have status `approved`, but no work orders exist yet.
- A builder or manager reports that the current order is too large to implement and verify in one loop and asks for it to be split.
- A material implementation run has finished and the remaining work must be re-derived from the new validation records.
- A new or changed dependency (a changed source, a failed audit, a superseded decision) invalidates the current order sequence.
- The Engineering Manager or Workflow Orchestrator needs dependency-ordered orders with write sets before dispatch.

## Do not use when

- Requirements are missing, vague or lack acceptance criteria. Use `aipt-method-requirements-and-acceptance` first; a plan built on an objective without criteria is not implementation-ready.
- The task is to implement one authorized order. Use `aipt-method-scoped-implementation`.
- The task is to verify a delivered order. Use `aipt-method-independent-audit`.
- The work is a staged release with cohorts, stop conditions and rollback. Use `aipt-method-rollout-and-operations`.
- The work is an evaluation campaign with metrics, slices and thresholds. Use `aipt-method-evaluation-planning`.
- The question is which option to choose. Use `aipt-method-evidentiary-adjudication` or `aipt-method-delegated-authority`; planning starts after the decision is recorded.

## Required inputs

- Approved requirements: `requirement` version ids with status `approved`, each with acceptance criteria and its `protected` flag. Missing or without criteria: return `needs_input` naming the requirement ids that lack criteria. Instead of guessing criteria, request them from `aipt-method-requirements-and-acceptance`.
- Authorizing decision: `decision` version id with status `accepted` whose selected option names the work. Missing: proceed only with the plan marked conditional in `uncertainties`, and request the decision in `requested_followups`.
- Target snapshot: `artifact` version of the repository or document set to be changed (git commit plus dirty-diff hash, or a content manifest). Missing: return `needs_input`; orders cannot declare write sets against an unknown target.
- Current validated state: latest `validation` records with `applicability: current` and, when present, the derived status brief from `aipt-method-status-handoff`. Missing: proceed and record in `uncertainties` that no prior validation was available.
- Run constraints from the task envelope: budget mode, risk tier, authorized roots and prohibited actions. Missing: assume the most conservative values (focused mode, risk raised one tier) and say so.
- Protected constraints: the subset of requirements flagged `protected`. Missing flag information: treat every requirement touching data scope, permissions or external actions as protected until told otherwise.

## Method

1. Read the approved requirements and the authorizing decision. List every requirement id the plan must cover. If any covered requirement has no acceptance criteria, stop and return `needs_input` with the ids instead of continuing on a paraphrase.
2. Read the target snapshot and the current validations. Mark what is already `verified_for_scope` with current applicability so it is not re-planned, and mark what has `applicability: historical` or `invalidated` so it is re-checked rather than reused.
3. Partition the work into units that one builder can implement and one auditor can verify in a single loop: one write set, one coherent change, one set of checks that can run within the order's budget. Split any unit whose write set crosses two unrelated modules or whose checks need two environments.
4. For each unit write, in this order: goal, why now, in scope, out of scope, write set (the exact output paths the builder may change), prohibited actions, blocking dependencies, follow-on orders.
5. For each unit write acceptance checks tied to requirement ids. Each check is automated (command plus expected result) or manual (observable condition plus who observes it). Every check names the receipt it must produce. Include at least one negative or refusal check for every protected requirement the unit touches.
6. Order the units by blocking dependencies. Choose as the first ready order the smallest unit that unlocks the most downstream work, not the largest or the most visible.
7. Assign a risk tier per unit, conservatively. Raise the tier when a unit touches a protected requirement, a permission, a data scope or an external action. Mark `review_required` for every unit and `independence_required` for every unit at or above R1 that touches a protected requirement.
8. Record risks and open questions per unit. Anything that would change a requirement or a decision becomes a `requested_followup` addressed to the decision path; the plan does not resolve it in a note.
9. Emit the plan artifact, then propose links: each order `implements` its requirement versions, each order `depends_on` its blocking orders, and the plan `derived_from` the decision version.
10. After each material implementation run, re-derive the plan from the new validation and review records. Update order status only from controller state; a builder's narrative that an order is finished changes nothing until a validation record exists.

## Output contract

Artifact `milestone-plan.json`, status `proposed`, with keys:

- `plan_version`, `target_snapshot`, `covers_requirements` (requirement version ids), `decision_ref`.
- `work_orders[]`, each with `id`, `title`, `goal`, `why_now`, `in_scope`, `out_of_scope`, `write_set`, `prohibited_actions`, `depends_on`, `follow_on`, `acceptance_checks[]` (`id`, `requirement_ref`, `kind: automated | manual`, `command` or `observable`, `expected`, `receipt_required`), `evidence_required`, `risk_tier`, `review_required`, `independence_required`, `status: proposed`.
- `first_ready_order` and `coverage_gaps` (requirement ids with no order).

Envelope fields this method always fills:

- `findings`: coverage summary, the chosen first order and why, requirements that no order covers.
- `evidence_refs`: the requirement, decision, snapshot and validation versions read.
- `artifact_refs`: the plan artifact.
- `proposed_links`: the edges listed in step 9: `implements` and `derived_from` edges with a reason; `depends_on` edges with a reason and an `impact_policy` (normally `review` for order-to-order dependencies).
- `uncertainties`: conditional assumptions, unknown dependencies, estimates labeled as hypotheses.
- `requested_followups`: missing criteria, requirement or decision changes, reviewer assignments.
- `scope_violations`: any requested order that would write outside the authorized roots or exceed the run's risk tier.

## Evidence and uncertainty rules

- An order is complete only when every acceptance check has a receipt and a `validation` record with `result: passed` and `applicability: current`. The plan reports `status: proposed` for every order and leaves completion to controller state.
- Record the sources, claims and versions the plan rests on through `aipt-method-evidence-and-lineage`; this method does not keep its own ledger.
- Label effort estimates, assumed dependencies and expected check outcomes as `hypothesis`. A dependency inferred from reading code rather than from a declared edge is an `observation` with its file reference.
- When the snapshot changes after planning, the plan's write sets and checks have `applicability: unestablished` until re-derived. Say so instead of presenting the old plan as current.
- A validation that passed on an earlier snapshot is a historical pass. Cite it as history instead of counting it as evidence for the new snapshot.

## Guardrails

### Always

- Prefer the smallest next order that unlocks downstream work.
- State in scope, out of scope and how completion is proven for every order.
- Re-derive the plan before and after each material implementation run.
- Carry a negative or refusal check for every protected requirement touched.

### Ask first

Return `needs_input` or a `requested_followup` addressed to the Engineering Manager or `human-owner` before:

- Reordering orders whose sequence has external impact (a commitment another team waits on, a release gate).
- Removing or weakening an acceptance check.
- Planning any order at R2 or above; the plan may describe it but the decision path authorizes it.

### Never

- Do not treat a vague objective as implementation-ready. Instead, return `needs_input` naming the missing acceptance criteria.
- Do not leave an order's validation empty. Instead, give every order at least one check with a receipt requirement, or mark the order `blocked` with the reason no check can be stated.
- Do not mark an order done in the plan. Instead, cite the validation record and let controller state carry the status.
- Do not fold a requirement change into a plan note. Instead, raise it as a `requested_followup` to the decision path and keep the protected requirement in force.
- Do not plan writes outside the authorized roots. Instead, record the need in `scope_violations` and stop.

## Success criteria

- Every approved requirement in scope maps to at least one order; `coverage_gaps` is empty or explained.
- Every order has a write set, blocking dependencies, acceptance checks with receipt requirements, a risk tier and a review flag.
- The first ready order is the smallest unit that unlocks the most downstream work, and the reason is stated.
- No order carries a completion claim; statuses are all `proposed`.
- Every protected requirement touched has a negative or refusal check.
- The plan can be re-derived from the cited record versions without consulting the planner.

## Example

Reply Assist (Larkspur Support) drafts support replies and has no send path. Decision `dec-03@v1` accepted the option "store-side workspace filter". Requirements: `req-07@v2` (protected) "Retrieval returns only documents whose workspace equals the requesting workspace"; `req-12@v1` "Drafts are written to the review queue; no send path exists."

```json
{
  "plan_version": "plan-reply-assist-v2",
  "target_snapshot": {"kind": "git", "commit": "3b1e9c0", "dirty_diff_sha256": null},
  "covers_requirements": ["req-07@v2", "req-12@v1"],
  "decision_ref": "dec-03@v1",
  "first_ready_order": "wo-01",
  "coverage_gaps": [],
  "work_orders": [
    {
      "id": "wo-01",
      "title": "Workspace filter in retrieval query",
      "goal": "Every retrieval call carries the requesting workspace and the store rejects any document from another workspace.",
      "why_now": "req-07 is protected; wo-02 depends on the filter existing.",
      "in_scope": ["query builder", "store filter", "isolation tests"],
      "out_of_scope": ["ranking changes", "draft queue"],
      "write_set": ["src/reply_assist/retrieval/", "tests/retrieval/"],
      "prohibited_actions": ["adding a send path", "editing req-07 wording"],
      "depends_on": [],
      "follow_on": ["wo-02"],
      "acceptance_checks": [
        {"id": "ac-07a", "requirement_ref": "req-07@v2", "kind": "automated",
         "command": "pytest tests/retrieval/test_workspace_isolation.py -k positive",
         "expected": "exit 0; a ws-alpha query returns only ws-alpha documents", "receipt_required": true},
        {"id": "ac-07b", "requirement_ref": "req-07@v2", "kind": "automated",
         "command": "pytest tests/retrieval/test_workspace_isolation.py -k cross_workspace",
         "expected": "exit 0; a ws-alpha query for a ws-beta document returns zero results", "receipt_required": true}
      ],
      "evidence_required": ["one receipt per check", "validation with applicability current"],
      "risk_tier": "R1", "review_required": true, "independence_required": true, "status": "proposed"
    },
    {"id": "wo-02", "title": "Draft queue write path with no send capability",
     "depends_on": ["wo-01"], "acceptance_checks": ["ac-12a (automated)", "ac-12b (manual: reviewer confirms no send control)"],
     "risk_tier": "R1", "status": "proposed"}
  ]
}
```

Envelope: `proposed_links` carries `wo-01 implements req-07@v2`, `wo-02 depends_on wo-01` and `plan derived_from dec-03@v1`; `uncertainties` records "ranking module may read the store directly (hypothesis, unverified)".
