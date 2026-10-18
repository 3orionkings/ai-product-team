---
name: aipt-method-cost-and-latency-analysis
description: Cost per completed task, latency distribution, p95, critical path, retries, dated rates, unknown rates, tokens versus outcomes. Use when a role must state what a feature costs per task that actually completed, or how long users wait end to end, from observed usage, timed traces and dated rate sources. Counts retries, retrieval, tool charges and review time; keeps unknown rates unknown instead of zero; reports latency as a measured end-to-end distribution; never sums parallel stage percentiles; separates critical-path, queued and user-review delay.
license: MIT
metadata:
  aipt_skill_id: "S20"
  aipt_provenance: "newly_authored"
  aipt_version: "0.1.0"
---

# Cost and latency analysis

## Purpose

Produce two reproducible models for one artifact version: what a task that actually completed costs, and how long a user waits from request to usable result. Build both from observed usage, timed traces and dated rate sources that the case already holds as `source` versions, so that another analyst can rebuild every number from the same references.

Terms used here. A *completed task* is a task whose result met the acceptance check named in a `requirement` or `validation` version; a request that returned output but failed acceptance is an *attempt*. A *dated rate* is a unit charge recorded as a `source` version with the date it was observed and the components it applies to. The *critical path* is the longest chain of dependent stages in one trace; stages that run in parallel contribute only through the longest member of their branch.

## Use when

- A cost or waiting-time figure is requested for an artifact version and observed usage, billing exports or timed traces exist as `source` versions (W07 "Measure economics", W08 "Cost the completed job" and "Map delay").
- A proposal claims a saving or a speedup, and the claim must be restated as a measurable hypothesis with the measurement that would confirm it.
- A rollout plan or an operational review needs an operating-cost estimate and a waiting-time distribution for a named cohort.
- Someone supplies token totals, per-stage percentiles or a single average and asks what the feature costs or how long it takes.
- An outcome comparison needs the cost side of a value judgment; this skill supplies the cost per completed task that `aipt-method-outcome-and-value-analysis` consumes as one criterion.

## Do not use when

- No observed usage or traces exist and the question is what a feature would cost. Return `needs_input` naming the measurement and plan it with `aipt-method-evaluation-planning`; if the owner still wants a figure, deliver a sensitivity sheet labeled hypothesis throughout.
- The question is whether the feature improves the user's outcome. Use `aipt-method-outcome-and-value-analysis`; this skill measures what the work costs, not whether it was worth doing.
- The traces still have to be produced by running an evaluation. Use `aipt-method-evaluation-execution-and-receipts` to run and record; return here once the receipts exist.
- The task is to design the optimization (narrower routing, caching, batching, context reduction). That belongs to the architect roles; this skill measures the current state and specifies the measurement that would confirm the change.
- The retries need a cause. Take the classification from the failure analysis `review`; here retries are counted and attributed to the task, not explained.

## Required inputs

Each input is a versioned reference recorded in `input_versions`.

| Input | Record kind | If missing |
|---|---|---|
| Observed usage per component (calls, retries, retrieval queries, tool invocations, review minutes) over a stated window | `source` | Return `needs_input`; an estimate may stand in only when labeled hypothesis in every figure that uses it |
| Task outcome marks: which attempts met the acceptance check | `validation`, or `artifact` with acceptance status | Report cost per attempt only and state that cost per completed task cannot be computed |
| Dated rates per component, with observation date and scope | `source` | Keep the component with its usage and `cost_status: unknown` |
| Timed traces with span start and end, parent and child, queue enter and exit, and human review timestamps | `source` | Restrict the latency model to the spans measured and list the missing ones |
| Workload slices that matter (cohort, workspace, task type) | `requirement` or `proposal` | Report the whole window as one slice and say so |
| Quality floor that any optimization must keep | `requirement` versions from `aipt-method-evaluation-planning` | Mark every optimization candidate unconstrained and request the floor |
| Concurrency and admission limits in force during the window | `source` or run record | Report queued delay as unexplained wait rather than attributing it to capacity |

## Method

