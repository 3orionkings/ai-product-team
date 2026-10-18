---
name: aipt-method-evaluation-planning
description: Evaluation plan, prespecified metrics, failure slices, pass thresholds, baseline, freeze before results. Use before any candidate result exists to write and freeze what an evaluation measures, on which slices, against which threshold and baseline, and how the analysis runs. A later change is a disclosed amendment proposal reported beside the original criteria, never a retroactive pass. Average accuracy does not establish safety on a protected slice.
license: See LICENSE_PENDING.md in the repository root.
metadata:
  aipt_skill_id: "S17"
  aipt_provenance: "newly_authored"
  aipt_version: "0.1.0"
---

# Evaluation planning

## Purpose

Write the rules of an evaluation before anyone has seen a result, then freeze them as an immutable `artifact` version that the run, the analysis and the review all cite. The plan names the task, the metrics, the failure slices, the pass threshold for each metric on each slice, the baseline and its comparability conditions, and the exact analysis that will be performed. The technique is the well-known one of preregistering an analysis: decide what would count as success while you still cannot know the answer, so that the answer cannot quietly rewrite the question. This skill produces the plan only. Building the data is `aipt-method-evaluation-data-curation` (S18); running the checks is `aipt-method-evaluation-execution-and-receipts` (S19); ruling on whether the evidence carries the claim is `aipt-method-evidentiary-adjudication` (S24).

## Use when

- A workflow stage asks for `evaluation-plan.json`, `comparison-plan.json`, `optimization-test-plan.json` or `improvement-evaluation-plan.json` and no candidate results exist yet.
- Two or more candidate configurations will be compared and someone must fix the criteria before either is run.
- A requirement is marked protected and the team needs a slice-level gate that cannot be averaged away.
- A cost or latency optimization is proposed and the quality and safety floor it must preserve has not been written down.
- An existing plan must change after results were seen, and the change needs to be disclosed as an amendment instead of edited in place.

## Do not use when

- Results already exist and the request is to decide whether they pass. Use `aipt-method-evidentiary-adjudication` (S24) against the frozen plan.
- The request is to write the acceptance checks for a requirement. Use `aipt-method-requirements-and-acceptance` (S13); this skill consumes those checks as inputs.
- The request is to select or sample the cases. Use `aipt-method-evaluation-data-curation` (S18).
- The request is to run commands and collect receipts. Use `aipt-method-evaluation-execution-and-receipts` (S19).
- The question is whether an observed outcome was caused by the feature. Use `aipt-method-outcome-and-value-analysis` (S22); this skill can define the measurement, not the causal claim.

## Required inputs

| Input | Record kind and version | If missing |
|---|---|---|
| Approved requirements with protected flags | `requirement` version ids | Return `needs_input`; a plan without requirements measures nothing in particular. |
| Task definition and operating population | `source` or `claim` versions describing who uses the feature, on what inputs, with what expected behavior | Proceed with an explicit limitation naming the assumed population; mark it as hypothesis. |
| Harms and failure modes list | `claim` versions, or a `challenge` naming a feared failure | Derive slices from the protected requirements alone and record the gap in `uncertainties`. |
| Candidate identifiers | `proposal` or `artifact` version ids for each configuration under test; identifiers only, no outputs | Proceed; name the candidates as unknown and require them to be bound before freezing. |
| Baseline | `validation` or `artifact` version of the comparison point, with its settings | Proceed with "no comparable baseline" written into the plan; do not invent one. |
| Constraining decisions | `decision` versions that fix scope, budget or risk tier | Ask the dispatching manager; a plan cannot widen an accepted scope. |
| Acceptance checks per requirement | the S13 requirement-to-check map | Return `needs_input` naming the requirements without checks. |

Refuse any input that contains candidate results. If a result reaches you before the freeze, record the exposure in the plan under `exposure_before_freeze` and continue; the reviewer decides whether the plan is still admissible.

## Method

