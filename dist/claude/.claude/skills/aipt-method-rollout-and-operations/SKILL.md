---
name: aipt-method-rollout-and-operations
description: Staged rollout, release plan, cohort, canary, stopping conditions, rollback, kill switch, alert ownership, runbook, operational readiness. Use when a validated artifact version needs a plan for reaching users in stages, saying who is in each cohort, what is observed, what stops the stage, how the change is reverted and who owns each alert. Produces the plan and readiness conditions only; deployment and publication stay outside autonomous scope, and rollback counts as available only after it has been exercised in a synthetic environment with a receipt.
license: See LICENSE_PENDING.md in the repository root.
metadata:
  aipt_skill_id: "S21"
  aipt_provenance: "newly_authored"
  aipt_version: "0.1.0"
---

# Rollout and operations

## Purpose

Turn an accepted decision about a validated artifact version into a staged release plan that a human owner can approve and operators can run: cohorts, entry and exit criteria, observations, stopping conditions, rollback, recovery procedures, ownership and approval points. The plan is a `proposal`. Executing a stage, flipping a flag or publishing anything is a human action outside the team's autonomous scope; this skill produces the plan and the approval request, never the action.

Terms used here. A *stage* is a bounded exposure of the artifact to a named cohort under stated observations. A *stopping condition* is a signal, a threshold and a window that halt further exposure and trigger a named response. An *exercised rollback* is a revert that was run against the same artifact version in a synthetic environment and has a `validation` record with a receipt; a rollback without one is *untested*. An *owned alert* has an owner role, an escalation route and an acknowledgment expectation recorded in a `source`.

## Use when

- A `decision` has accepted an `artifact` version for release and a release scope is proposed (W09 "Plan bounded release").
- An operational review must judge whether a release plan is ready, conditional or blocked, and needs the plan in a form whose items can each be checked.
- A pre-mortem needs a concrete plan to attack: stages, signals and responses that failure chains can be checked against.
- An authorized work order asks for instrumentation or recovery changes, and the specification of what to observe and how to revert must exist before `aipt-method-scoped-implementation` edits anything.
- A feature already in use needs its stopping conditions, ownership or rollback revised after an incident or a change.

## Do not use when

- The artifact version lacks a current, applicable `validation` for its acceptance criteria. Use `aipt-method-independent-audit` and `aipt-method-evaluation-execution-and-receipts` first; the plan references validations, it does not create them.
- The question is whether users benefit from the feature. Use `aipt-method-outcome-and-value-analysis` for the outcome hypothesis; this skill decides what is observed during exposure, not what counts as value.
- The request is to deploy, publish, enable a flag or run a migration. Return `out_of_scope`, name the human owner, and name the `approval` record the action needs under `aipt-method-delegated-authority`.
- The task is to write monitoring or recovery code. Hand the specification from this skill to `aipt-method-scoped-implementation` under an authorized work order.
- The concern is permission enforcement, injection or data egress. Use `aipt-method-security-and-privacy-review`; its findings enter this skill as stopping conditions.

## Required inputs

| Input | Record kind | If missing |
|---|---|---|
| Accepted decision naming the exact artifact version and release scope | `decision` | Return `needs_input`; a plan cannot target an unaccepted version |
| Artifact under release, with snapshot hash | `artifact` | Return `needs_input` |
| Validations applicable to that version, with status and applicability | `validation` | Mark stage 0 blocked and name the missing validation |
| Requirements, with protected flags | `requirement` | Request them; protected requirements supply the non-negotiable stops |
| Pre-mortem or review findings on failure modes | `challenge`, `review` | Proceed, and record that recovery procedures cover only the failure modes known |
| User population, segments and workspaces for cohort design | `source` | Return `needs_input`; cohorts cannot be invented |
| Signals and controls the platform exposes (flags, dashboards, alert routes) | `source` | Mark every stage that depends on an unverified capability `conditional` |
| Ownership roster of roles, rotations and escalation routes | `source` | Mark the affected alerts unowned and the plan `blocked` |
| Baseline readings for each observation signal, with period and counts | `source` | Treat the threshold as a hypothesis and mark the stage `conditional` until the baseline is measured |

## Method

