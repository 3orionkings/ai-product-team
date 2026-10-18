---
name: aipt-method-independent-audit
description: Independent audit, verification, frozen artifact, acceptance criteria, re-run checks, pass fail blocked, reviewer independence. Use when a delivered artifact with a pinned version must be verified against its actual acceptance criteria by someone who did not produce it, in a fresh context. Re-runs or replays the checks under receipts, inspects the files directly, and returns a review record with pass, fail or blocked and the evidence for each criterion. Not for drift comparison, structural audits, evaluation campaigns or ruling on disputed evidence.
license: MIT
metadata:
  aipt_skill_id: "S10"
  aipt_provenance: "adapt"
  aipt_version: "0.1.0"
---

# Independent audit

Verify a frozen artifact against its actual acceptance criteria in a fresh context, re-run or replay the checks, and return pass, fail or blocked with the evidence for each criterion.

## Purpose

An audit establishes whether delivered work meets the criteria it was ordered against, without relying on the builder's account of it. The artifact under audit is frozen: a specific `artifact` version id and content hash, inspected in a context that did not produce it. The audit reads the builder's report as a set of claims, replaces each claim with a receipt or a direct inspection, and records the result per criterion. A receipt is the controller's record that a command ran with a given exit status (see `aipt-method-evaluation-execution-and-receipts`). Applicability is whether a validation still speaks to the current version of its target. Independence is a recorded fact about roles and sessions, not a label a reviewer gives itself.

## Use when

- A builder has submitted a work order with artifacts in `implemented_not_verified` and the order carries `review_required` or `independence_required`.
- A gate (acceptance of an order, readiness of a release stage, a protected-requirement change) requires an independent verdict before the controller can proceed.
- A manager review returned `ready` but the stage requires independence; manager review is not an independent audit.
- A previously passed artifact has `applicability: unestablished` after a snapshot change and must be re-verified.
- The Audit Manager, Independent Auditor, Test Engineer, Security Reviewer or Accessibility Reviewer holds an assigned audit task.

## Do not use when

- The question is whether a changed artifact drifted from a baseline against declared invariants. Use `aipt-method-drift-and-regression-audit`.
- The question is structural quality across a set of artifacts (duplication, contradiction, bloat). Use `aipt-method-structural-integrity-audit`.
- The task is a measurement campaign over many cases with metrics and slices. Use `aipt-method-evaluation-execution-and-receipts` with `aipt-method-evaluation-planning`.
- Two parties dispute whether the evidence is sufficient. Use `aipt-method-evidentiary-adjudication`; the audit reports what it observed and does not rule.
- The audit target is permission enforcement, trust boundaries or data egress as such. Use `aipt-method-security-and-privacy-review` for the method; this skill supplies the independence and receipt discipline.
- You produced the artifact, or your session produced it. Refuse and request reassignment; see the conflict rule under Method step 1.

## Required inputs

- Frozen artifact under audit: `artifact` version id with `content_hash`, `producer_role`, `producer_task` and `status: implemented_not_verified`. Missing hash or a mutable reference: return `blocked`; a moving target cannot be audited.
- Actual acceptance criteria: the `requirement` version ids in the artifact's `implements_refs` and the originating work order's `acceptance_criteria`. Missing: return `blocked`; an audit against the builder's paraphrase is not an audit.
- Builder's submission: the response envelope and implementation report for the producing task, read as claims. Missing: proceed from the artifact and criteria alone and record the gap.
- Receipts cited by the builder: `receipt` ids from the builder's `observed_checks`. Missing for a check: treat that check as `claimed_only`.
- Target snapshot: the snapshot recorded for the producing task. Missing or different from the inspected tree: return `blocked` with both values.
- Reviewer identity: own role id and session or child id, and the producer's role and session from the dispatch record. Either unknown: continue, record `conflict_check: unverified` and state that gates requiring independence stay blocked.
- Available capabilities: whether commands can run, and whether a fixture replay is the only option. Missing: ask instead of assuming execution is possible.

