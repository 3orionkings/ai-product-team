# W07 · Would another model improve this feature?

A team running an AI feature on one model configuration asks whether a different candidate would serve the same task better, and under what quality, waiting and cost limits. This workflow answers with a like-for-like comparison on frozen cases, a stated uncertainty, and a recommendation to retain, migrate, narrow deployment or obtain more evidence. It never switches the feature over; it produces a proposal that a human or W11 acts on.

Entry skill `aipt-compare-models` · Manager `systems-manager` · Minimum risk R1 · Core cross-host release test: no

## Purpose and outcome

Decide between a current configuration (the baseline) and one or more candidates using the same cases, the same criteria and disclosed settings, so that the recommendation rests on task results rather than on reputation or a per-token rate. The outcome is a `model-decision-proposal.md` whose recommendation is one of `retain`, `migrate`, `narrow_deployment` or `obtain_more_evidence`, bound to the exact candidate, plan, dataset and results versions it used. Where the run cannot execute a candidate, the outcome says so and names the missing capability instead of substituting replay numbers.

In the synthetic case, Larkspur Support runs Reply Assist, which drafts replies for agents and never sends them. The protected slice is cross-workspace questions: a draft prepared for ws-alpha must not draw on ws-beta documents. A candidate that scores higher on average but fails that slice is not an improvement.

## Inputs

The user supplies three things. First, the current and candidate configurations as configuration records: a `candidate_id`, a configuration reference the runner can execute, and dated availability evidence; the current configuration is always included as `baseline`. Second, the frozen cases: a `dataset-manifest.json` version with development and held-out separation and named slices, including the protected slice. Third, the limits: a quality floor per slice, a waiting limit stated as an end-to-end distribution target, and a cost ceiling or an explicit statement that cost is to be reported rather than bounded.

The case must already contain accepted requirements or an acceptance map that names the protected behavior, a source scope that authorizes the cases, a capability report saying whether the host can execute candidate evaluations, and the run budget.

When something is missing, the stage that needs it returns `needs_input` with the exact question and retains all progress. Missing quality floor: "Which pass threshold on the cross-workspace slice must every candidate meet? Give the metric and value, or confirm the accepted acceptance-map value for this feature." Missing frozen cases: "Which dataset-manifest version are the candidates compared on? If none exists, authorize the dataset-curator to build one from the listed sources." Missing candidate configuration: "Supply an executable configuration reference and dated availability evidence for each candidate; a product name alone is not enough." Missing execution capability is not `needs_input`; it is `blocked` (see Status handling).

## Outputs

`candidates.json` (artifact node, status `proposed`): `baseline_id`, `candidates[]` with `candidate_id`, `configuration_ref`, `availability_evidence_ref`, `evidence_dated`, `task_suitability_notes`, `excluded[]` with reasons.

`comparison-plan.json` (artifact node): `dataset_version`, `slices[]`, `metrics[]`, `thresholds[]` per slice, `baseline_id`, `settings_common`, `settings_differing[]` with `candidate_id`, `setting`, `value`, `reason`, and `frozen_before_results: true`.

`candidate-results.json` (artifact node plus one validation record per candidate with receipts): `comparison_plan_version`, `dataset_version`, `candidates[]` with `requested_configuration`, `actual_configuration_observed`, `execution_mode`, `per_case[]` (`case_id`, `slice`, `score`, `retries`, `latency_ms`, `output_ref`), `slice_summary[]`, `receipt_ids[]`, `unavailable_observations[]`.

`cost-comparison.json` (artifact node): `workload_window`, `usage_source`, `rate_records[]` each with `rate_id`, `dated`, `source_ref`, `per_completed_task[]` by candidate with `value` or `unknown`, `components`, `unknown_charges[]`, `sensitivity[]`.

`latency-comparison.json` (artifact node): `end_to_end[]` by candidate with `p50`, `p95`, `sample_count`, `slices[]` with the same fields, `measurement_gaps[]`.

`model-decision-proposal.md` (review record from the manager; also a proposal record when a decision is requested): headings `## Recommendation`, `## Evidence used`, `## Constraint results by slice`, `## Economics`, `## Waiting`, `## Uncertainty`, `## Alternatives and dissent`, `## Requested authority`.

## Work graph

