---
name: aipt-method-status-handoff
description: Status handoff, status brief, current state, resume, blockers, next queue, latest validated progress. Use when a human or a fresh session must resume a case quickly and needs a short, current brief derived from controller state: run state, active work orders, latest validated progress with applicability, blockers with next actions and the immediate queue. The controller renders the brief; this method decides what goes in and in what order. Not for the evidence ledger, research synthesis, outcome analysis or the full case report.
license: MIT
metadata:
  aipt_skill_id: "S11"
  aipt_provenance: "adapt"
  aipt_version: "0.1.0"
---

# Status handoff

Produce a short, current status brief derived from controller state: the run state, the latest validated progress, blockers with their next actions and the immediate queue, in that order.

## Purpose

The status brief is the fastest resume surface for a human or a fresh session. It is a derived view: the controller renders it from authoritative state, and this method decides what to include, what to leave out and in what order. Nothing exists only in the brief; every line resolves to a record version, and editing the brief changes no state. The deeper record (validation history, decisions, dissent, the evidence ledger) lives in the case store and the full case report; the brief points at it rather than repeating it. Applicability is whether a validation still speaks to the current version of its target; the brief shows only validations whose applicability is `current` as progress and refers to the rest as history.

## Use when

- A run has paused, completed a stage or returned `needs_input`, and the Workflow Orchestrator must hand the case to the human owner or to a new session.
- A fresh context (a new session, a reassigned auditor, the Context Analyst) needs to resume without reading the whole case history.
- A material event has changed the picture: an accepted decision, a failed audit, a blocked order, a budget limit crossed.
- The Decision Recorder or Dissent Recorder needs the current state of decisions and open objections summarized before recording.
- A human asks "where are we" and the answer must be short and traceable.

## Do not use when

- The task is to record sources, claims or versions. Use `aipt-method-evidence-and-lineage`; the brief cites records, it does not create them.
- The task is to consolidate research findings across sources. Use `aipt-method-research-consolidation`.
- The task is to judge whether an outcome was achieved or an option paid off. Use `aipt-method-outcome-and-value-analysis`.
- The reader needs the full acceptance matrix, every decision with dissent and the impact queue. Point them to the full case report, which the controller also renders; the brief is the summary that links to it.
- The task is to decide the next work orders. Use `aipt-method-milestone-planning`; the brief shows the queue the plan and the controller produced.
- The state is unknown because the controller is unavailable. Say the brief cannot be rendered instead of composing one from memory.

## Required inputs

- Run status: `run_id`, run state, budget mode, used and remaining worker tasks, from the controller's run status. Missing: the brief cannot be rendered; return `blocked`.
- Task states: every task in the run with its state (`admitted`, `running`, `submitted`, `reviewed`, `accepted`, `blocked`, `needs_input`, `rejected`) and its work order id. Missing: return `blocked`.
- Latest validations: `validation` version ids with `result` and `applicability` for each active or recently accepted order. Missing: write "no validation recorded" for that order instead of inferring progress.
- Blockers: for each `blocked` or `needs_input` task, the recorded reason, the open question, the escalation destination and any `requested_followup`. Missing reason: show the task as blocked with reason unknown.
- Ready queue: the next ready tasks in dependency order from the controller's task-next listing. Missing: show the queue as empty and say why.
- Recent reviews and decisions: `review` and `decision` versions created since the previous brief, with results. Missing: omit the line instead of summarizing from recollection.
- Target snapshot: the snapshot id the current state refers to. Missing: state "snapshot unknown".
- Previous brief, when one exists: its artifact version, used to compute what changed. Missing: mark the brief as the first for this run.

## Method

1. Read the run status and the task list. Copy the run state verbatim instead of translating `reviewing` into "almost done" or `blocked` into "on hold".
2. Select the active work orders: tasks in `admitted`, `running`, `submitted` or `reviewed`. One line each: order id, task id, state.
3. Select latest progress: the tasks accepted since the previous brief and their artifact versions, then the validations with `applicability: current` as "validated", each with its receipt id. Validations with `applicability: historical` or `invalidated` are not progress; add one line counting them and pointing at the validation records (the history stays in state, not in the brief).
4. Select blockers: every `blocked` or `needs_input` task. For each, one line with the reason and one line with the next resolving action and its owner or escalation destination. A blocker without a next action is listed as such instead of being given an invented one.
5. Select the immediate queue: the first three ready tasks in dependency order, each with its precondition and target check. If fewer than three are ready, show what is ready and why the rest are not.
6. Order the sections exactly: Current state, Latest progress, Active blockers, Immediate next queue. A reader resuming the case reads the state first and the queue last.
7. Compress: one line per item; every line carries at least one record reference; receipts are cited by id, not quoted. Keep the brief to what fits on one screen; move anything longer into a pointer to the case report.
8. Decide what to drop: items whose records are `superseded`, `archived` or `retired` since the previous brief. Any item that still affects immediate execution stays; removing one requires the ask-first step below.
9. Emit the brief as the artifact and record the selection rules used (which states counted as active, which applicability counted as validated) in `findings`, so the controller can render the same brief again from the same state.

## Output contract

Artifact `status-brief.md` with headings: Current state; Latest progress; Active blockers; Immediate next queue. The first line under the title names the run, the event sequence and the snapshot the brief was rendered from.

Artifact `status-brief.json` with keys: `run_id`, `rendered_at_event_seq`, `snapshot`, `run_state`, `budget` (`mode`, `used_tasks`, `max_worker_tasks`), `active_orders[]` (`order_id`, `task_id`, `state`, optional `waits_on`), `latest_progress` (`accepted[]`, `submitted[]`, `validated[]` with `validation_ref` and `receipt_id`, `not_established[]`, `history_count`), `blockers[]` (`task_id`, `reason`, `next_action`, `owner`), `next_queue[]` (`task_id`, `role_id`, `precondition`, `target_check`), `changed_since_previous[]`, `unknown_fields[]`.

