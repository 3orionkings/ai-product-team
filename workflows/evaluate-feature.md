# W05 · Evaluate this feature against its actual task.

This workflow answers the request "tell me how well this feature does its job, and where it fails". The user has task cases, expected behaviors, one or more candidate configurations and a budget. It returns an evaluation plan whose metrics, slices, thresholds and baseline were frozen before any candidate result existed, a versioned dataset with development and held-out splits, results per candidate broken down by failure slice with execution receipts, and a review that separates what is established from what is narrowly demonstrated and what still needs evidence.

Entry skill `aipt-evaluate-feature` · Manager `evaluation-manager` · Minimum risk R1 · Core cross-host release test yes

## Purpose and outcome

Use this workflow when a decision depends on measured behavior rather than a demonstration: whether Reply Assist draft quality at Larkspur Support meets the bar on refund questions as well as on the easy majority, whether a candidate configuration leaks ws-beta content into ws-alpha answers, or whether a change moved the failing slice at all. The outcome is a results record that a later decision can cite: candidate, configuration observed, dataset version, plan version, receipts, scores by slice with sample counts, and the unavailable observations named as unavailable.

Two things cannot happen inside this workflow. Criteria do not move after results are seen; a proposed new threshold is a disclosed decision proposal and the original criteria stay in the record. Held-out cases are not used for development, and development results are not reported as held-out results.

## Inputs

The user supplies:
- Task cases: authorized examples of the real task, or a pointer to an existing `dataset-manifest` version. Each case carries an access classification; a private record never enters a public fixture.
- Expected behaviors: the outcome definition per case or per slice, drawn from approved requirements or the acceptance map where they exist.
- Candidate configurations: an identifier and configuration ref for each candidate and for the baseline. The baseline is preserved even when the user prefers a candidate.
- Budget: the mode, plus any limit on evaluation runs the runner must honor.

The case must already contain the source scope that authorizes the data, the protected constraints (for Reply Assist: drafts only, never send; workspace isolation between ws-alpha and ws-beta) and, where they exist, approved requirements and an acceptance map from `shape-feature`.

When something is missing, the run returns `needs_input` and retains progress:
- No task cases and no dataset in scope: "Which cases may be used, and under what access scope? Supply files or a dataset version, and state whether any case is private."
- No expected behavior for a slice: "What counts as a correct answer for cases in slice `cross-workspace`? Give the pass condition before any candidate runs."
- No baseline named: "Which configuration is the baseline? The comparison is frozen against it before execution."
- More candidate runs than the mode allows: "The plan needs N runner tasks; mode `standard` allows M. Expand the mode or drop a candidate."
- A candidate configuration is unavailable on the host: the runner task returns `blocked`, the configuration is listed under `unavailable_observations`, and the plan stays intact.

## Outputs

| Artifact | Shape | Stored as |
|---|---|---|
| `evaluation-plan.json` | `{plan_version, task_definition, candidates: [{id, configuration_ref}], baseline_id, metrics: [{id, definition, direction}], failure_slices: [{id, definition, minimum_cases}], thresholds: [{metric_id, slice_id, pass_if}], frozen_before_results: true, change_log: []}` | `artifact` node, kind `evaluation-plan`, status `proposed`; a later change is a new version, never an edit |
| `dataset-manifest.json` | `{dataset_version, plan_version, source_scope, splits: {development: [], held_out: []}, cases: [{id, slice_ids, access_classification, synthetic}], sampling_limits, coverage_by_slice}` | `artifact` node, kind `dataset-manifest`, status `proposed`; `depends_on` edge to the plan version |
| `results.json` | `{plan_version, dataset_version, label: live/fixture_replay, runs: [{candidate_id, configuration_requested, configuration_observed, split, execution_mode, receipt_id, outputs_ref, scores: {metric_id: value}, by_slice: {slice_id: {metric_id: value, n}}, unavailable_observations: []}]}` | `artifact` node plus one `validation` record per run with `receipt_id`, `result` and `applicability` |
| `failure-analysis.md` | Headings: Error modes · Slice results against frozen thresholds · Discriminating explanations · Alternatives retained · Next tests. | `artifact` node, kind `failure-analysis`; each explanation proposed as a `claim` of type `hypothesis` |
| `evaluation-review.json` | `review` fields `reviewed_refs, reviewer_role, reviewer_session, findings, evidence_sufficiency, result, conflict_check, unresolved`, plus `established: [], narrowly_demonstrated: [], needs_more_evidence: [], threshold_changes_disclosed: []` | `review` node via `aipt review submit` |