1. Freeze the target. Record the `artifact` version and hash, the `decision` version, and every `validation` whose applicability is current for this exact version. List each acceptance criterion without a current validation; if any exists, the plan starts `blocked` at stage 0 and names the evidence that unblocks it.
2. Derive non-negotiable stopping conditions from protected requirements and from security and privacy findings. Each is a signal that must read zero or hold a floor, and one breach halts exposure. For Reply Assist, a retrieval result from `ws-beta` appearing in a `ws-alpha` draft is such a stop.
3. Define the stages in order. Stage 0 runs against synthetic traffic with no users (replay or shadow). Later stages widen the cohort: internal users, one workspace at a small share, one workspace fully, all workspaces. For each stage write the cohort selection rule and exclusions, entry criteria, minimum dwell stated as volume (enough completed tasks to observe each stop signal) and as time, observations, stopping conditions, and exit criteria for the next stage.
   - Set the dwell volume from the stop signal, not from the calendar: a stage that must detect a rise of ten points in a rejection rate whose baseline is 18% needs enough completed drafts for that rise to show above noise, and the plan states that count.
   - Widen one dimension per stage (more users, or another workspace, or a riskier ticket type), so that a stop that fires can be read back to the dimension that changed.
4. Specify each observation: signal name, source of truth, pre-rollout baseline with its `source`, threshold, check frequency and the owner role who reads it. Take cost and waiting-time signals from `aipt-method-cost-and-latency-analysis` and outcome signals from `aipt-method-outcome-and-value-analysis`. A signal the platform cannot expose makes its stage `conditional` until it can.
5. Design the rollback. State what reverts (flag off, previous version, reverse migration), the expected time to revert, what state remains after the revert (for Reply Assist, drafts already shown to agents stay in the ticket history) and what does not revert. Specify the rehearsal: run the revert in a synthetic environment against the same artifact version with synthetic data for both workspaces, and record it as a `validation` with a receipt per `aipt-method-evaluation-execution-and-receipts`. Until that record is linked, mark `rollback: untested` and overall readiness `conditional`.
6. Write a recovery procedure for each failure mode taken from pre-mortem `challenge` records: detection signal, first response, owner role, data to preserve, rehearsal status. Mark any procedure rehearsed only on paper `untested`.
7. Assign ownership. Give every alert and stopping condition an owner role, a backup, an escalation route and an acknowledgment expectation, each traced to the roster `source`. An alert with no owner marks the plan `blocked`.
8. Place approval points. For each stage name the `approval` required to enter it, who grants it, and what it binds: artifact version, stage, cohort and date range. State in the plan that approval of the plan itself authorizes nothing to run.
9. Write the operating notes: where the runbook lives, which dashboard shows each signal, what support staff and users are told at each stage, and how incidents are recorded as `challenge` or `validation` records so they reach change review.
10. Produce the readiness list. Mark each item `ready`, `conditional` (with the evidence that resolves it) or `blocked` (with the owner who can unblock it). Fill the envelope and propose `depends_on` links from the plan to the decision, artifact, validation and roster versions.

## Output contract

Artifact `rollout-plan.md` with these headings in order: Target; Stopping conditions; Stages (a table with cohort, entry, dwell, observations, stop, exit); Observations; Rollback; Recovery procedures; Ownership; Approval points; Operating notes; Readiness; Open items. A companion `rollout-readiness.json` carries `target`, `overall` (`ready`, `conditional` or `blocked`), `items[]` (item, state, resolves_with, owner_role) and `rollback` (state `exercised` or `untested`, validation_ref) for the operational review.

Envelope fields this skill always fills: `findings` (readiness state per item, missing validations, unowned alerts); `evidence_refs` (decision, artifact, validation, requirement, challenge and roster versions); `artifact_refs` (plan and readiness file); `uncertainties` (unverified platform capabilities, baselines not yet measured, failure modes not covered); `requested_followups` (the rollback rehearsal, baseline measurements, roster confirmation); `proposed_links` (`depends_on` edges with `impact_policy: review`); `observed_checks` only when a rehearsal was actually run and its receipt is referenced; `scope_violations` whenever the request included deploying, publishing or enabling anything.

## Evidence and uncertainty rules

