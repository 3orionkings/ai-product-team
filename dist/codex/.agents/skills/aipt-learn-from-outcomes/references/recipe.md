# W12 · Use verified outcomes to improve the product or team.

Audited runs and their outcomes are in the case, some approaches failed, and the user asks what the team should change in its methods, skills or workflows as a result. The workflow measures what the outcomes actually show, proposes a versioned method change with a rollback path for a repeated and supported failure, checks what else the change touches, compares old and new behavior on development and held-out cases when evaluation fixtures exist, and has the audit-manager review whether the candidate is supported and authorized. The audit-manager holds `acceptance_authority: none`; promotion itself is a decision-authority act within a delegation bound to the candidate version, or a human act where protected scope is touched. Protected policies never modify themselves.

Entry skill `aipt-learn-from-outcomes` · Manager `audit-manager` · Minimum risk R0 · Core cross-host release test no

## Purpose and outcome

Learning from outcomes is where a team most easily fools itself: a complaint count falls and the feature is credited; one bad example is fixed and the fix becomes a rule; a prompt is tuned on the example that motivated it and promoted without a held-out check. This workflow puts a measurement step before the proposal, a drift check after it and a held-out comparison before promotion, and keeps the previous version and its results available so the change can be reversed.

The user receives an improvement proposal that names the repeated failure it addresses and the evidence for it, a test and evaluation plan that says how the candidate was or will be compared against the current version, and a versioned change with its rollback path, carrying the audit-manager's review result and the promotion decision recorded as a decision: `accepted` by the decision-authority for a supported improvement within a delegation bound to the candidate version, `rejected` with the failing held-out cases, `deferred` with the evidence still needed, or `human_required` where the change touches a protected policy. The review says whether the candidate is supported; only the decision moves the current pointer. In the Reply Assist case, a drafting-instruction revision that fixes one tone complaint in ws-alpha is a candidate; it is promoted only if it also holds on the held-out cross-workspace negatives.

## Inputs

The user supplies the audited runs to learn from (run ids whose audits are accepted), the outcomes observed with their definitions and denominators, the approaches that were tried and failed, and the current versions of the skills, workflows or prompts the proposal would change.

The case must already contain accepted `review` nodes from independent audits over those runs, `validation` records with receipts for the outcomes cited, the current method versions as immutable nodes, and, where the method has evaluation fixtures, the dataset manifest with its development and held-out split. Without an accepted audit the workflow does not learn from the run: `needs_input` with "Run R has no accepted independent audit. Should W04 or W05 audit it first, or should it be excluded from this learning cycle?" Without an outcome definition it stops at `measure-outcome`: `needs_input` with "What outcome does this feature change, measured how, over which denominator and period?" Without a held-out split for a method that has fixtures, `test` returns `blocked` rather than comparing on development cases alone.

## Outputs

`outcome-review.md` — headings Outcome definition, Observed results, Denominators and reporting changes, Confounding explanations, Association versus effect, What is established, What needs a discriminating test. Stored as an `artifact` node with status `proposed`; each stated result links to a `validation` or `claim` version, and a claim typed `observation` does not become `fact` here.

`improvement-proposal.json` (registry output: improvement proposal) — the `proposal` schema: `title`, `options` (at least `adopt_candidate`, `retain_current`, `gather_more_evidence`), `recommended_option`, `assumptions`, `evidence_refs`, `constraints`, `unresolved_questions`, `target_refs` (the current method versions), `author_role`, `requested_authority`, plus `repeated_failure` (each `occurrence_ref`, `audit_ref`), `candidate_version_id`, `rollback_version_id` and `protected_scope_touched`. Stored as a `proposal` node; the candidate is a new method version on its own branch with a proposed `supersedes` edge to the current version.

`improvement-impact.json` — keys `candidate_version_id`, `affected_methods` (each `version`, `path`, `impact_policy`, `reason`), `retained_invariants`, `likely_regressions` (each `behavior`, `fixture_ref`), `missing_lineage`. Stored as an `artifact` node.

`improvement-evaluation-plan.json` (registry output: test and evaluation plan) — keys `metrics`, `failure_slices`, `thresholds`, `baseline_version_id`, `candidate_version_id`, `development_cases`, `held_out_cases`, `frozen_at`, `results` (each `case_ref`, `split`, `baseline_result`, `candidate_result`, `receipt_id`), `disclosed_changes`. Stored as an `artifact` node, with each executed comparison as a `validation` node carrying a `receipt_id`.