The registry outputs map as follows: evaluation plan is `evaluation-plan.json`; versioned dataset is `dataset-manifest.json`; results by failure slice are `results.json` read with `failure-analysis.md`; review is `evaluation-review.json`.

## Work graph

| Stage id | Role | Depends on | Conditional predicate | Artifact | Review / independence | Write scope |
|---|---|---|---|---|---|---|
| `define-test` | `evaluation-designer` | — | — | `evaluation-plan.json` | — | proposal-only |
| `curate` | `dataset-curator` | `define-test` | — | `dataset-manifest.json` | — | proposal-only |
| `execute` | `evaluation-runner` | `curate` | — | `results.json` | — | verification-sandbox |
| `analyze-failures` | `failure-analyst` | `execute` | — | `failure-analysis.md` | — | proposal-only |
| `review` | `evaluation-manager` | `analyze-failures` | — | `evaluation-review.json` | review | proposal-only |

`curate` may begin collecting authorized cases while `define-test` runs, but its manifest is accepted only once it cites the frozen plan version and reports coverage per slice, so the dependency stands. `execute` expands to one task per candidate configuration and split; these tasks are independent and parallelize up to the mode's concurrency inside the verification sandbox. Everything else follows stage order.

## Stage procedures

### `define-test` — evaluation-designer
Read `agents/evaluation-designer.md`. Apply `aipt-method-evaluation-planning` to freeze metrics, slices, thresholds and the baseline before any candidate output exists, and `aipt-method-requirements-and-acceptance` to tie each threshold to an approved requirement or acceptance criterion. Input refs: the requirement versions, the acceptance map when present, the candidate list from the user. For Reply Assist the slices include at least `cross-workspace` and `refund-policy`, each with a minimum case count. Accepted when every threshold names a metric and a slice, `frozen_before_results` is true, the baseline is one of the candidates, and no result record exists yet for this plan version.

### `curate` — dataset-curator
Read `agents/dataset-curator.md`. Apply `aipt-method-evaluation-data-curation` to build representative, permissioned cases with development and held-out splits, and `aipt-method-evidence-and-lineage` to record each case's source, access classification and limitations. Input refs: the plan version, the source scope, the supplied cases. Held-out ids are never shared with anyone tuning a candidate. Sampling limits are stated plainly, for example "no ws-beta cases from before the drafts-only policy change". Accepted when every slice meets its minimum count or the shortfall is recorded in `coverage_by_slice`, the splits are disjoint, and no case classified private appears in a public or synthetic set.

### `execute` — evaluation-runner
Read `agents/evaluation-runner.md`. Apply `aipt-method-evaluation-execution-and-receipts` to run each candidate against the frozen dataset through `aipt receipt run`, recording command, configuration observed, dataset version and exit status, and `aipt-method-cost-and-latency-analysis` to record usage and timing where the host exposes them and to mark them unknown where it does not. Input refs: the plan version, the dataset version, the candidate configuration refs. A proposed command is not an executed one; a run that did not happen is recorded as `not_run`. Replay output is labeled `fixture_replay` and is never mixed into live scores. Accepted when every run has a receipt or a `not_run` entry, `configuration_observed` is filled or marked unobservable, and scores are reported per slice with sample counts.