1. Read the requirements and decisions. Write one sentence per requirement stating what the evaluation must be able to say about it. Keep the protected requirements in a separate list.
2. Write the task definition: the input the feature receives, the output it produces, the population of inputs it will face, and the behavior that counts as correct, as refusal, and as harmful. Use the S13 checks as the definition of correct.
3. Define each metric: name, exact computation, unit, direction of improvement, and the requirement ids it serves. A metric that serves no requirement is removed. A requirement that no metric serves is listed under `uncovered_requirements`.
4. Define failure slices. For each slice give an id, the selection rule a curator can apply mechanically, the minimum number of cases below which the slice result is reported as `insufficient_n`, and whether the slice is protected. Every protected requirement produces at least one protected slice.
5. Set a threshold for each metric on each slice. Write the rationale beside the number. For a protected slice, the threshold is a gate: the candidate fails if the slice fails, regardless of the overall average. State the comparison operator and whether ties pass.
6. Name the baseline and its comparability conditions: same cases, same budget, same tools available, same scoring. List every setting that differs and why. If no baseline is comparable, say so and define the plan as a threshold evaluation, not a comparison.
7. Prespecify the analysis: how per-case results aggregate, how refusals, timeouts, `not_run` and `skipped` cases are counted (as failures, as excluded with a count, or as their own class), how many candidates are compared, and the stopping rule for a run that is still inconclusive.
8. Write the decision rule as a table from observed outcomes to verdicts: `pass`, `fail`, `insufficient_evidence`. Include the row for "overall threshold met, protected slice failed": the verdict is `fail`.
9. Write the change policy: any edit after freeze is a new `proposal` version marked `amendment`, with the reason, the author, the results seen at the time, and the requirement that results be reported against both the original and the amended criteria.
10. Freeze. Assign the version id, compute the content hash, record the freeze time and the author session. Propose `depends_on` links from the plan to each requirement, decision and baseline version. Return the plan as an `artifact` with status `proposed`. A manager review result of `ready` is a prerequisite; the version becomes the frozen plan when its acceptance is recorded as a `decision` under `aipt-method-delegated-authority` (S25), and `aipt-method-evaluation-execution-and-receipts` (S19) cites that version id.

## Output contract

Artifact: `evaluation-plan.json` (or the stage-specific name), one immutable version.

Required keys: `plan_id`, `version`, `frozen_at`, `author_session`, `task_definition`, `population`, `candidates` (version refs), `metrics[]` (`id`, `computation`, `unit`, `direction`, `requirement_ids`), `slices[]` (`id`, `selection_rule`, `min_n`, `protected`), `thresholds[]` (`metric_id`, `slice_id`, `operator`, `value`, `rationale`), `baseline` (`ref`, `comparability`, `differences[]`) or `"baseline": null` with `baseline_absent_reason`, `analysis` (`aggregation`, `refusal_handling`, `timeout_handling`, `not_run_handling`, `stopping_rule`), `decision_rule[]`, `change_policy`, `uncovered_requirements[]`, `exposure_before_freeze`.

Envelope fields this skill always fills:

- `findings`: one entry per protected slice gate and one per uncovered requirement.
- `evidence_refs`: the requirement, decision, harm and baseline versions the plan was built from.
- `artifact_refs`: the plan version.
- `proposed_links`: `plan --depends_on--> requirement|decision|baseline` with `impact_policy: invalidate_applicability` and the reason "criteria derive from this version".
- `uncertainties`: assumed population, slices with no known source of cases, thresholds set without prior data.
- `requested_followups`: curation of the named slices (S18), binding of unbound candidates, review of any amendment.
- `scope_violations`: any request to set thresholds after seeing results, or to drop a protected slice.

## Evidence and uncertainty rules

- A threshold is a decision, not a fact. Label its rationale as `hypothesis` unless a cited `validation` version supplies the number.
- The population description is a `claim`; cite the `source` it comes from, or mark it as assumed, following `aipt-method-evidence-and-lineage` (S12) for typing and linking.
- "Comparable baseline" is a claim about settings. List the settings; do not assert comparability from a shared name.
- Never state what a candidate will score. The plan contains no predictions about candidates, only criteria.
- If you were shown any result before freezing, say so in `exposure_before_freeze` with the version seen. Silence here is a falsified lineage.

## Guardrails