| stage id | role | depends on | conditional predicate | artifact | review / independence | write scope |
|---|---|---|---|---|---|---|
| select-candidates | model-selection-analyst | — | — | candidates.json | reviewed at `review` | proposal-only |
| freeze-comparison | evaluation-designer | select-candidates | — | comparison-plan.json | reviewed at `review` | proposal-only |
| run | evaluation-runner | freeze-comparison | — | candidate-results.json | receipts required | verification-sandbox |
| economics | cost-analyst | run | — | cost-comparison.json | reviewed at `review` | proposal-only |
| waiting | latency-analyst | run | — | latency-comparison.json | reviewed at `review` | proposal-only |
| review | systems-manager | economics, waiting | — | model-decision-proposal.md | review gate; author exclusion applies | proposal-only |

`economics` and `waiting` read the same accepted results and do not depend on each other; dispatch them in parallel within the concurrency limit. Every other edge follows stage order.

## Stage procedures

### select-candidates

The model-selection-analyst (`aipt-model-selection-analyst`) applies `aipt-method-research-consolidation` to gather dated capability and availability evidence for each candidate, `aipt-method-evaluation-planning` to check that each candidate can be run on the frozen cases, and `aipt-method-cost-and-latency-analysis` to note which billing facts are known and dated. Input refs: the user's configuration records, the accepted requirements, the capability report. Accept when `candidates.json` lists the baseline, gives each candidate a dated evidence reference, and records every exclusion with a reason that is about the task rather than the brand.

### freeze-comparison

The evaluation-designer (`aipt-evaluation-designer`) applies `aipt-method-evaluation-planning` and `aipt-method-requirements-and-acceptance` to fix metrics, slices, thresholds and baseline before any candidate result exists, and to list each setting that differs between candidates with the reason. Input refs: accepted `candidates.json`, the dataset manifest version, the acceptance map. Accept when `comparison-plan.json` names one dataset version for all candidates, carries `frozen_before_results: true`, and leaves no differing setting undisclosed.

### run

The evaluation-runner (`aipt-evaluation-runner`) applies `aipt-method-evaluation-execution-and-receipts` to execute each candidate on the frozen cases inside the verification sandbox as recorded commands with receipts in the case ledger, and `aipt-method-cost-and-latency-analysis` to record token and timing observations per call. Input refs: accepted `comparison-plan.json`, the dataset version, the candidate configurations, the approved budget. Accept when every candidate has a receipt-bound validation record, `actual_configuration_observed` is filled or marked unobservable, and no replay or fixture output appears in a live score.

### economics

The cost-analyst (`aipt-cost-analyst`) applies `aipt-method-cost-and-latency-analysis` to compute cost per completed task from observed workload, including retries and retrieval calls, and `aipt-method-outcome-and-value-analysis` to separate tokens consumed from tasks completed. Input refs: accepted `candidate-results.json`, dated rate records from `policies/`. Accept when every rate used carries a date and source, every unknown charge is listed as unknown rather than zero, and the sensitivity section states which assumption moves the ranking.

### waiting

The latency-analyst (`aipt-latency-analyst`) applies `aipt-method-evaluation-execution-and-receipts` to read the timing receipts and `aipt-method-cost-and-latency-analysis` to compare end-to-end distributions and slices. Input refs: accepted `candidate-results.json`. Accept when each distribution carries a sample count, the protected slice is reported separately, and no figure is a sum of component percentiles.

### review

The systems-manager (`aipt-systems-manager`) applies `aipt-method-structural-integrity-audit` to check that the recommendation follows from the slice results and stated limits, `aipt-method-ai-responsibility-allocation` to check that a migration would not move a deterministic control into model judgment, and `aipt-method-tool-and-permission-boundaries` to confirm the candidate respects the same permission boundaries. Input refs: all five accepted artifacts. Accept when `model-decision-proposal.md` states one recommendation, records uncertainty, and names the authority a migration would require.

## Gates

The run completes only when every non-conditional stage has an accepted task or a `satisfied_by_version_id`, the `review` stage has a review record with result `ready` or `pass`, no `partial` output remains and no `needs_input` is open. `review` is the review gate for this workflow; the controller refuses to admit it to the role that produced any artifact under review. No stage here requires independence, so `conflict_check` is recorded but not mandatory. Review and independence gates are never pruned, whatever artifacts already exist.

