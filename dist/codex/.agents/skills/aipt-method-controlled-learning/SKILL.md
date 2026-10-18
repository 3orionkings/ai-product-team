---
name: aipt-method-controlled-learning
description: Controlled learning, skill change proposal, workflow change proposal, repeated failure, verified outcomes, held-out tests, rollback version, protected policy, separate version, anecdote is not a rule. Use when audited results show the same failure recurring across independent cases and a change to a skill, role body or workflow recipe is proposed to address it. Produces a learning proposal on its own version with the failure statement, affected invariants, expected improvement, held-out tests and rollback; blocks any change to protected authority, exclusions, privacy boundaries or thresholds.
license: See LICENSE_PENDING.md in the repository root.
metadata:
  aipt_skill_id: "S27"
  aipt_provenance: "newly_authored"
  aipt_version: "0.1.0"
---

# Controlled learning

Turn a repeated, verified failure into a proposed change to a skill, role body or workflow recipe, written on its own version, judged on held-out cases, with a rollback recorded first and protected policy left untouched.

## Purpose

A learning proposal is a `proposal` record that says: this failure recurred; here is where the current text or recipe causes it; here is a candidate replacement on a separate version; here is what should improve and by how much; here are the cases that will test it, none of which were used to find it; and here is the version to return to if it does not improve. The author of the proposal does not promote it. Independent review and the appropriate human approval do.

Three terms carry the skill. A **protected policy** is any record whose change is reserved to a human: who may approve or delegate (authority), which sources are excluded, where privacy boundaries sit, what the package may claim at release, and the thresholds an evaluation must meet. The list lives in a policy version the case names; this skill reads it and leaves it unchanged. **Repeated** means the same failure class observed in independent cases, each with a receipt, in a count that meets a threshold set in policy by reference; one case, however vivid, is an anecdote that yields an observation claim and no rule. **Held-out** means cases that played no part in forming the pattern or the candidate.

Three public techniques are used in plain words. Changing on a branch: the candidate is a new version with its own hash, linked to the current version but not replacing it, so the current version keeps running until promotion. Held-out evaluation: the cases that judge the change are kept apart from the cases that motivated it, because a change tuned to its own examples passes them trivially. Rollback by version: the prior version id is recorded before the change is tried, so returning is a lookup rather than a reconstruction.

## Use when

- Audited `validation` or `review` records show the same failure class in more than one independent case against one version of a skill, role body or workflow recipe.
- A skill's success criteria are repeatedly unmet for the same reason, and the cause sits in the skill's text rather than in the host or in enforcement.
- A `challenge` or `review` recommends a process change and asks for it to be made testable.
- A workflow step repeatedly returns `partial`, `blocked` or `needs_input` for a reason the recipe could remove.
- A promoted learning change needs its rollback exercised or its held-out result compared with its prediction.

## Do not use when

- The evidence is one case: record it with `aipt-method-evidence-and-lineage` (S12) as an `observation` claim and wait for the threshold.
- The change would alter protected policy: write a `requested_followups` entry to `human-owner`; a `decision` under `aipt-method-delegated-authority` (S25) is the only path.
- The change is to the product rather than to the process: use `aipt-method-milestone-planning` (S08).
- The failure is a code defect: use `aipt-method-scoped-implementation` (S09) under a work order.
- You need the evaluation protocol frozen, the held-out set built or the run executed: use `aipt-method-evaluation-planning` (S17), `aipt-method-evaluation-data-curation` (S18) and `aipt-method-evaluation-execution-and-receipts` (S19); this skill names what they will do.
- You need to tell whether two versions differ in the intended way: use `aipt-method-drift-and-regression-audit` (S07).
- The text was clear and the output disregarded it: that is an enforcement question for `aipt-method-tool-and-permission-boundaries` (S16) or `aipt-method-security-and-privacy-review` (S26), not a text change.

## Required inputs

- **Outcome records** — `validation` versions with receipts and `review` versions, each naming the skill, role or recipe version in force. If a record lacks a receipt, exclude its case from the count; if the count then falls below threshold, return `complete` with `result: insufficient_evidence`.
- **Current version** — the `artifact` version (content hash) of the skill, role body or recipe. If missing, return `needs_input`; a change cannot be proposed against "the current file".
- **Failure claims** — `claim` versions typed `observation`, one per case, naming what went wrong. If missing, write them first with S12 and cite them.
- **Protected policy list** — the policy version naming protected `requirement` ids. If missing, treat every rule about authority, exclusions, privacy, release claims and thresholds as protected and return `partial` with the list requested.
- **Threshold reference** — the minimum independent case count, in policy by reference. If missing, no count is sufficient; return `insufficient_evidence` and request the threshold.
- **Evaluation protocol and held-out set** — S17 and S18 `artifact` versions. If missing, write the candidate, set `held_out_tests.status: pending`, and return `partial`.
- **Delegation for promotion** — the `approval` version naming who may promote. If missing, write `promotion.requires: ["human-owner"]`.