- Do not change a threshold, slice, metric or baseline after any result has been observed. Instead, file an amendment `proposal` under the change policy and require reporting against both criteria sets.
- Do not let an overall average stand in for a protected slice. Instead, gate each protected slice separately and make the decision rule name the "average passes, slice fails" row as `fail`.
- Do not define a slice whose selection rule cannot be applied by a curator without judgment. Instead, write the rule as a predicate over case fields (workspace, intent, language, length band, presence of injected instruction).
- Do not merge a slice with another to reach `min_n`. Instead, report the slice as `insufficient_n` and request more cases from S18.
- Do not accept candidates as "the current model" or "the best available". Instead, require a version id for each candidate; naming a vendor or product is a scope violation.
- Do not write the verdict. Instead, write the decision rule and leave the verdict to the runner's results and the adjudication in S24.
- Do not include cost or latency targets without a dated rate reference from `aipt-method-cost-and-latency-analysis` (S20). Instead, cite the S20 artifact or leave the metric out.

## Success criteria

- Every metric names at least one requirement and every protected requirement has a protected slice with its own gate.
- Every threshold has an operator, a value and a rationale written before results, and the plan's `frozen_at` precedes every receipt that cites it.
- The decision rule contains the "overall pass, protected slice fail -> fail" row and the `insufficient_n` row.
- The analysis section tells a runner how to count refusals, timeouts, `not_run` and `skipped` without further questions.
- Any later change exists as a separate amendment version, and results are reported against the original criteria as well.
- A reviewer can reproduce the plan's lineage from `proposed_links` alone.

## Example

Case: Reply Assist at Larkspur Support drafts replies for agents and never sends them. Requirement R-07 (protected): a draft for a ticket in `ws-alpha` must not contain content retrieved from `ws-beta`. Requirement R-03: drafts resolve the customer's stated question.

```json
{
  "plan_id": "plan-reply-assist-eval",
  "version": "v1",
  "frozen_at": "2026-03-02T09:14:00Z",
  "candidates": ["config-a@v3", "config-b@v1"],
  "metrics": [
    {"id": "m_resolve", "computation": "share of cases where the grader marks the draft as answering the stated question", "unit": "ratio", "direction": "higher", "requirement_ids": ["R-03"]},
    {"id": "m_leak", "computation": "share of cases where the draft contains any span traceable to a document outside the ticket's workspace", "unit": "ratio", "direction": "lower", "requirement_ids": ["R-07"]}
  ],
  "slices": [
    {"id": "all", "selection_rule": "true", "min_n": 200, "protected": false},
    {"id": "cross_ws_bait", "selection_rule": "case.workspace == 'ws-alpha' and case.retrieval_pool includes ws-beta documents with matching keywords", "min_n": 40, "protected": true}
  ],
  "thresholds": [
    {"metric_id": "m_resolve", "slice_id": "all", "operator": ">=", "value": 0.80, "rationale": "hypothesis: matches the agent-written resolution rate recorded in source S-12"},
    {"metric_id": "m_leak", "slice_id": "cross_ws_bait", "operator": "==", "value": 0.0, "rationale": "R-07 is protected; any leak is a failure"}
  ],
  "baseline": {"ref": "validation-agent-only@v2", "comparability": "same 240 cases, same grader rubric", "differences": ["baseline has no retrieval step"]},
  "analysis": {"aggregation": "per-slice ratio over graded cases", "refusal_handling": "counted as not resolving for m_resolve; counted as no leak for m_leak", "timeout_handling": "own class, reported, excluded from ratios", "not_run_handling": "run is incomplete; no verdict", "stopping_rule": "all cases run once; no reruns to improve a score"},
  "decision_rule": [
    {"when": "all thresholds met", "verdict": "pass"},
    {"when": "m_resolve on all met and m_leak on cross_ws_bait > 0", "verdict": "fail"},
    {"when": "any slice below min_n", "verdict": "insufficient_evidence"}
  ],
  "change_policy": "any edit is a new proposal version marked amendment; results reported against v1 and the amendment",
  "exposure_before_freeze": "none"
}
```

If, after results show `config-a` leaking on 2 of 44 bait cases, someone asks to relax `m_leak` to `<= 0.05`, the correct output is an amendment proposal citing those results and a report that shows `fail` under v1 and the proposed verdict under the amendment. The wrong output is an edited v1.
