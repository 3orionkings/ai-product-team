# W08 · Reduce cost or waiting without losing required quality.

A team asks what an AI feature costs per completed job, where its users wait, and what could be changed to reduce either without dropping below the quality and safety the feature must keep. This workflow answers with a cost model, a latency model, a set of candidate changes and an experiment plan that fixes the floor each change must preserve. It returns hypotheses with a next measurement; it implements nothing.

Entry skill `aipt-optimize-cost-latency` · Manager `operations-manager` · Minimum risk R0 · Core cross-host release test: no

## Purpose and outcome

Turn measured usage and traces into a reproducible account of what one completed job costs and where its time goes, then propose bounded changes whose benefit is stated as a hypothesis with the measurement that would confirm it. The outcome is an `optimization-review.md` that states potential benefit, uncertainty and the next measurement, and hands any implementation to a separately authorized W04 task. The quality and safety floor is fixed before any option is scored and does not move to make an option look better.

In the synthetic case, Reply Assist at Larkspur Support drafts replies across ws-alpha and ws-beta. A completed job is one accepted draft, not one model call; a draft that an agent discards after three retries cost three calls and produced nothing. The floor includes drafts-only behavior and zero cross-workspace exposure; no saving is admissible if it weakens either.

## Inputs

The user supplies measured usage and traces (per-call records with timestamps, token counts where observed, retry markers and span parent and child relations), rates (dated rate records, from `policies/` or supplied with a date; a missing rate is allowed and stays unknown), the outcome floor (the quality and safety constraints the feature must keep, each as a metric, slice and threshold), and workload slices (by workspace, by request type or by cohort).

The case must already contain accepted requirements or an acceptance map that names the protected behavior, a source scope that authorizes reading the traces, and the run budget. An accepted architecture helps the workflow-architect propose changes that fit, but its absence does not block the cost and latency stages.

When something is missing, the stage that needs it returns `needs_input` with the exact question and retains progress. Missing floor: "Which outcome floor applies: the accepted acceptance-map thresholds for this feature, or a different set? Name the metric and threshold for each protected slice." Missing end-to-end timing: "Supply start and end timestamps per completed job, or confirm that only per-stage percentiles exist; without end-to-end samples the latency model will report the end-to-end distribution as unmeasured." Missing usage data: "Which usage window and source should the cost model use? If usage is unavailable, confirm that cost per job is to be reported as unknown." Rates are never requested as a blocking input; an unknown rate produces an unknown component, not a stop.

## Outputs

`cost-model.json` (artifact node, status `proposed`): `usage_window`, `data_sources[]`, `per_completed_job` with `calls`, `retries`, `retrieval_calls`, `tool_calls`, `tokens_in`, `tokens_out`, `review_minutes`, `rate_records[]` each with `rate_id`, `dated`, `source_ref`, `cost_per_completed_job` with `value` or `unknown`, `currency`, `components[]`, `unknown_components[]`, `sensitivity[]`, `assumptions[]`, `by_slice[]`.

`latency-model.json` (artifact node): `critical_path[]`, `span_classes` with `serial`, `parallel`, `queued`, `user_review`, `end_to_end` with `available`, `p50`, `p95`, `sample_count`, `per_stage[]` with the same fields, `measurement_gaps[]`, `by_slice[]`.

`optimization-options.md` (artifact node): headings `## Options` (each with mechanism, expected effect, affected slices, risks and the measurement that would confirm it), `## Rejected options`, `## Dependencies on the accepted architecture`, `## Required measurements`.

`optimization-test-plan.json` (artifact node): `floor_constraints[]` each with `metric`, `slice`, `threshold`, `source_ref`, `baseline_version`, `held_out_ref`, `per_option_tests[]`, `stop_conditions[]`, `frozen_before_results: true`.

`optimization-review.md` (review record): headings `## Verdict`, `## Potential benefit (hypothesis)`, `## Uncertainty`, `## Next measurement`, `## Floor preserved`, `## Implementation handoff`.

## Work graph

| stage id | role | depends on | conditional predicate | artifact | review / independence | write scope |
|---|---|---|---|---|---|---|
| cost-job | cost-analyst | — | — | cost-model.json | reviewed at `review` | proposal-only |
| map-delay | latency-analyst | — | — | latency-model.json | reviewed at `review` | proposal-only |
| candidate-changes | workflow-architect | cost-job, map-delay | missing_current_artifact | optimization-options.md | reviewed at `review` | proposal-only |
| preserve-floor | evaluation-designer | candidate-changes | missing_current_artifact | optimization-test-plan.json | reviewed at `review` | proposal-only |
| review | operations-manager | cost-job, map-delay, candidate-changes, preserve-floor | — | optimization-review.md | review gate; author exclusion applies | proposal-only |