Envelope fields this method always fills:

- `findings`: what changed since the previous brief and the selection rules applied.
- `evidence_refs`: every run, task, validation, review, decision and receipt reference cited in the brief.
- `artifact_refs`: the two brief artifacts and the previous brief version.
- `uncertainties`: fields rendered as unknown, states whose reasons are missing.
- `requested_followups`: blockers without an owner, items whose removal needs approval.
- `scope_violations`: any request to include material from outside the case or to state progress with no record.
- `proposed_links`: the brief `derived_from` the run and the previous brief.

## Evidence and uncertainty rules

- Every statement in the brief resolves to a record version; a line that cannot cite one is removed or rendered as "unknown".
- "Validated" means a `validation` record with `result: passed` and `applicability: current` backed by a receipt. A builder's `complete` status, a manager's `ready` or a passed check on an older snapshot is progress of a different kind; label it as submitted, reviewed or historical.
- The brief reports state and does not assert that a product is ready. Instead, for a `completed` run it says which gates were met.
- Record sources, claims and versions through `aipt-method-evidence-and-lineage`; the brief cites what that ledger holds and does not duplicate it.
- When the controller cannot supply a field, write "unknown" and list it in `uncertainties` instead of filling it from memory or from an earlier brief.

## Guardrails

### Always

- Keep the brief short and current: one screen, one line per item, rendered from the present state.
- Make every line resolve to a record version.
- Use the brief as the fastest resume surface for humans; the case report carries the depth.
- Show the run state verbatim and the queue in dependency order.

### Ask first

Route as a `requested_followup` to the Workflow Orchestrator or `human-owner` before:

- Removing a note that still affects immediate execution, even when its record is old.
- Changing the section order or adding a section for one reader; a different view belongs in the case report.

### Never

- Do not turn the brief into the cumulative record. Instead, cite the validation history by count and reference and leave the records in state.
- Do not duplicate large sections of the case report. Instead, give one line and a reference.
- Do not paste raw logs or command output. Instead, cite the receipt id.
- Do not edit the brief to change state. Instead, submit the record (a review, a decision, a follow-up) and re-render.
- Do not report progress without a record. Instead, show the task state and say no validation is recorded.
- Do not keep a stale "current state" after the state changed. Instead, re-render from the present state and list what changed.

## Success criteria

- The four sections appear in the fixed order and the brief fits on one screen.
- The run state is verbatim; every active order, blocker and queue item cites a task or record id.
- Validated progress cites validations with current applicability and their receipts; history is counted and referenced, not repeated.
- Every blocker has a next action or is marked as lacking one.
- Rendering the brief again from the same state produces the same brief.
- A reader who is new to the case can state the next action within a minute.

## Example

Brief for Reply Assist (Larkspur Support) after the audit of work order `wo-01` returned `fail`. The JSON artifact is shown; the Markdown rendering places the same content under the four headings in order, one line per item.

```json
{
  "run_id": "run-0003",
  "rendered_at_event_seq": 418,
  "snapshot": {"kind": "git", "commit": "3b1e9c0"},
  "run_state": "reviewing",
  "budget": {"mode": "standard", "used_tasks": 7, "max_worker_tasks": 12},
  "active_orders": [
    {"order_id": "wo-01", "task_id": "task-wo-01-a1", "state": "reviewed"},
    {"order_id": "wo-02", "task_id": "task-wo-02-a1", "state": "ready", "waits_on": "wo-01"}
  ],
  "latest_progress": {
    "accepted": [],
    "submitted": [{"order_id": "wo-01", "artifact_refs": ["art-2f9c@v3", "art-51c0@v1"], "status": "implemented_not_verified"}],
    "validated": [
      {"check": "ac-07a", "validation_ref": "val-0088", "receipt_id": "rcpt-0519", "result": "passed", "applicability": "current"},
      {"check": "ac-07b", "validation_ref": "val-0089", "receipt_id": "rcpt-0520", "result": "passed", "applicability": "current"}
    ],
    "not_established": [{"requirement": "req-07@v2", "path": "rerank", "review_ref": "rev-0031", "result": "fail"}],
    "history_count": 4
  },
  "blockers": [
    {"task_id": "task-wo-01-a1", "reason": "rev-0031: unfiltered store read at rerank.py:41", "next_action": "plan an order for the rerank read path, then re-audit", "owner": "engineering-manager"},
    {"task_id": "task-wo-02-a1", "reason": "waits on wo-01 acceptance", "next_action": null, "owner": "workflow-orchestrator"}
  ],
  "next_queue": [
    {"task_id": "task-plan-rerank", "role_id": "implementation-planner", "precondition": "dec-03@v1 still current", "target_check": "plan artifact proposed"},
    {"task_id": "task-wo-04-a1", "role_id": "integration-engineer", "precondition": "rerank order admitted", "target_check": "negative test through rerank passes"},
    {"task_id": "task-wo-01-audit-2", "role_id": "independent-auditor", "precondition": "fresh session", "target_check": "review result pass"}
  ],
  "changed_since_previous": ["rev-0031 added (fail)", "wo-02 moved from planned to ready"],
  "unknown_fields": ["production configuration for get_by_ids"]
}
```

Under Current state the Markdown rendering also lists the protected requirements in force, `req-07@v2` (workspace isolation) and `req-12@v1` (no send path), each as one line with its record reference. `findings` records the selection rules: active means `admitted`, `running`, `submitted` or `reviewed`; validated means `result: passed` with `applicability: current`.