1. Fix the unit. Point `completed_task` at the exact acceptance check (`validation` or `requirement` version). Count completed, attempted and abandoned tasks in the window and write all three denominators before computing any rate.
2. Inventory components. List every charged or time-consuming component per task: generation calls including retries and fallbacks, retrieval queries, tool or API calls, storage or egress where charged, human review time, rework after rejection. Give each component a usage metric, the `source` version that reports it and the `source` version that prices it, or `unknown`.
3. Measure usage per completed task. Attribute retries and fallbacks to the task that triggered them, so a task completed on the second call carries two calls. Report usage per attempt and per completed task, and the retry multiplier (calls per completed task).
4. Attach dated rates. For each component record the rate value, its `source` version, the date observed and the scope it covers. A rate without a date is a hypothesis; a component without a rate stays in the model with `cost_status: unknown` and a note of the document that would supply it. Zero is a measured value, never a placeholder.
5. Compute cost per completed task as the sum of known component costs divided by the completed count. Report beside it: cost per attempt, the share of spend consumed by abandoned attempts, the list of unknown components, and the statement that the known-component total is a lower bound while any component is unknown.
6. Run sensitivity on the two or three largest drivers: retry rate, completion rate, retrieved passages per task, review minutes, rate changes. Report the resulting range as a hypothesis conditioned on the stated assumptions, not as a forecast.
7. Build the latency distribution from end-to-end durations: one value per task from the user's triggering action to the result being usable. Report count, median, p95, p99 where the sample supports it, and maximum, for the whole window and for each slice. Compute every percentile from the per-task end-to-end values, never from stage percentiles.
   - Tasks abandoned before a result have no completion time. Report them as their own series (count and time to abandonment) rather than dropping them, because a distribution built only from completed tasks understates waiting when abandonment rises with delay.
   - Compare distributions only on the same slices and windows; a before/after comparison across different workload mixes is a hypothesis until the mix is held constant.
8. Decompose a sample of traces. For each sampled trace mark the critical path, the parallel branches (whose longest member sets the branch time), queued delay (time between ready and admitted) and user-review delay (time waiting for a human). Report each class as its own measured distribution, and keep user-review delay out of the system figure unless the owner defines the outcome to include it.
9. For each candidate optimization, name the component or path segment it changes, state the expected change as a hypothesis with the exact measurement that would confirm it on the same slices, and attach the quality floor it must keep. A saving is a hypothesis until measured.
10. Write `cost-model.json` and `latency-model.json`, fill the envelope, and propose `depends_on` links from each model to the usage, rate and trace `source` versions it used, with `impact_policy: invalidate_applicability`, so that a new rate or trace export marks the model stale.

## Output contract

Artifacts:

- `cost-model.json`: `target` (artifact version, window, slices); `unit` (acceptance reference, completed, attempted, abandoned); `components[]` (name, usage_per_completed, usage_per_attempt, rate_ref, rate_observed_on, cost_status); `cost_per_completed_task` (known_components_total, lower_bound, unknown_components); `cost_per_attempt`; `share_from_abandoned_attempts`; `sensitivity[]` (driver, range, resulting range); `claim_types` per figure.
- `latency-model.json`: `end_to_end` (definition, n, p50, p95, p99 or the reason it is withheld, max) for the window and per slice; `abandoned` (count, time to abandonment distribution); `decomposition` (sample n, critical_path, parallel_branches, queued, user_review, each as a distribution); `rejected_computations` (any stage sum offered by the inputs and why it is not the system figure); `optimization_candidates[]` (segment, hypothesis, confirming measurement, quality floor reference).

Envelope fields this skill always fills: `findings` (one entry per material cost or delay fact, each with its claim type); `evidence_refs` (usage, rate, trace and acceptance versions); `artifact_refs` (the two models); `uncertainties` (unknown rates, missing spans, thin slices, window representativeness); `requested_followups` (the measurement that would close each unknown); `proposed_links` (`depends_on` edges to the sources used); `observed_checks` only when a computation was actually run and its receipt is referenced; `scope_violations` when the request asked for a rate or a usage figure the sources do not contain.

## Evidence and uncertainty rules

- Type every figure as observation (computed from referenced sources), hypothesis (sensitivity, projection, expected saving) or unknown. Record provenance and claim types as `aipt-method-evidence-and-lineage` specifies; this skill does not restate those rules.
- A token count is usage, not an outcome. The denominator for cost is completed tasks against the referenced acceptance check; token totals appear only as a component's usage.
- Report a percentile only when the sample holds at least 1/(1-p) observations (20 for p95, 100 for p99). Otherwise report the maximum and the count, and name the sample size that would allow the percentile.
- An undated rate, a rate for a different scope, or a rate inferred from a total is a hypothesis and is marked so in `claim_types`.
- A window represents only the slices it contains; name the absent slices rather than extrapolating to them.
- Extrapolation to a longer period carries the explicit assumption of constant workload and rates, and is a hypothesis.
- The known-component total is a lower bound while any component is `unknown`; say so wherever the figure appears, including in `findings`.
- A figure computed by the analyst from referenced sources is an observation of those sources, not of the live system; the receipt for the computation, when one exists, is referenced in `observed_checks`, and the absence of a receipt is stated.