## Method

1. **Count independent cases.** Group outcome records by failure class and by the version in force. A case counts when it has its own receipt, its own case id and its own inputs; a rerun of another case's inputs is the same case. Compare the count to the threshold reference. Below it, stop: write the observation claims, set `result: insufficient_evidence`, and return.
2. **State the failure as a claim that could be false.** Name the version, the cases, what the output lacked or did wrongly, and the consequence a reviewer observed. "Outputs were weak" is not a statement; "no refusal check for a forbidden action in 4 of 4 requirement sets" is.
3. **Locate the cause in the text or recipe.** Cite the step, section or line. Classify it: `text_absent` (nothing covers the case), `text_unclear` (covers it but was read two ways), `text_contradicted` (another step or a role body pulls the other way) or `text_ignored` (the text was clear and the output disregarded it). For `text_ignored`, write no candidate; set `result: routed_to_enforcement` and name S16 or S26 in `requested_followups`.
4. **Check the protected list before writing any change.** List every record the change would touch. If any is protected, set `protected_touch.result: true`, write no candidate, record the proposal as a request to `human-owner`, and return `blocked`. The test is whether the record is on the list, not whether the change seems beneficial.
5. **Enumerate affected invariants.** Which success criteria, guardrails, negative tests, fixtures and role bodies reference the text being changed. Propose a `depends_on` link from each to the candidate with `impact_policy: review`.
6. **Write the candidate on a separate version.** New version id and content hash; the change as an exact diff against the base; a `supersedes` link with `edge_status: proposed`. The base version is left as it is.
7. **State the expected improvement against the frozen protocol.** Metric, slice, baseline taken from the outcome records, direction, threshold by reference (S17), and a list of what must not change. A later edit to this statement is a new proposal version, not a correction.
8. **Name the held-out tests.** The S18 set version; the cases excluded because they formed the pattern; those same cases listed as `regression_only`, since passing them shows little. The run belongs to S19; this skill names what it will run and against which hash.
9. **Record rollback before trial.** The exact base version id, the trigger (any held-out regression, any guardrail violation, any protected touch discovered later) and who may invoke it.
10. **Submit and stop.** Emit `learning-proposal.json` with `promotion.status: proposed`. Promotion requires independent review under `aipt-method-independent-audit` (S10) and approval under S25. The author is not the reviewer.

## Output contract

Artifact: `learning-proposal.json`, kind `proposal`, with keys:

- `proposal_id`, `failure_statement`, `evidence_refs[]`
- `case_count`: `independent`, `threshold_ref`, `meets_threshold`
- `cause_location`: `version`, `where`, `kind` (`text_absent` | `text_unclear` | `text_contradicted` | `text_ignored`), `detail`
- `protected_touch`: `checked_against`, `touches[]`, `result`
- `affected_invariants[]`
- `candidate`: `base_version`, `candidate_version`, `hash`, `change`, `link` (`relation: supersedes`, `edge_status: proposed`)
- `expected_improvement`: `metric`, `slice`, `baseline`, `direction`, `threshold_ref`, `must_not_change[]`
- `held_out_tests`: `set_version`, `cases_excluded[]`, `regression_only[]`, `status` (`pending` | `named` | `receipted`)
- `rollback`: `to_version`, `trigger`, `may_invoke`
- `promotion`: `requires[]`, `status`
- `result`: `proposed` | `insufficient_evidence` | `protected_blocked` | `routed_to_enforcement`

Envelope fields this skill always fills:

- `findings`: the pattern and its count; the cause classification; any protected touch; any routing to enforcement.
- `evidence_refs`: the outcome records, failure claims, current version, protected list and threshold reference read.
- `artifact_refs`: the proposal version and, when written, the candidate version.
- `proposed_links`: candidate `supersedes` base (`proposed`); each affected invariant `depends_on` the candidate, `impact_policy: review`; each held-out `validation`, once run, `verifies` the candidate.
- `uncertainties`: the cause location (a hypothesis until the held-out run supports it); a baseline drawn from few cases; `must_not_change` items that are not yet measured.
- `requested_followups`: the held-out run (S19), the independent review (S10), the approval (S25), and the threshold or protected list if either was missing.
- `scope_violations`: any request to edit the base version in place, to promote the candidate, to alter a protected record, or to count a rerun as an independent case.

## Evidence and uncertainty rules