### `analyze-failures` — failure-analyst
Read `agents/failure-analyst.md`. Apply `aipt-method-evaluation-planning` to read results against the frozen thresholds, `aipt-method-evaluation-execution-and-receipts` to trace each failure to its recorded output, and `aipt-method-corpus-grounded-onboarding` to separate observed error modes from inferred causes. Input refs: `results.json`, the plan version, the dataset version. Group failures by error mode, state the discriminating explanation for each group, and retain the alternatives. A high mean that hides a failing `cross-workspace` slice is reported as a failing slice; the mean does not rescue it. Accepted when every error mode cites case ids and receipts, every explanation is typed hypothesis unless tested, and the next test for each open explanation is named.

### `review` — evaluation-manager
Read `agents/evaluation-manager.md`. Apply `aipt-method-independent-audit` to check that each claim in the analysis traces to a receipt, `aipt-method-evaluation-planning` to detect any criterion changed after results, and `aipt-method-outcome-and-value-analysis` to judge whether the measured task is the product's real question. Input refs: all four upstream artifacts. The manager sorts findings into established, narrowly demonstrated and needs more evidence, lists missing coverage, and records any threshold change as disclosed. Accepted when `result` is set, every item in `established` cites a held-out result with a receipt, and `threshold_changes_disclosed` is empty or points at a recorded decision proposal.

## Gates

The run completes only when all of the following are true:
- Every stage has an accepted task or a `satisfied_by_version_id` for a current artifact of its type.
- `review` has a `review` node with `result` in `{ready, pass}`. This stage is a review gate; the Evaluation Manager authored none of the plan, manifest, results or analysis under review, which admission enforces.
- The plan version cited by the manifest, the results and the review is one and the same version, and its `frozen_before_results` flag is true.
- Every `validation` record derived from `results.json` with a result other than `not_run` carries a receipt, and `results.json` carries `label: live` for any score the review counts as established.
- No `partial` outputs remain and no `needs_input` is open.

Review gates are never pruned. When `evidence-judge` joins under `material_conflict`, its ruling is a second review gate with `independence_required`; if a fresh context cannot be made, the ruling records `independence_unverified` and the run blocks rather than completing.

Acceptance lines from the registry: Hold-out separation. Actual execution receipts. Criteria frozen before results.

## Routing and pruning

A stage is satisfied without a new task when a current accepted artifact of its type exists for the same inputs: `define-test` when an `evaluation-plan` is current for the same requirements and candidates; `curate` when a `dataset-manifest` is current for that plan version and source scope; `execute` when `validation` records for the same candidate, configuration, plan and dataset versions are current and labeled live; `analyze-failures` when a `failure-analysis` is current for those results. A changed test, dataset or configuration invalidates applicability even when the candidate itself did not change.

Conditional specialists join when a named condition holds:
- `test-engineer` when a candidate needs harness code or a check that does not yet exist; it returns the check as a proposed patch and runs it through receipts.
- `evidence-judge` under `material_conflict`, when two result records or two readings of the same slice disagree on whether a threshold was met.
- `cost-analyst` and `latency-analyst` when cost or waiting is part of the acceptance criteria and the runner recorded the observations they need; neither estimates from reputation or from a rate without a date.
- `changes_protected_scope` raises the tier to R2 when a candidate configuration touches a protected behavior such as sending or cross-workspace access; the adoption decision goes through `resolve-decision`.

A narrow request, such as "rerun the cross-workspace slice on the current candidate", yields `execute` for one candidate on one slice, then `analyze-failures` and `review`, reusing the current plan and manifest. A request to compare candidates by model rather than by task belongs to `compare-models` (W07), not here.

Budget guidance: focused (4 tasks) fits one candidate on a current plan and dataset: execute, analyze, review, with one slot spare for a retry; standard (12 tasks) covers plan, curation, two or three candidates, analysis and review, usually 6 to 8 tasks; deep (24 tasks) is for many candidates, a held-out rerun after a disclosed threshold decision, or an evidence-judge round. Every runner attempt and retry counts.

## Status handling and recovery