`cost-job` and `map-delay` read the same traces and do not depend on each other; dispatch them in parallel within the concurrency limit. `preserve-floor` follows `candidate-changes` so that each option has a named test; the floor itself comes from the accepted acceptance map and is not derived from the options.

## Stage procedures

### cost-job

The cost-analyst (`agents/cost-analyst.md`) applies `aipt-method-cost-and-latency-analysis` to count every call behind one completed job, including retries, retrieval and tool charges and stated review time, and `aipt-method-outcome-and-value-analysis` to divide by completed jobs rather than by calls. Input refs: the usage records, dated rate records, the workload slices, the definition of a completed job from the accepted requirements. Accept when `cost-model.json` reproduces from its listed sources, every rate is dated, every missing price appears in `unknown_components` rather than as zero, and the sensitivity section names the assumption that moves the total most.

### map-delay

The latency-analyst (`agents/latency-analyst.md`) applies `aipt-method-evaluation-execution-and-receipts` to read span timings from the traces and `aipt-method-cost-and-latency-analysis` to build the critical path and classify each span as serial, parallel, queued or user review. Input refs: the traces, the dependency graph between stages, the workload slices. Accept when `latency-model.json` reports the end-to-end distribution only from end-to-end samples with a count, lists every gap in `measurement_gaps`, and contains no figure formed by adding percentiles of parallel spans.

### candidate-changes

The workflow-architect (`agents/workflow-architect.md`) applies `aipt-method-ai-responsibility-allocation` to find steps where fixed code or a narrower route can replace model inference, `aipt-method-tool-and-permission-boundaries` to keep each permission check deterministic and in place, and `aipt-method-milestone-planning` to express each option as a bounded change a later W04 order could implement. Input refs: accepted `cost-model.json` and `latency-model.json`, the accepted architecture where present. Accept when each option in `optimization-options.md` names its mechanism, the slice it affects, its risk to the floor and the measurement that would confirm its benefit, and when any model alternative is referred to W07 rather than scored here.

### preserve-floor

The evaluation-designer (`agents/evaluation-designer.md`) applies `aipt-method-evaluation-planning` to freeze the floor constraints, baseline and held-out cases before any option is measured, and `aipt-method-requirements-and-acceptance` to trace each constraint to the acceptance map. Input refs: accepted `optimization-options.md`, the acceptance map version, the dataset manifest where present. Accept when `optimization-test-plan.json` carries a test per option, a floor constraint per protected slice with its source, and `frozen_before_results: true`.

### review

The operations-manager (`agents/operations-manager.md`) applies `aipt-method-cost-and-latency-analysis` to check that totals and distributions follow from the data, `aipt-method-outcome-and-value-analysis` to check that benefit is stated per completed job and under uncertainty, and `aipt-method-rollout-and-operations` to name who would own each change and how it would be measured. Input refs: all four accepted artifacts. Accept when `optimization-review.md` states every saving as a hypothesis, records what remains unmeasured, names the next measurement and routes implementation to a separate W04 task.

## Gates

The run completes only when `cost-job`, `map-delay` and `review` have accepted tasks or satisfying versions, the conditional stages have either an accepted task or a false predicate recorded, the `review` stage has a review record with result `ready` or `pass`, no `partial` output remains and no `needs_input` is open. `review` is the review gate; the controller refuses to admit it to a role that produced an artifact under review. No stage here requires independence, so `conflict_check` is recorded but not mandatory. Review and independence gates are never pruned, whatever artifacts already exist.

Acceptance lines from the registry: no fabricated prices or token totals; quality constraints remain fixed; savings are hypotheses until measured.

## Routing and pruning

A stage is satisfied without a model call when the case holds an accepted artifact of its type bound to the same usage window and trace version: a current `cost-model.json` satisfies `cost-job`, a current `latency-model.json` satisfies `map-delay`. `candidate-changes` and `preserve-floor` carry `missing_current_artifact`; an accepted `optimization-options.md` or `optimization-test-plan.json` whose inputs are still current makes the predicate false and the stage is not planned. A changed acceptance map invalidates a test plan's applicability and the predicate becomes true again.