`promotion-review.json` (registry output: versioned change and rollback path) — the `review` schema: `reviewed_refs`, `reviewer_role`, `reviewer_session`, `findings`, `evidence_sufficiency`, `result` (`ready`, `revise`, `blocked` or `escalate`), `conflict_check`, `unresolved`, plus `candidate_version_id`, `rollback_version_id`, `candidate_supported` (`true` only when every held-out slice passed with receipts), `protected_scope_touched` and `previous_results_retained` (always `true`). Stored as a `review` node. It records that the candidate is supported or not; it promotes nothing.

`promotion-decision.json` — the `decision` schema: `proposal_version_id` (the improvement proposal), `outcome` (`accepted`, `rejected`, `deferred`, `human_required`), `selected_option`, `criteria`, `rationale`, `dissent`, `authority_basis` (`{kind: delegation|human_input, approval_version_id}`), `revisit_conditions`, `status`. Stored as a `decision` node, opened as a proposed decision after the review. The outcome is recorded by the decision-authority within a delegation bound to the exact candidate version (W11 `apply-authority`, or a bounded decision-authority task when nothing is disputed), or by attested human input where `protected_scope_touched` is true; the audit-manager never records it.

## Work graph

| stage id | role | depends on | conditional predicate | artifact | review / independence | write scope |
|---|---|---|---|---|---|---|
| measure-outcome | outcome-analyst | — | — | outcome-review.md | — | proposal-only |
| propose-learning | learning-steward | measure-outcome | — | improvement-proposal.json | — | proposal-only |
| scope-drift | change-impact-analyst | propose-learning | — | improvement-impact.json | — | proposal-only |
| test | evaluation-designer | scope-drift | improvement_needs_evaluation | improvement-evaluation-plan.json | — | proposal-only |
| review-promotion | audit-manager | scope-drift; test when present | — | promotion-review.json | review gate | proposal-only |

The stages are sequential: each reads the accepted output of the one before. Every stage is proposal-only. Promotion is not a stage of this workflow: after `review-promotion` the controller opens a `decision` record, and its outcome belongs to the decision-authority or to a human, never to the audit-manager. The candidate method version lives on a separate branch of the method's node; nothing in this workflow writes to the current version, and any execution of comparisons runs through W05 in a `verification-sandbox`.

## Stage procedures

### measure-outcome
The outcome-analyst (`aipt-outcome-analyst`) receives the outcome definitions, the audited results and the rollout context. It applies `aipt-method-outcome-and-value-analysis` to state the outcome as a falsifiable hypothesis and compare approaches on the same criteria, `aipt-method-evaluation-planning` to read each result within the metrics and slices that were frozen for it, and `aipt-method-cost-and-latency-analysis` where the outcome includes cost or waiting. It inspects denominators and reporting changes before crediting any effect and separates association from cause. Accepted when every stated result cites an audited record, confounders are listed with the test that would exclude each, and fewer complaints is not written as fewer harms.

### propose-learning
The learning-steward (`aipt-learning-steward`) receives the accepted outcome review, the repeated failures with their audit refs, and the current method versions. It applies `aipt-method-controlled-learning` to propose the change on a separate version with a rollback and held-out checks, `aipt-method-drift-and-regression-audit` to state the invariants the change must keep, `aipt-method-evidence-and-lineage` to link the proposal to each failure occurrence, and `aipt-method-evaluation-planning` to name how the candidate will be judged before it is. A failure is repeated when at least two audited occurrences support it; a single anecdote or a rejected hypothesis produces `retain_current` or `gather_more_evidence`, not a change. Accepted when the proposal names candidate and rollback versions, lists the occurrences, marks `protected_scope_touched`, and recommends one of its own options.

### scope-drift
The change-impact-analyst (`aipt-change-impact-analyst`) receives the candidate version and the case's accepted `depends_on` edges. It applies `aipt-method-drift-and-regression-audit` to compare candidate and current against declared invariants, `aipt-method-corpus-grounded-onboarding` to read the methods that reference the changed one, and `aipt-method-evidence-and-lineage` to traverse the declared dependents and report missing lineage separately. It lists the methods and workflows the change reaches, the invariants that must hold and the regressions the fixtures would catch. Accepted when every affected method carries a declared path or a stated semantic reason, and unrelated methods are not marked stale.