- `needs_input`: the exact question is preserved in the run record; the frozen plan and any accepted manifest stay accepted; the run returns to `planned` when `aipt decision record-user-input` supplies the answer.
- `blocked`: the runner records the configuration or tool that is unavailable, the other candidates keep running, and the runnable command is kept in `unavailable_observations`. The user receives the blocker, the results that did complete and the next resolving action.
- `failed`: the receipt of the failed run is preserved with exit status and logs; a timeout is distinguished from a failing exit; retries stay within the work order's budget; a failed run never appears as a score.
- `partial`: completed candidate runs and their analysis stay accepted; the run cannot complete while any planned candidate lacks a result; the review names the missing candidates.
- Budget exhaustion: dispatch stops; accepted results are summarized with their receipts; the user is asked for an explicit expansion or a smaller candidate set. The run never drops the review and never shrinks the held-out split to fit.
- Threshold change after results: recorded as a new plan version with `change_log` populated and a decision proposal, never as an edit to the frozen version. The review is judged against the original criteria.

In every case the user receives a packet: what is established, what was measured but narrowly, what is blocked or missing, and the single next action.

## Authority boundary

This workflow never deploys, publishes, sends a message, pays, deletes data or changes a production configuration. The runner writes only inside the verification sandbox; everything else is a proposal. An evaluation that meets its thresholds is a measured fact about one candidate at one dataset version. It is not a release decision, which belongs to `review-release` (W09), and it authorizes no change to how Reply Assist behaves. A proposal to adopt a new threshold or promote a candidate is R2 when it touches a release criterion or a protected behavior, and it goes through `resolve-decision` (W11) with human acceptance bound to the exact proposal version. A manager's favorable review creates no authority: the Evaluation Manager has `acceptance_authority: none`.

## Fixture

Scenario: A high average score hides failures on cross-workspace questions; the proposed threshold is changed after results. Expected behavior: the report preserves the failing `cross-workspace` slice and the original frozen criteria; the review lists the slice as failing or under `needs_more_evidence`, never under `established`; the new threshold appears as a disclosed decision proposal recorded with `aipt decision propose`, not as a retroactive pass.

Fixture path: `evals/workflows/evaluate-feature/fixture.json`. A replay of this fixture is labeled `fixture_replay` and is not a live run.

## Invocation

Entry skill: `aipt-evaluate-feature`, loaded in the root session only.

- `aipt run start --case CASE --workflow evaluate-feature --mode standard` records a run in state `created` then `scoped`, with the case, workflow version, mode, risk floor R1 and the host when observable.
- `aipt run plan --run RUN` records the route plan: selected and omitted roles with reasons, included stages, satisfied-by versions, evaluated predicates and the budget check, including the count of runner tasks against the mode.
- `aipt task next --run RUN` lists the ready tasks whose dependencies are accepted, in dependency order.
- `aipt task admit --task TASK` runs the admission checks (dependencies, budget, write scope, author-as-reviewer, source scope, wall clock) and mints the work order with a reserved slot.
- `aipt task attach --task TASK --native-child-id CHILD` records the native child identity and execution mode; without it, a native claim is downgraded to `sequential` with `observed_by=agent_reported`.
- `aipt task submit --task TASK --response response.json` validates the envelope, stores the plan, manifest, results and analysis as proposed nodes, flags runs without receipts as `claimed_only` and moves the task to `submitted`.
- `aipt receipt run --task TASK -- <command>` executes one evaluation run and stores the receipt with command, snapshot, dataset and configuration hashes, exit status and log locations.
- `aipt review submit --run RUN --record review.json` records the manager review, or an evidence-judge ruling, with its conflict check.
- `aipt decision propose --run RUN --record decision.json` records a threshold change or candidate adoption as a proposal; `aipt decision record-user-input --run RUN --record user-input.json` records the user's answer with `channel=cli` and `attested=false`.
- `aipt case report --case CASE --format markdown` renders the derived report, including validation coverage with applicability and the open decision proposals.

## Live coverage

| Host | fixture_replay | native | Last run |
|---|---|---|---|
| first native host (see `docs/compatibility/`) | not yet run | not yet run | — |
| second native host (see `docs/compatibility/`) | not yet run | not yet run | — |
| fixture runner, no host | not yet run | — | — |

This table is updated only from recorded runs; no cell is inferred from parsed files or from a run on another host.