Conditional specialists join under these conditions: the retrieval-designer when `requires_retrieval` holds and retrieval dominates cost or the critical path; the outcome-analyst when the value of a completed job is itself in question or reporting changes confound the usage data; the alternative-advocate when `consequential_or_disputed` holds, for example when an option proposes a model alternative or a recorded dissent exists; the evaluation-designer appears both as the `preserve-floor` role and as a specialist when the floor must be re-derived after a changed acceptance map.

A narrow request such as "what does one drafted reply cost us?" routes to cost-analyst and operations-manager only; no architect or test plan is planned.

Budget guidance: `focused` (4 tasks) fits the two measurement stages plus review, or one measurement stage plus review for a single-dimension question; `standard` (12 tasks) is the default for all five stages with a specialist and a retry; `deep` (24 tasks) is for a disputed floor or an optimization that triggers W07 and W11. A full run uses 5 tasks; a cost-only question uses 2.

## Status handling and recovery

`needs_input`: the task stores the exact question, the run moves to `needs_input`, accepted artifacts stay in place, and the user receives the question with what is already measured.

`blocked`: when traces or usage are unavailable or unauthorized, the stage reports the missing evidence, the other measurement stage continues if its data exists, and the user receives the list of unavailable inputs and the authorization or export needed.

`failed`: a reproduction command that fails keeps its receipts, the controller investigates within the work order's retry budget, and the user receives the failure with receipts.

`partial`: a cost model with unknown components or a latency model without end-to-end samples is a complete artifact with disclosed unknowns, not `partial`; `partial` applies when a stage could not finish its listed slices, and then the run cannot reach `completed`.

Budget exhaustion: the run returns the accepted models, the options not yet tested and a specific request to expand scope, without switching mode or skipping review.

In every case the user receives a packet stating what is measured, what is unknown and the single next measurement.

## Authority boundary

This workflow never changes routing, caching, batching, context assembly or model configuration in a running feature, never edits a target repository, and never deploys, publishes, sends, pays or deletes. Implementation of any option is a separate W04 task with its own write authorization and independent audit. A change to the outcome floor is a change to a protected requirement: it requires W11 and human acceptance, and no option may be scored against a lowered floor in the meantime. A favorable operations-manager review records that the analysis is coherent; it creates no authority to implement.

## Fixture

Registry scenario: trace spans run in parallel and only per-stage percentile numbers are supplied. Expected behavior: the latency-analyst does not add per-stage p95 values and call the result the end-to-end p95; `latency-model.json` reports `end_to_end.available: false`, lists the missing end-to-end samples in `measurement_gaps`, and the review names that measurement as the next step before any latency improvement is claimed.

Fixture path: `evals/workflows/optimize-cost-latency/fixture.json`. A replay of this fixture is labeled `fixture_replay` and is not a live run.

## Invocation

Entry skill: `aipt-optimize-cost-latency`.

- `aipt run start --case CASE --workflow optimize-cost-latency --mode standard` records a run bound to the case, this workflow version and the `standard` budget.
- `aipt run plan --run RUN_ID` records the route plan with the predicate results for the two conditional stages and any pruned stage's satisfying version.
- `aipt task next --run RUN_ID` lists the ready tasks, which at the start are `cost-job` and `map-delay` together.
- `aipt task admit --task TASK_ID` records the admission checks and reserves a worker slot.
- `aipt task attach --task TASK_ID --native-child-id CHILD_ID` records which native child executes the task so the execution mode is observed.
- `aipt receipt run --task TASK_ID -- <trace query command>` records a receipt for any command used to reproduce a figure.
- `aipt task submit --task TASK_ID --response response.json` records the response envelope and stores its artifacts as proposed versions.
- `aipt review submit --run RUN_ID --record review.json` records the operations-manager review against the exact versions reviewed.
- `aipt decision propose --run RUN_ID --record decision.json` records a proposal to change the floor or to authorize a W04 task, with the authority it requests.
- `aipt decision record-user-input --run RUN_ID --record user-input.json` records the user's answer to a `needs_input` question with `attested: false`.
- `aipt case report --case CASE --format markdown` renders the case state, including the models, options and their unknowns.

## Live coverage

| host | fixture_replay | native | last run |
|---|---|---|---|
| `adapters/<host>` (one row per host directory) | not yet run | not yet run | — |

This table is updated only from recorded runs.