### test
The evaluation-designer (`aipt-evaluation-designer`) runs only when `improvement_needs_evaluation` is true: the changed behavior has fixtures or held-out cases. It receives the candidate and baseline versions, the dataset manifest and the likely regressions, and applies `aipt-method-evaluation-planning` to freeze metrics, slices and thresholds before any candidate result is seen, and `aipt-method-requirements-and-acceptance` to tie each slice to the requirement or invariant it protects. Execution of the comparison is a W05 task with receipts; results are recorded per case and per split, and a threshold changed after results is a disclosed proposal, not a pass. Accepted when `frozen_at` precedes every result, held-out cases are separate from development cases, and every result carries a `receipt_id` or is `not_run`.

### review-promotion
The audit-manager (`aipt-audit-manager`) receives the proposal, the impact report, the evaluation plan with results where it exists, and the author identities. It applies `aipt-method-structural-integrity-audit` to check that proposal, impact and results describe the same candidate version, `aipt-method-independent-audit` to require receipts rather than the steward's report of success, and `aipt-method-security-and-privacy-review` when the change touches access, data handling or an authority rule. It records whether the candidate is supported on held-out cases and whether protected scope is touched; it holds `acceptance_authority: none` and promotes nothing. A supported, unprotected R1 candidate gets `ready`, and the promotion then goes as a proposed decision to the decision-authority, who accepts only within a delegation bound to the candidate version; a protected change gets `escalate`, and the decision is opened `human_required` for W11 and attested human acceptance; a failing held-out slice gets `revise` with the cases named, and a proposed decision is `rejected`. Accepted when the reviewer authored none of the inputs, the result follows from the recorded results, `candidate_supported` is `true` only with receipts for every held-out slice, and `previous_results_retained` is `true`.

## Gates

The run completes only when `measure-outcome`, `propose-learning`, `scope-drift` and `review-promotion` each have an `accepted` task or a `satisfied_by_version_id`; `review-promotion` has a `review` node with result `ready` or `pass`; `test`, when its predicate is true, is accepted with receipts for its results; no output is `partial`; and no `needs_input` is open. `review-promotion` is the review gate, and the audit-manager may not have authored the proposal, the impact report or the evaluation plan. A `ready` review completes the run; it does not promote. Moving the current pointer additionally requires a `decision` node with outcome `accepted` whose `authority_basis` is a delegation bound to the exact candidate version and recorded by the decision-authority, or a human acceptance with attested provenance where protected scope is touched. No stage requires a fresh independent context by default, but a promotion that changes a method used by audits adds the independent-auditor as a conditional specialist with `independence_required`, and that gate then needs `conflict_check` `verified`. Review and independence gates are never pruned.

The registry acceptance lines are checked against the stored records: no automatic policy self-modification; no private traces in public fixtures; compare on held-out examples before promoting.

## Routing and pruning

A stage is satisfied without a model call when a current accepted artifact exists for the same inputs: an outcome review accepted in a W06 or W08 run over the same audited runs satisfies `measure-outcome`; an evaluation plan frozen in W05 for the same candidate and baseline versions satisfies `test`, provided its held-out split is intact. A proposal for a different candidate version satisfies nothing.

Conditional specialists join for an identified gap: evidence-curator when the outcomes cite records that are not yet `source` or `validation` nodes; evaluation-designer on `improvement_needs_evaluation`; dataset-curator when no held-out split exists and one must be built from authorized, synthetic or permissioned cases; independent-auditor when the change alters a method that audits depend on; dissent-recorder when the steward and the analyst disagree on whether the failure is repeated. Private traces are never copied into fixtures; the curator builds synthetic equivalents.

A narrow request stays narrow. "Did the last three audited runs show the same failure?" routes to outcome-analyst alone and returns the outcome review. "Roll back the candidate we promoted" is a W10 change with the rollback version as the new version, not a new learning cycle.

Budget guidance: focused (4 tasks) fits the four unconditional stages for a method without fixtures or a cycle that ends at `retain_current`. Standard (12 tasks) is the default: five tasks here, the W05 comparison tasks for a method with fixtures, and one bounded decision-authority task when the promotion is within delegation and undisputed. Deep (24 tasks) is reserved for a disputed promotion that goes through W11 with two rounds. A protected change that does not fit the current mode requires explicit replanning or human approval to expand.

