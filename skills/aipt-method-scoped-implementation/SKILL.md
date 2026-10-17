---
name: aipt-method-scoped-implementation
description: Scoped implementation, builder loop, smallest safe diff, work order, targeted checks, receipts, files changed. Use when one authorized work order with a write set, acceptance criteria and a pinned snapshot must be turned into a verified change. Inspects before editing, keeps the diff inside the write set, runs the targeted checks under receipts and reports exact files, checks, receipts and residual risks. Not for planning the work, auditing it, or running an evaluation campaign.
license: See LICENSE_PENDING.md in the repository root.
metadata:
  aipt_skill_id: "S09"
  aipt_provenance: "adapt"
  aipt_version: "0.1.0"
---

# Scoped implementation

Implement one authorized work order with the smallest safe diff, run the targeted checks under receipts, and report exactly which files changed, which checks ran and what remains.

## Purpose

This is the builder loop: turn one planned work order into a change whose scope, checks and residual risks are stated precisely enough that an independent auditor can verify them without asking the builder. A work order is the bounded task packet the controller admits (`{id, task_id, role_id, envelope}`); its envelope names the objective, input references, write scope, output paths, prohibited actions, budget, acceptance criteria and return instruction. A receipt is the controller's record that a command ran with a given exit status; a check without a receipt is a claim. The builder's output is `implemented_not_verified` until `aipt-method-independent-audit` has reviewed it.

## Use when

- The controller has admitted a work order with `write_scope: assigned-worktree`, an `output_paths` list, acceptance criteria and a recorded target snapshot.
- The order's acceptance checks are stated as commands or observable conditions that can run within the order's budget.
- A prior attempt was rejected and the review names the specific gaps; the new attempt is a new task against the same order.
- A failed audit requires a corrective change inside an already authorized write set.
- The Engineering Manager, Prototype Engineer, Integration Engineer, Refactoring Engineer or Operations Engineer holds an order to execute.

## Do not use when

- No work order exists or its acceptance criteria are missing. Use `aipt-method-milestone-planning` to produce one instead of inferring scope from a conversation.
- The task is to verify someone else's delivered change. Use `aipt-method-independent-audit`; the author cannot audit its own artifact.
- The task is to run a measurement campaign across many cases. Use `aipt-method-evaluation-execution-and-receipts`.
- The change alters tool permissions, idempotency rules or the boundary between proposed and executed actions. Use `aipt-method-tool-and-permission-boundaries` first and treat the result as a proposal.
- The change is a release, deployment or external action. Use `aipt-method-rollout-and-operations` to plan it; execution outside the local boundary is a human action request.
- The change restructures code while preserving behavior across a wide surface. Use `aipt-method-drift-and-regression-audit` to define the invariants before implementing.

## Required inputs

- Authorized work order: `work-order` id with its task envelope, including `acceptance_criteria`, `output_paths`, `prohibited_actions`, `budget` and `capabilities`. Missing: return `needs_input`; nothing is implemented without an order.
- Target snapshot: `artifact` version (git commit plus dirty-diff hash, or manifest) recorded at admission. Missing or different from the working tree: return `blocked` with the two snapshot values.
- Requirements implemented: `requirement` version ids the order claims to implement, with their `protected` flags. Missing: proceed only if the order itself states acceptance criteria, and record the gap in `uncertainties`.
- Check commands: the automated checks from the order's acceptance criteria, each with its expected result. Missing for a criterion: implement, then return `partial` naming the criterion that has no runnable check.
- Prior attempt record, when any: the rejected `review` version and its findings. Missing on a retry: ask for it; a retry without the review repeats the same gap.
- Current status brief from `aipt-method-status-handoff`, when present. Missing: proceed from the order alone.

## Method

1. Read the work order envelope: objective, deliverable, acceptance criteria, write set, prohibited actions, budget and the capabilities actually available. Read the status brief if attached. Note anything in the envelope that conflicts with the snapshot or with another order's write set.
2. Confirm the exact order and criteria. Restate each acceptance check by id with its command or observable condition and expected result. If a criterion is absent or ambiguous, return `needs_input` with the criterion id instead of inventing an interpretation.
3. Confirm the target snapshot. Compare the recorded commit and dirty-diff hash with the working tree. If they differ, return `blocked` with both values and stop; a diff against the wrong base is not the authorized change.
4. Inspect the files in the write set and their immediate callers or dependents before editing. Record the list of files read. A file outside the write set is read-only; if the change cannot be made without editing it, stop and record a `scope_violation` naming the path and the reason.
5. Implement the smallest safe diff that satisfies the criteria. Prefer a change that one reviewer can read in one sitting. Leave unrelated improvements out and list them in `requested_followups`.
6. Run the targeted checks first: the commands named in the acceptance criteria, each through the receipt mechanism so it has a `receipt_id`. Then run broader checks only if the order's budget and capabilities allow; record which broader checks were not run and why.
7. Fix failures inside the write set before touching anything else. A failure whose fix lies outside the write set is a `blocked` result with the receipt attached, not a reason to widen the diff.
8. Report: exact files changed with content hashes, exact checks run with receipt ids and exit status, checks not run, residual risks and what remains. Set `status` by the rule in the output contract and submit the envelope; the status brief is re-derived from state, so the report is the record.

## Output contract

One `artifact` record per changed file or unit, with `kind`, `path`, `content_hash`, `producer_role`, `producer_task`, `write_scope: assigned-worktree`, `implements_refs` (requirement version ids), `status: implemented_not_verified` and `access_classification`.