Acceptance lines from the registry: same cases and disclosed settings; rates are dated or cost is unknown; no recommendation based solely on model reputation.

## Routing and pruning

A stage is satisfied without a model call when the case holds an accepted artifact of its type whose versions still apply: an accepted `candidates.json` listing the same baseline and candidates; a `comparison-plan.json` bound to the same dataset version; a `candidate-results.json` bound to that plan and those configurations; a `cost-comparison.json` or `latency-comparison.json` bound to that results version. Reusing results avoids a paid rerun and is recorded as `satisfied_by_version_id`; the report must then not claim fresh execution.

Conditional specialists join under these conditions: the dataset-curator when `missing_current_artifact` holds for the dataset manifest or the manifest lacks held-out separation; the evidence-judge when `material_conflict` holds between two results records or between a candidate's claimed and observed configuration; the alternative-advocate when `consequential_or_disputed` holds, which is the case for any migration recommendation at R2 or any recorded dissent.

A narrow request such as "compare these two evaluation reports we already have" routes to model-selection-analyst, cost-analyst and systems-manager only, reuses the supplied results, and does not rerun evaluations.

Budget guidance: `focused` (4 tasks) fits only a pruned route, typically three tasks when results exist; `standard` (12 tasks) is the default and carries the six stages with room for one retry and one specialist; `deep` (24 tasks) is for a disputed migration where W11 challenge rounds are expected. A full run uses 6 tasks; with two specialists, 8.

## Status handling and recovery

`needs_input`: the task stores the exact question, the run moves to `needs_input`, completed artifacts stay accepted, and the user receives the question with what is already known.

`blocked`: when the host cannot execute a candidate, `run` reports the missing capability, `economics` and `waiting` for that candidate stay unadmitted, and any independent work on other candidates continues; the user receives the blocked candidate list and the capability needed.

`failed`: a failed execution keeps its receipts, the controller investigates within the retry budget of the work order, and the user receives the failure with receipts rather than a guess.

`partial`: completed artifacts remain, the run cannot reach `completed`, and the report lists which candidates lack results.

Budget exhaustion: the run returns the accepted artifacts, the stages not reached and a specific request to expand scope; it never switches to `deep` on its own or drops the review to fit.

In every case the user receives a packet stating what is established, what is unknown and the single next resolving action.

## Authority boundary

This workflow never changes the model configuration of the feature, never edits a target repository, never purchases capacity, and never deploys, publishes, sends, pays or deletes. A `migrate` or `narrow_deployment` recommendation that changes release criteria, a sensitive data flow or protected behavior is an R2 proposal: it goes to W11 for challenge when disputed and to human acceptance before anything changes. A favorable systems-manager review records that the proposal is coherent; it creates no authority to act.

## Fixture

Registry scenario: candidate B looks cheaper per input token but retries more and fails the protected slice. Expected behavior: the recommendation uses task-level results and the stated constraints, not a superficial rate comparison, so candidate B is not recommended for the cross-workspace slice and the per-completed-task cost reflects its retries. Any billing component without a dated rate stays `unknown`.

Fixture: `evals/workflows/compare-models/fixture.json` records this scenario, its expected behavior and the acceptance lines. It has not been run against a model or a host.

## Invocation

Entry skill: `aipt-compare-models`. It runs in your current session, never a forked one, and that session acts as the root orchestrator.

- Claude Code: `/aipt-compare-models` followed by your request and the files or folders to use.
- Codex: `$aipt-compare-models` followed by the same.
- Either host: describe the request in plain language; the `aipt-start` entry skill routes it here when it fits.

Example request: "Would a different model configuration improve Reply Assist? Compare it with the current one on the frozen cases."

Before dispatching any role, the session states the route plan: the stages it will run, the stages it will skip and why, the artifacts it will write, any missing input, and anything it will not do. Artifacts and the case ledger go under `aipt-cases/<case-id>/` in your project, as the `aipt-start` skill describes.

This release has no command-line controller. The record-keeping rules in this recipe (version binding, review independence, receipts, impact tracing) are followed by the orchestrating session as instructions; nothing enforces them in code. The experimental controller library in `src/` implements several of these rules in tested code, but it is not connected to either host.

## Live coverage

Per-host status is recorded in `docs/compatibility/`. As of this release, no workflow has been run end to end on either host, and this recipe's fixture is unrun.