## Guardrails

- Do not report zero or omit a component when usage or billing is unavailable. Instead keep the component in the model with its usage, mark `cost_status: unknown` and name the export or invoice that would supply the rate.
- Do not add stage medians or stage p95s and call the sum a system figure. Instead compute percentiles from per-task end-to-end durations; when only stage percentiles exist, report that the end-to-end measurement is missing and request it.
- Do not treat token totals, call counts or drafts generated as throughput or outcomes. Instead report completed tasks against the referenced acceptance check.
- Do not copy a rate value into a skill or role body. Instead reference the dated `source` version; rate values live in dated policy files, and the model cites them.
- Do not blame retries on the model without the failure classification. Instead count them here and cite the failure analysis `review` for the cause.
- Do not present an expected saving as realized. Instead state it as a hypothesis with the measurement, slices and quality floor that would confirm it.
- Do not include narrative about why a number feels right. Instead include the formula, the inputs and their versions.
- Do not drop abandoned tasks from the latency picture. Instead report their count and time to abandonment as a separate series beside the completed-task distribution.

## Success criteria

- Every number in both models traces to a `source` version and a stated formula; an independent analyst reproduces the figures from the same references.
- Completed, attempted and abandoned counts are stated, and cost per completed task is distinguished from cost per attempt.
- Every component appears once with `known` or `unknown`; there is no silent omission and no zero placeholder.
- Latency percentiles come from end-to-end values with sample counts; any stage sum offered by the inputs is listed under `rejected_computations`.
- Critical path, parallel branches, queued delay and user-review delay are reported as separate distributions.
- Sensitivity ranges and optimization candidates are labeled hypothesis, each with its confirming measurement and quality floor.
- `uncertainties` lists every unknown rate, missing span and thin slice.

## Example

Reply Assist at Larkspur Support drafts support replies that a human agent reviews and sends. Observation window: four weeks across workspaces `ws-alpha` and `ws-beta`.

```json
{
  "artifact": "cost-model.json",
  "target": {"artifact": "reply-assist-draft@v3", "window": "2026-09-01/2026-09-28", "slices": ["ws-alpha", "ws-beta"]},
  "unit": {"completed_task": "draft accepted by agent per validation:accept-check@v2", "completed": 1180, "attempted": 1420, "abandoned": 240},
  "components": [
    {"name": "draft_generation", "usage_per_completed": {"calls": 1.31}, "usage_per_attempt": {"calls": 1.09}, "rate_ref": "source:rates-2026-09-30@v1", "rate_observed_on": "2026-09-30", "cost_status": "known"},
    {"name": "retrieval", "usage_per_completed": {"queries": 2.0}, "rate_ref": "source:rates-2026-09-30@v1", "rate_observed_on": "2026-09-30", "cost_status": "known"},
    {"name": "tone_check_tool", "usage_per_completed": {"calls": 1.0}, "rate_ref": null, "cost_status": "unknown", "would_resolve": "vendor invoice export for September"},
    {"name": "agent_review", "usage_per_completed": {"minutes": 2.4}, "rate_ref": "source:staffing-rate-2026-07@v1", "rate_observed_on": "2026-07-01", "cost_status": "known"}
  ],
  "cost_per_completed_task": {"known_components_total": 0.84, "unit": "as stated in source:rates-2026-09-30@v1", "lower_bound": true, "unknown_components": ["tone_check_tool"]},
  "cost_per_attempt": 0.70,
  "share_from_abandoned_attempts": 0.17,
  "sensitivity": [{"driver": "retry_rate", "range": [0.10, 0.40], "cost_per_completed_task": [0.76, 0.93]}],
  "claim_types": {"known_components_total": "observation", "sensitivity": "hypothesis"}
}
```

```json
{
  "artifact": "latency-model.json",
  "end_to_end": {"definition": "ticket opened to draft visible to agent", "n": 1180, "p50_s": 6.2, "p95_s": 19.8, "p99_s": 31.5, "max_s": 44.1},
  "slices": {"ws-beta": {"n": 84, "p50_s": 7.0, "p95_s": 22.3, "p99_s": "withheld: n < 100", "max_s": 44.1}},
  "decomposition": {"sample_n": 60, "critical_path_p50_s": 5.1, "parallel_branches": ["retrieval", "policy_lookup"], "queued_p50_s": 0.6, "user_review_p50_s": 95.0, "user_review_in_end_to_end": false},
  "rejected_computations": [{"offered": "sum of stage p95s = 27.4 s", "reason": "stages run in parallel; the measured system p95 is 19.8 s"}]
}
```