## Method

1. Confirm independence before reading the work. Apply the conflict rule: if your role equals the artifact's `producer_role`, the audit is refused as `author_cannot_review_own_artifact`; return `out_of_scope` and request a different auditor. If your session or child id equals the producer's, record `conflict_check: conflict` and refuse likewise. If either identity is unknown, record `conflict_check: unverified`, continue, and state in `findings` that any gate requiring independence remains blocked. A manager reviewing its own team's artifact may record a manager review, not an independent audit.
2. Pin the target. Record the artifact version id and content hash, confirm the inspected tree matches the recorded snapshot, and refuse to continue on a different tree; return `blocked` with both snapshot values instead.
3. Read the actual acceptance criteria from the requirement versions and the work order. List each by id with its command or observable condition and expected result. Use the criteria's own wording; a paraphrase in the builder's report is not the criterion.
4. Read the builder's report as a numbered list of claims. For each claim, note the receipt it cites or mark it `claimed_only`. Carry no claim forward as a result; each is replaced by evidence in steps 5 and 6.
5. Inspect the changed files directly against each criterion. Record observations with file and line references, including code paths the criteria cover that the builder's checks leave unexercised.
6. Re-run each check in your own context through the receipt mechanism so it has a fresh `receipt_id`. Where only a fixture replay is possible, run it and label the result `fixture_replay`. Where a check cannot run, record `not_run` with the reason and preserve the runnable instruction.
7. Judge each criterion: `passed`, `failed` or `blocked`, each with its evidence (receipt id, file reference). Flag coverage gaps: a passing check that does not exercise the criterion's full statement is evidence for the check, not for the criterion.
8. Decide the overall result. `pass` only when every criterion is `passed` with a receipt, `conflict_check` is `verified` and no coverage gap remains. `fail` when any criterion failed or an inspection shows the requirement is not met. `blocked` when any criterion could not be established.
9. Write the review record and one validation record per re-run check. Keep the builder's claims and your observations in separate fields. List required follow-ups as resolving tasks, not as advice.

## Output contract

A `review` record: `reviewed_refs` (artifact version ids), `reviewer_role`, `reviewer_session`, `findings` (one entry per criterion with `result` and `evidence`), `evidence_sufficiency`, `result: pass | fail | blocked`, `conflict_check: verified | unverified | conflict`, `unresolved`.

One `validation` record per check re-run: `method`, `target_refs`, `receipt_id`, `result`, `rubric`, `coverage`, `applicability: current`. A replayed fixture carries `method: fixture_replay`.

Artifact `audit-report.md` with headings: Status; Scope checked; Independence; Evidence; Findings; Required follow-up.

Envelope fields this method always fills:

- `findings`: per-criterion results, coverage gaps, and the independence statement.
- `evidence_refs`: artifact, requirement, work order, snapshot and receipt versions read.
- `artifact_refs`: the review record, validation records and the report.
- `observed_checks`: every command re-run, each with its fresh `receipt_id`; replays labeled.
- `proposed_links`: each validation `verifies` its artifact version; and each validation `depends_on` the artifact version and snapshot with `impact_policy: invalidate_applicability`.
- `uncertainties`: what could not be established, paths not reachable in the audit context, unknown identities.
- `requested_followups`: resolving tasks for each failure or gap; any waiver request routed to the decision path.
- `scope_violations`: any request to audit outside the assigned artifact or to relax a criterion.

## Evidence and uncertainty rules

- Only a receipt produced in the audit context proves a check ran. The builder's receipts prove the builder's run; cite them as history, not as audit evidence.
- A `pass` result that cites any check without a `receipt_id` is invalid; the controller rejects it as `review_cites_unexecuted_check`.
- A passing check proves the command's exit status on that snapshot. State what the check exercised and what it did not; coverage is a separate finding from the exit status.
- Label direct inspection as `observation` with file and line; label beliefs about unseen configuration or data as `hypothesis`; label missing evidence as `unknown` rather than inferring a result.
- Record sources, claims and versions through `aipt-method-evidence-and-lineage`; the receipt shape and the replay label come from `aipt-method-evaluation-execution-and-receipts`.
- A validation's applicability becomes `unestablished` when the target changes after the audit. Say so instead of letting a past pass stand for a new version.