- A case counts only with a receipt (S19) naming the version in force. A reviewer's recollection of a failure is a hypothesis and does not count.
- Reruns of the same inputs are one case, whatever their number.
- The cause location is a hypothesis until a held-out run on the candidate supports it; label it so in the proposal and the envelope.
- The baseline is computed from the observed records and labeled with their count; a count near the threshold earns a `low` confidence label.
- The candidate's hash is computed before any held-out run, and results are reported against that hash.
- A pass on the motivating cases alone is not evidence of improvement; only the held-out result is.
- Follow S12 for citing versions and typing claims; this skill adds only the rules above.

## Guardrails

- Do not turn one case into a rule. Instead, record an `observation` claim and wait for the threshold.
- Do not edit the current version in place. Instead, write the candidate as a new version with a `supersedes` link in state `proposed`.
- Do not change protected policy, including an evaluation threshold, because the change would raise the pass rate. Instead, set `protected_touch.result: true`, write no candidate, and escalate to `human-owner`.
- Do not test the candidate on the cases that motivated it and call the result improvement. Instead, list them as `regression_only` and judge on the held-out set.
- Do not write the expected improvement after seeing results. Instead, write it before the run and treat any later edit as a new proposal version.
- Do not propose a text change for text that was ignored. Instead, set `result: routed_to_enforcement` and name S16 or S26.
- Do not promote the candidate or ask any executor to adopt it. Instead, submit it and name the reviewer and the approver.
- Do not act as reviewer of your own proposal. Instead, require that the review record a different author.
- Do not propose a change without a rollback version. Instead, record the base version id and the trigger before the candidate is tried.

## Success criteria

- The failure statement names a version, a case count that meets the threshold reference, and an observable consequence.
- The cause has a cited location and one of the four kinds; `text_ignored` produced no candidate.
- The protected list was checked and the result recorded; no protected record is in the change set.
- The candidate has its own version id and hash, an exact diff and a `supersedes` link in state `proposed`.
- The expected improvement names a metric, slice, baseline, direction and threshold reference, plus what must not change.
- The held-out set excludes every motivating case, and those cases appear under `regression_only`.
- The rollback names the base version, the trigger and who may invoke it.

## Example

Reply Assist at Larkspur Support: across four cases the requirement sets never included a check that the model does not send. Proposal excerpt:

```json
{
  "proposal_id": "LP-012",
  "failure_statement": "On aipt-method-requirements-and-acceptance@v1 as applied by requirements-writer in cases c-104, c-117, c-131 and c-140, the requirement set for Reply Assist held no refusal check for 'the model never sends', so the independent audit found no test covering the send boundary.",
  "evidence_refs": ["val-2201", "val-2240", "val-2277", "val-2302", "rev-0890"],
  "case_count": {"independent": 4, "threshold_ref": "policies/learning-thresholds@current", "meets_threshold": true},
  "cause_location": {"version": "aipt-method-requirements-and-acceptance@v1", "where": "Method step 6", "kind": "text_absent",
                     "detail": "the step asks for negative checks on inputs but names no check for an action the system must never take"},
  "protected_touch": {"checked_against": "policies/protected@v2", "touches": [], "result": false},
  "affected_invariants": ["S13 success criterion: every requirement has at least one negative check", "requirements-writer review rubric item 3"],
  "candidate": {"base_version": "aipt-method-requirements-and-acceptance@v1", "candidate_version": "aipt-method-requirements-and-acceptance@v2-candidate",
                "hash": "sha256:5b1e...", "change": "Method step 6, append: for every action the requirement forbids, write a refusal check whose expected result is the action not occurring and a recorded denial",
                "link": {"relation": "supersedes", "edge_status": "proposed"}},
  "expected_improvement": {"metric": "share of requirement sets with a refusal check per forbidden action", "slice": "features with at least one forbidden action",
                           "baseline": "0 of 4 audited sets", "direction": "up", "threshold_ref": "eval-plan-requirements@v1",
                           "must_not_change": ["requirement count per feature", "time to first requirement draft (unmeasured)"]},
  "held_out_tests": {"set_version": "eval-set-requirements@v3", "cases_excluded": ["c-104", "c-117", "c-131", "c-140"],
                     "regression_only": ["c-104", "c-117", "c-131", "c-140"], "status": "named"},
  "rollback": {"to_version": "aipt-method-requirements-and-acceptance@v1", "trigger": "any held-out regression or guardrail violation", "may_invoke": "audit-manager"},
  "promotion": {"requires": ["independent review (S10)", "approval under delegation (S25)"], "status": "proposed"},
  "result": "proposed"
}
```

In the same run a second request asked to lower the pass threshold for the send-boundary check because three builds had failed it. The threshold is on the protected list, so that proposal records `protected_touch: {"touches": ["eval-plan-requirements@v1 threshold"], "result": true}`, writes no candidate, sets `result: protected_blocked`, and returns `blocked` with a followup addressed to `human-owner`.