Artifact `implementation-report.md` with headings: Work order; Files read; Files changed; Checks run; Checks not run; Unresolved risks; Out of scope found.

Envelope fields this method always fills:

- `findings`: what the diff does, stated as observations with file references; which criteria it addresses.
- `evidence_refs`: the order, requirement, snapshot and review versions read.
- `artifact_refs`: every changed file's artifact version.
- `observed_checks`: one item per command, `{command, claimed_exit_status, receipt_id}`; an item without `receipt_id` is a claim and is marked as such in `findings`.
- `uncertainties`: residual risks, untested paths, assumptions about callers outside the write set.
- `requested_followups`: the independent audit, deferred unrelated fixes, broader checks not run, any ask-first item.
- `scope_violations`: every path outside the write set that the change needed, with the reason.
- `proposed_links`: each artifact `implements` its requirement versions.

Status rule: `complete` when the diff is inside the write set and every targeted check has a receipt with the expected exit status; `partial` when some targeted checks lack receipts or were not run; `blocked` when the snapshot differs, a fix needs an out-of-scope edit or a required capability is unavailable; `needs_input` when a criterion is missing or ambiguous. `complete` means the order's contract is met, not that the change is verified.

## Evidence and uncertainty rules

- Only a receipt proves a check ran. A command the builder names without a receipt is recorded as `claimed_only` and cannot support `complete`.
- A passing check proves the command's exit status on this snapshot. It does not prove requirement coverage; say which criterion each check exercises and which paths it leaves untested.
- Label as `observation` anything read from the code with a file reference; label as `hypothesis` any belief about callers, environments or data the builder did not inspect.
- Record sources, claims and versions through `aipt-method-evidence-and-lineage`; the receipt shape and the replay-versus-live label come from `aipt-method-evaluation-execution-and-receipts`.
- If the snapshot changes after the checks ran, their applicability is `unestablished`. Re-run them or report the gap instead of carrying the old result forward.

## Guardrails

### Always

- Keep the diff inside the order's write set and scoped to its criteria.
- Fix in-scope failures before moving to any other work.
- Submit the envelope after each meaningful checkpoint so the derived status brief stays current.
- Read a file immediately before editing it, not from memory of an earlier read.

### Ask first

Return `needs_input` or a `requested_followup` to the Engineering Manager or `human-owner` before:

- Adding a new dependency or package.
- Running a schema or data migration.
- Deleting files, data or branches (destructive cleanup).
- Any change that expands scope beyond the order's write set or criteria.

### Never

- Do not skip verification because a change looks small. Instead, run the targeted checks under receipts for every diff, including one-line changes.
- Do not claim completion without evidence. Instead, return `partial` and list the checks that lack receipts.
- Do not fold unrelated refactors into the order. Instead, list them in `requested_followups` for a separate order.
- Do not edit outside the write set to make a check pass. Instead, return `blocked` with a `scope_violation` naming the path.
- Do not describe a check as run when the host could not execute it. Instead, record it as not run with the runnable instruction preserved.

## Success criteria

- Every changed file is inside the write set and listed with a content hash.
- Every targeted acceptance check appears in `observed_checks` with a receipt id, or is listed as not run with a reason.
- The report names residual risks and untested paths rather than asserting completeness.
- No unrelated change is in the diff; deferred items appear in `requested_followups`.
- The status follows the status rule, and an independent audit is requested.
- An auditor can reproduce the checks from the report alone.

## Example

Order `wo-01@v1` for Reply Assist (Larkspur Support): add a workspace filter so a ws-alpha query returns no ws-beta documents. Write set `src/reply_assist/retrieval/` and `tests/retrieval/`; snapshot `3b1e9c0`.

```json
{
  "task_id": "task-wo-01-a1",
  "role_id": "integration-engineer",
  "status": "complete",
  "summary": "Added workspace_id to RetrievalQuery and a store-side filter; both targeted checks ran under receipts.",
  "input_versions": ["wo-01@v1", "req-07@v2", "snapshot:3b1e9c0"],
  "findings": [
    "build_query() now carries workspace_id and the store filter rejects any document whose workspace differs (query.py lines 38-61, observation).",
    "Broader suite not run: order budget covered targeted checks only."
  ],
  "evidence_refs": ["wo-01@v1", "req-07@v2"],
  "artifact_refs": [
    {"path": "src/reply_assist/retrieval/query.py", "content_hash": "sha256:9d1f...", "implements_refs": ["req-07@v2"], "status": "implemented_not_verified"},
    {"path": "tests/retrieval/test_workspace_isolation.py", "content_hash": "sha256:51c0...", "implements_refs": ["req-07@v2"], "status": "implemented_not_verified"}
  ],
  "observed_checks": [
    {"command": "pytest tests/retrieval/test_workspace_isolation.py -k positive", "claimed_exit_status": 0, "receipt_id": "rcpt-0412"},
    {"command": "pytest tests/retrieval/test_workspace_isolation.py -k cross_workspace", "claimed_exit_status": 0, "receipt_id": "rcpt-0413"}
  ],
  "proposed_links": [{"from": "art-2f9c@v3", "relation": "implements", "to": "req-07@v2"}],
  "uncertainties": ["rerank.py reads the store by id outside this write set; it may bypass the filter (hypothesis, not inspected)."],
  "requested_followups": ["Independent audit of wo-01.", "Plan an order covering the rerank read path."],
  "scope_violations": []
}
```

The implementation report lists the same two files under Files changed, four files under Files read, and the rerank path under Out of scope found.