## Guardrails

### Always

- Verify the actual acceptance criteria, not a paraphrase of them.
- Prefer reproducible evidence (a fresh receipt, a file reference) over narrative claims.
- Call out missing evidence explicitly, per criterion.
- State the independence check and its result in every audit.

### Ask first

Route as a `requested_followup` to the decision path (a `decision` under `aipt-method-delegated-authority`, backed by a recorded human delegation or `human-owner` approval) before:

- Relaxing a failed acceptance criterion.
- Waiving a required verification step.
- Accepting a replay where the order required live execution.

### Never

- Do not reuse the builder's conclusion as the audit result. Instead, re-run the check or mark it `claimed_only` and let the result follow the evidence.
- Do not mark a failed check acceptable without an explicit recorded waiver. Instead, return `fail` and route the waiver request to the decision path.
- Do not audit your own artifact or one from your own session. Instead, refuse under the conflict rule and request reassignment.
- Do not audit a moving target. Instead, pin the version and hash, and return `blocked` if the tree differs.
- Do not report `pass` while any criterion lacks a receipt or any coverage gap remains. Instead, return `blocked` or `fail` with the gap named.
- Do not present a fixture replay as live execution. Instead, label it `fixture_replay` and say what it does and does not establish.

## Success criteria

- The independence check is recorded with role and session comparison, and the result is `verified`, `unverified` or `conflict` as the facts dictate.
- Every criterion has a result and evidence; no result rests on the builder's claim.
- Every re-run check has a fresh receipt; replays are labeled.
- Coverage gaps between checks and criteria are named with file references.
- The overall result follows the decision rule in step 8.
- Follow-ups are resolving tasks a planner can turn into orders.

## Example

Audit of `art-2f9c@v3` and `art-51c0@v1` from work order `wo-01` for Reply Assist (Larkspur Support), criteria `ac-07a`, `ac-07b` under protected `req-07@v2`: a ws-alpha query must return no ws-beta document.

```json
{
  "kind": "review",
  "reviewed_refs": ["art-2f9c@v3", "art-51c0@v1"],
  "reviewer_role": "independent-auditor",
  "reviewer_session": "child-9b21",
  "conflict_check": "verified",
  "evidence_sufficiency": "insufficient",
  "result": "fail",
  "findings": [
    {"criterion": "ac-07a", "result": "passed", "evidence": ["rcpt-0519"], "note": "Re-run in audit context; exit 0."},
    {"criterion": "ac-07b", "result": "passed", "evidence": ["rcpt-0520"], "note": "Re-run; exit 0. Exercises the query path only."},
    {"criterion": "req-07@v2 statement", "result": "failed",
     "evidence": ["src/reply_assist/retrieval/rerank.py:41"],
     "note": "rerank() calls store.get_by_ids() without workspace_id; a ws-beta neighbor id can reach a ws-alpha draft. No check exercises this path."}
  ],
  "builder_claims": [
    {"claim": "isolation complete", "disposition": "replaced by rcpt-0519, rcpt-0520 and the rerank inspection"},
    {"claim": "broader suite not run", "disposition": "confirmed; not run in audit either (budget)"}
  ],
  "unresolved": ["Whether get_by_ids is reachable from the draft flow under production configuration (unknown; configuration not in snapshot)."],
  "requested_followups": [
    "Plan an order for the rerank read path (aipt-method-milestone-planning).",
    "Add a negative check through rerank (aipt-method-requirements-and-acceptance, aipt-method-evaluation-execution-and-receipts).",
    "No waiver requested; relaxing req-07 would require a human decision."
  ]
}
```

Two validation records accompany the review, one per fresh receipt, each `verifies art-2f9c@v3` with `applicability: current` and `coverage: query path`.