## Status handling and recovery

`needs_input`: the task and run move to `needs_input` with the exact question preserved, for example "The candidate changes the reply-tone instruction that the drafts-only policy references. Is this a method change within delegation or a policy change for the owner?" Completed stages stay accepted; the run returns to `planned` when the answer is recorded in the case ledger as user input.

`blocked`: the task names the unavailable capability or evidence, such as a missing held-out split, an audit without receipts or a sandbox the host cannot provide, and the run continues only the stages that do not depend on it. The user receives the outcome review and proposal so far and the blocker.

`failed`: receipts from any executed comparison are preserved and the failure is investigated within the remaining budget; a retry is a new attempt that counts against `max_worker_tasks`.

`partial`: completed artifacts stay stored, the candidate version stays on its branch, the run is not promoted to `completed`, and the report lists the missing outputs under `limitations`.

Budget exhaustion returns a useful partial result and a specific request to expand scope, naming the comparisons not run. The run never promotes a candidate to fit the budget and never switches mode on its own. In every case the user receives what the outcomes establish, what the candidate would change, what was and was not tested and the next resolving action.

## Authority boundary

This workflow never deploys, publishes, sends, pays, deletes or broadens access, and never edits the current version of a method in place: the candidate is a separate version and promotion is a `decision` record that moves the current pointer, accepted by the decision-authority within a delegation bound to the exact candidate version or by attested human input, with the previous version and its results retained for rollback. It never modifies a protected policy or an authority rule: a candidate that touches one is R2, returns `human_required`, and goes through W11 and attested human acceptance before any pointer moves. A promotion of a method the team itself uses to audit or decide is reviewed by an independent-auditor who did not author it. The audit-manager's favorable review records that the candidate is supported; promotion is a decision-authority or human act. A manager's favorable review creates no authority: the Audit Manager has `acceptance_authority: none`, and the decision-authority, whose authority is `delegation-limited`, cannot grant itself more or weaken any rule the candidate touched.

## Fixture

Scenario: a new prompt fixes the one example from which it was written but fails held-out negative cases. In the Reply Assist case, a revised drafting instruction removes an over-apologetic tone from the ws-alpha reply that prompted the complaint; on the held-out set it drafts a reply to a ws-alpha ticket using a ws-beta document and, on one case, drafts text that reads as a commitment to send.

Expected behavior: the review result is `revise` with the failing held-out cases named, `candidate_supported` is `false`, and no promotion decision is accepted (a decision proposed anyway is recorded `rejected` by the decision-authority); the current version remains current and the candidate remains readable on its branch with its development and held-out results; the drafts-only requirement and the workspace-isolation requirement are untouched and no authority rule is weakened; the steward's next proposal must address the held-out failures or recommend `gather_more_evidence`.

Fixture: `evals/workflows/learn-from-outcomes/fixture.json` records this scenario, its expected behavior and the acceptance lines. It has not been run against a model or a host.

## Invocation

Entry skill: `aipt-learn-from-outcomes`. It runs in your current session, never a forked one, and that session acts as the root orchestrator.

- Claude Code: `/aipt-learn-from-outcomes` followed by your request and the files or folders to use.
- Codex: `$aipt-learn-from-outcomes` followed by the same.
- Either host: describe the request in plain language; the `aipt-start` entry skill routes it here when it fits.

Example request: "Our last three evaluation runs show the same retrieval failure. Propose and test an improvement to the method."

Before dispatching any role, the session states the route plan: the stages it will run, the stages it will skip and why, the artifacts it will write, any missing input, and anything it will not do. Artifacts and the case ledger go under `aipt-cases/<case-id>/` in your project, as the `aipt-start` skill describes.

This release has no command-line controller. The record-keeping rules in this recipe (version binding, review independence, receipts, impact tracing) are followed by the orchestrating session as instructions; nothing enforces them in code. The experimental controller library in `src/` implements several of these rules in tested code, but it is not connected to either host.

## Live coverage

Per-host status is recorded in `docs/compatibility/`. As of this release, no workflow has been run end to end on either host, and this recipe's fixture is unrun.