- A validation counts only if its applicability is `current` for this artifact version; a historical pass on an earlier version is listed as missing evidence. Record applicability and claim types as `aipt-method-evidence-and-lineage` specifies.
- Rollback and recovery are `untested` until a `validation` with a receipt from a synthetic environment is linked. A description of the mechanism, a configuration flag or a vendor statement does not change the state.
- A platform capability (flag, dashboard, alert route) is treated as absent until a `source` shows it; the plan says `conditional` rather than relying on it.
- A stopping threshold without a measured baseline is a hypothesis; record the baseline measurement as a followup and leave the stage `conditional`.
- Absence of complaints in a stage is not evidence of safety. A stage has cleared a signal only when the signal was observable, the dwell volume was reached and the reading is recorded.
- A statement that a stage is approved requires an `approval` record reference; a manager's favorable review creates no authority to enter a stage.
- Stage 0 evidence applies only to the distribution that was replayed. Name what live traffic contains that the replay set does not (new ticket types, another workspace, peak volume), using the sampling limits recorded by `aipt-method-evaluation-data-curation`.

## Guardrails

- Do not deploy, publish, enable a flag or run a migration because the plan was approved. Instead return the plan and an approval request addressed to the human owner, and record the request in `scope_violations` if it asked for execution.
- Do not mark rollback available because a mechanism exists. Instead keep `rollback: untested` until the synthetic rehearsal receipt is linked, and keep overall readiness `conditional`.
- Do not test a destructive recovery against production or shared data. Instead run it in a synthetic environment with synthetic workspaces and synthetic tickets, and state in the plan that a production rehearsal is a separate human decision.
- Do not leave an alert or stopping condition without an owner role. Instead mark it unowned and the plan `blocked`, naming the roster entry that would resolve it.
- Do not set a threshold without a baseline. Instead record the baseline measurement needed and mark the stage `conditional`.
- Do not log secrets, credentials or private prompt text in observations. Instead log identifiers, counts and outcomes, within the limits `aipt-method-security-and-privacy-review` sets.
- Do not write a plan that covers only the happy path. Instead include every failure mode from the pre-mortem with the stop that detects it, and name the failure modes that remain uncovered.

## Success criteria

- The target is one artifact version with its hash, decision and current validations; any gap is named at stage 0.
- Each stage has a cohort rule, entry criteria, dwell volume, observations with baselines and sources, stopping conditions with thresholds and owners, and exit criteria.
- Every protected requirement and every security or privacy finding appears as a stopping condition.
- Rollback states what reverts, what remains, how long it takes and whether it has been exercised, with the validation reference or `untested`.
- Every alert and stop has an owner role, a backup and an escalation route from the roster.
- Approval points bind artifact version, stage, cohort and dates, and the plan states that its own approval runs nothing.
- The readiness list marks each item ready, conditional or blocked with what resolves it; nothing is marked ready on an assumed capability or an untested recovery.

## Example

Reply Assist at Larkspur Support: drafts are shown to agents, never sent. The accepted decision selects `reply-assist-draft@v3` for a release to `ws-alpha` first.

```markdown
Rollout plan for reply-assist-draft@v3 (excerpt of rollout-plan.md)

### Target
Artifact `reply-assist-draft@v3` (hash 4f1c0a2e), decision `dec-0412@v1`.
Validations current for v3: `accept-check@v2` passed; `isolation-suite@v1` passed on synthetic ws-alpha and ws-beta.
Missing for acceptance: none. Rollback rehearsal: not yet recorded (see Rollback).

### Stopping conditions
| Signal | Threshold | Window | Response | Owner role |
|---|---|---|---|---|
| Cross-workspace retrieval event | > 0 | any | Halt stage; flag off; incident record | support-platform-oncall |
| Draft sent without agent action | > 0 | any | Halt stage; flag off | support-platform-oncall |
| Agent rejection rate, ws-alpha | > baseline 18% + 10 points | 24 h, n >= 200 drafts | Pause widening; review a sample | reply-assist-owner |

### Stages
| Stage | Cohort | Entry | Dwell | Exit |
|---|---|---|---|---|
| 0 | Synthetic replay, no users | Validations current | 2,000 replayed tickets | All stops read zero |
| 1 | 12 internal agents, ws-alpha | Stage 0 exit; approval `apr-0412-s1` | 5 working days or 500 completed drafts | Stops clear; p95 wait within latency-model@v1 |
| 2 | 10% of ws-alpha agents | Stage 1 exit; approval `apr-0412-s2` | 1,000 completed drafts | Stops clear |

### Rollback
Flag `reply_assist.enabled` off per workspace; expected revert under 5 minutes; drafts already shown remain in ticket history.
State: untested. Rehearsal: run flag-off and reverse migration 0007 in the synthetic environment; record as a validation with receipt.

### Readiness
ready: target, stops, cohorts, ownership. conditional: rollback (rehearsal receipt); ws-beta baseline for stage 3 (not yet measured). blocked: none.
```
