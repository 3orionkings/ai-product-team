# W06 · Find out why this feature is failing.

This workflow answers the request "something is wrong with the feature; find out why". The user has failure reports, authorized traces, a list of recent changes and the outcome definitions the feature is judged by. It returns a validated symptom, a ranked set of hypotheses typed by the component they implicate, the discriminating tests that would confirm or kill each one, and a repair recommendation that names a bounded work order instead of performing the repair.

Entry skill `aipt-investigate-failure` · Manager `evaluation-manager` · Minimum risk R0 · Core cross-host release test no

## Purpose and outcome

Use this workflow when a reported failure needs a cause before anyone acts on it: Reply Assist drafts at Larkspur Support start citing the wrong refund policy, ws-alpha agents report seeing ws-beta phrasing in a draft, or a metric moves and the team is about to credit or blame the feature. The outcome is a diagnosis the team can act on with a stated level of confidence: the symptom as actually defined and reproduced, the cuts that separate volume, rate, data quality and task outcome, the conflicts between what the documents say and what the traces show, and a recommendation that says which component is implicated and what to check next.

The workflow validates the failure definition before it investigates causes. It distinguishes model, retrieval, tool, interface and data failures rather than defaulting to the model. It recommends repair; the repair itself is a separate scoped work order under `build-prototype`.

## Inputs

The user supplies:
- Failure reports: the complaints, tickets, dashboards or metric alerts, registered as `source` records with their observation time and access scope.
- Authorized traces: request and response logs, retrieval logs, tool-call records or evaluation outputs inside the case source scope, with their time range and any redaction applied.
- Recent changes: the deployed code, configuration, prompt, policy or interface changes in the window, with dates, or a `change-assessment` from `process-change`.
- Outcome definitions: the measure the feature is judged by, drawn from approved requirements, the acceptance map or the evaluation plan.

The case must already contain the source scope that authorizes the traces and the protected constraints (for Reply Assist: drafts only, never send; workspace isolation between ws-alpha and ws-beta). Earlier `evaluation-plan` and `results` artifacts are used when current.

When something is missing, the run returns `needs_input` and retains progress:
- No outcome definition: "What outcome defines the failure: complaint volume, draft acceptance rate, task completion or something else? Name the measure and the source that defines it."
- No time range or cohort: "Over which period and for which users or workspaces is the failure reported? Give the window and the cohort."
- No recent-change list: "Which code, configuration, prompt, policy or interface changes landed in the window? List them or confirm none."
- Traces not in scope: the stages that need them return `blocked`; the brief continues on reports and changes alone and names the trace access that would unblock the rest.
- Report cannot be reproduced and the user wants causes anyway: "The symptom did not reproduce on the supplied cases. Supply a reproducing case, or accept an analysis limited to the reported data."

## Outputs

| Artifact | Shape | Stored as |
|---|---|---|
| `incident-brief.md` | Headings: Reported symptom · Outcome definition used · Time range and cohorts · Recent changes · Reproduction status · Established, inherited and assumed · Open questions. | `artifact` node, kind `incident-brief`, status `proposed`; the symptom proposed as a `claim` of type `observation` |
| `hypotheses.json` | `{symptom_ref, cuts: [{dimension: volume/rate/data_quality/task_outcome, finding, evidence_refs}], hypotheses: [{id, statement, component: model/retrieval/tool/interface/data/process, prior: low/medium/high, confirming_test, killing_test, evidence_refs}], retained_alternatives: []}` | `artifact` node, kind `hypotheses`; each hypothesis proposed as a `claim` of type `hypothesis` |
| `conflicts.json` | `{conflicts: [{id, records: [refs], kind: context_difference/actual_contradiction, explanation, resolution_options: [], status: open/explained}]}` | `artifact` node, kind `conflicts`; `contradicts` edges proposed between the records, which mark the affected claim `contested`, not false |
| `diagnostic-evidence.json` | `{snapshot, code_paths: [{path, symbol, observation, receipt_id}], commands_observed: [{command, receipt_id}], specialist_requests: [], finding: implicated/cleared/inconclusive}` | `artifact` node, kind `diagnostic-evidence`; each command a `receipt` |
| `remediation-recommendation.md` | Headings: Diagnosis reviewed · Confidence and what remains untested · Containment proposal · Remediation work order request · Not authorized here · Next discriminating measure. | `review` node via `aipt review submit`, with the recommendation body stored as an `artifact` of kind `remediation-recommendation` |

The registry outputs map as follows: validated symptom is `incident-brief.md`; hypotheses and discriminating tests are `hypotheses.json`, with `conflicts.json` and `diagnostic-evidence.json` as supporting evidence; repair recommendation is `remediation-recommendation.md`.

## Work graph

| Stage id | Role | Depends on | Conditional predicate | Artifact | Review / independence | Write scope |
|---|---|---|---|---|---|---|
| `validate-report` | `context-analyst` | — | — | `incident-brief.md` | — | proposal-only |
| `discriminating-cuts` | `failure-analyst` | `validate-report` | — | `hypotheses.json` | — | proposal-only |
| `reconcile` | `contradiction-analyst` | `discriminating-cuts` | — | `conflicts.json` | — | proposal-only |
| `targeted-causes` | `repository-mapper` | `reconcile` | `evidence_points_to_code` | `diagnostic-evidence.json` | — | proposal-only; read-only commands through receipts |
| `review-contain` | `evaluation-manager` | `targeted-causes` when included, otherwise `reconcile` | — | `remediation-recommendation.md` | review | proposal-only |

Edges follow stage order by default. `reconcile` is parallelizable with `discriminating-cuts` when the incident brief already lists the conflicting records; in that case both depend on `validate-report` and the failure analyst receives `conflicts.json` as an input before finalizing priors. `targeted-causes` may expand to one task per implicated component, with `retrieval-designer` or `tool-integration-designer` taking the task where the evidence points at retrieval or at a tool contract rather than at code.

## Stage procedures

### `validate-report` — context-analyst
Read `agents/context-analyst.md`. Apply `aipt-method-corpus-grounded-onboarding` to reconstruct what the reports say, which definition they use and what the recent changes were, separating current observations from inherited decisions and assumptions, and `aipt-method-status-handoff` to write the brief as a short derived record rather than a narrative. Input refs: the report sources, the change list, the outcome definition versions, trace sources when in scope. Check the definition, the time range, the cohorts and whether the symptom reproduces on at least one supplied case. An obsolete specification is not treated as current behavior; it is listed under inherited decisions. Accepted when the brief states the outcome definition used, the window and cohort, the reproduction result, and names every source by ref.

### `discriminating-cuts` — failure-analyst
Read `agents/failure-analyst.md`. Apply `aipt-method-evaluation-planning` to define the cuts and the pass condition for each test before looking for a culprit, `aipt-method-evaluation-execution-and-receipts` to read the traces against their recorded versions, and `aipt-method-corpus-grounded-onboarding` to keep symptom, cause and remedy apart. Input refs: `incident-brief.md`, the trace sources, current `results` when present. Distinguish volume (how many reports), rate (reports per task), data quality (whether the measurement itself changed) and task outcome (whether drafts got worse). For each hypothesis, record a prior, the component it implicates and one confirming and one killing test. The model is not blamed by default; a retrieval or permission cause is retained as an alternative with its own test. Accepted when every cut cites evidence, every hypothesis has both tests, and alternatives are retained rather than collapsed into a favorite.

### `reconcile` — contradiction-analyst
Read `agents/contradiction-analyst.md`. Apply `aipt-method-evidence-and-lineage` to record which records disagree and to propose `contradicts` edges, `aipt-method-structural-integrity-audit` to separate an actual contradiction from a scope or context difference, and `aipt-method-corpus-grounded-onboarding` to anchor each record in its own time and audience. Input refs: `hypotheses.json`, the report and trace sources, the requirement versions, the recent-change list. For Reply Assist, the older slide saying "send automatically" and the current policy saying "drafts only" is a scope difference with a date, not a live contradiction, and the brief must not pick the newer record silently when its scope differs. Accepted when every conflict is typed, explained and either resolved with evidence or left open with resolution options, and no record is discarded.

### `targeted-causes` — repository-mapper
Read `agents/repository-mapper.md`. Runs only under `evidence_points_to_code`. Apply `aipt-method-corpus-grounded-onboarding` to follow the implicated execution path from the actual entry point, and `aipt-method-structural-integrity-audit` to spot duplicated or diverging code paths that could explain cohort differences. Input refs: `hypotheses.json`, `conflicts.json`, the repository root and snapshot from the case. Inspect only the paths the evidence names, run read-only commands through `aipt receipt run`, and raise the risk tier to R1 when any command executes. Where the evidence points at retrieval filtering or a tool contract, request `retrieval-designer` or `tool-integration-designer` instead of guessing. Accepted when every observation cites a file and snapshot or a receipt, the finding is `implicated`, `cleared` or `inconclusive` per hypothesis, and no entry point is invented.

### `review-contain` — evaluation-manager
Read `agents/evaluation-manager.md`. Apply `aipt-method-independent-audit` to check that each hypothesis status traces to a test that ran or is marked untested, `aipt-method-outcome-and-value-analysis` to judge whether the outcome measure actually tracks task quality, and `aipt-method-evaluation-planning` to specify the next discriminating measure. Input refs: all upstream artifacts. The manager states which component is implicated and at what confidence, proposes a bounded, reversible containment where one exists, and writes the remediation as a work-order request for `build-prototype` with its own checks. Nothing in the recommendation changes production. Accepted when `result` is set, confidence is tied to executed tests, the containment is reversible and inside authorized scope, and the work-order request names the requirement it serves.

## Gates

The run completes only when all of the following are true:
- Every non-conditional stage has an accepted task or a `satisfied_by_version_id` for a current artifact of its type; `targeted-causes` is required only when `evidence_points_to_code` evaluated true at planning.
- `review-contain` has a `review` node with `result` in `{ready, pass}`. This stage is a review gate; the Evaluation Manager authored none of the brief, hypotheses, conflicts or diagnostic evidence, which admission enforces.
- The symptom in `incident-brief.md` is the one the hypotheses and recommendation refer to; a redefined symptom restarts from `validate-report`.
- No `partial` outputs remain and no `needs_input` is open.

Review gates are never pruned. This workflow has no stage with `independence_required`; when the recommendation is contested or reaches R2, `resolve-decision` supplies the independent judges, and its gates block on `independence_unverified` when a fresh context cannot be made.

Acceptance lines from the registry: Validate the failure definition first. Differentiate model, retrieval, tool, UI and data failures. Repair requires a separate scoped work order.

## Routing and pruning

A stage is satisfied without a new task when a current accepted artifact of its type exists for the same symptom: `validate-report` when an `incident-brief` is current for the same reports and window; `discriminating-cuts` when `hypotheses` are current and no new trace or change has arrived; `reconcile` when `conflicts` are current for the same record set; `targeted-causes` when `diagnostic-evidence` is current for the same snapshot. A new trace, a new change or a redefined outcome invalidates applicability of everything downstream of the brief.

Conditional specialists join when a named condition holds:
- `repository-mapper` under `evidence_points_to_code`, as the `targeted-causes` stage itself.
- `retrieval-designer` when a hypothesis implicates source acquisition, access filtering or freshness, for example ws-beta text appearing in a ws-alpha draft.
- `tool-integration-designer` when a hypothesis implicates a tool contract: timeouts, retries, malformed results or a missing idempotency key.
- `outcome-analyst` when the outcome definition itself is in question, for example when complaint volume is being read as task quality.
- `test-engineer` when a discriminating test needs executable code; it returns the check as a proposed patch and runs it through receipts.
- `material_conflict` on the diagnosis, or an R2 containment, routes to `resolve-decision`.

A narrow request, such as "tell me whether the drop in complaints means drafts improved", produces `validate-report` and `discriminating-cuts` with `outcome-analyst` attached, then `review-contain`; no code inspection and no contradiction stage unless the brief surfaces a conflict.

Budget guidance: focused (4 tasks) fits a definition check and one cut with the review: brief, cuts, review, one slot spare; standard (12 tasks) covers the full chain with one or two targeted-cause tasks and a retry, usually 5 to 7 tasks; deep (24 tasks) is for several implicated components with specialists on each, or a disputed diagnosis that needs a challenge round. Every attempt and retry counts.

## Status handling and recovery

- `needs_input`: the exact question is preserved in the run record; the accepted brief and any accepted hypotheses stay accepted; the run returns to `planned` when `aipt decision record-user-input` supplies the answer.
- `blocked`: the task records the trace, log or tool that is unavailable; stages that do not need it continue; the recommendation lists what access would unblock the rest. The user receives the blocker, the diagnosis so far and the next resolving action.
- `failed`: receipts from a failed command are preserved with exit status and logs; a timeout is distinguished from a failing exit; retries stay within the work order's budget; a failed inspection never becomes a `cleared` finding.
- `partial`: cuts and conflicts that completed stay accepted; the run cannot complete while an implicated component has no finding; the recommendation names the components left `inconclusive`.
- Budget exhaustion: dispatch stops; the brief, hypotheses and any findings are summarized with receipts; the user is asked for an explicit expansion or a narrower component list. The run never skips the review and never promotes an untested hypothesis to a cause to close out.
- Symptom not reproduced: the run does not stop; the brief records `reproduction: not_reproduced`, every downstream finding carries that limitation, and the recommendation asks for a reproducing case before any repair is scheduled.

In every case the user receives a packet: what is established, what is hypothesis with its test, what is blocked or missing, and the single next action.

## Authority boundary

This workflow never deploys, publishes, sends a message, pays, deletes data, rolls back a release or changes a production configuration. Its only commands are read-only inspections recorded as receipts; everything it returns is a proposal. Containment is a recommendation to a person; remediation is a work-order request executed later under `build-prototype` (W04) within its own write authorization. A containment that would change a protected requirement, an authority rule or a sensitive data flow is R2 and goes through `resolve-decision` (W11) with human acceptance bound to the exact proposal version. For Reply Assist, a recommendation to "stop sending drafts" is rejected as a misreading: the current policy already says drafts only, so the question becomes why a send path exists at all, and that is an authority finding for a human, not a fix. A manager's favorable review creates no authority: the Evaluation Manager has `acceptance_authority: none`.

## Fixture

Scenario: Support complaints fall after the reporting interface becomes harder to find. Expected behavior: the analysis distinguishes reporting volume from actual task quality, records the interface change as a data-quality cut, types "the feature improved drafts" as a hypothesis with a prior and a killing test, and asks for a discriminating measure such as draft acceptance rate on a fixed cohort before crediting the AI feature.

Fixture path: `evals/workflows/investigate-failure/fixture.json`. A replay of this fixture is labeled `fixture_replay` and is not a live run.

## Invocation

Entry skill: `aipt-investigate-failure`, loaded in the root session only.

- `aipt run start --case CASE --workflow investigate-failure --mode standard` records a run in state `created` then `scoped`, with the case, workflow version, mode, risk floor R0 and the host when observable.
- `aipt run plan --run RUN` records the route plan: selected and omitted roles with reasons, the `evidence_points_to_code` evaluation, satisfied-by versions and the budget check.
- `aipt task next --run RUN` lists the ready tasks whose dependencies are accepted, in dependency order.
- `aipt task admit --task TASK` runs the admission checks (dependencies, budget, write scope, author-as-reviewer, source scope, wall clock) and mints the work order with a reserved slot.
- `aipt task attach --task TASK --native-child-id CHILD` records the native child identity and execution mode; without it, a native claim is downgraded to `sequential` with `observed_by=agent_reported`.
- `aipt task submit --task TASK --response response.json` validates the envelope, stores the brief, hypotheses, conflicts and diagnostic evidence as proposed nodes, records proposed claims and `contradicts` edges as proposals, and moves the task to `submitted`.
- `aipt receipt run --task TASK -- <command>` executes a read-only inspection and stores the receipt with command, snapshot, exit status and log locations.
- `aipt review submit --run RUN --record review.json` records the manager review with its conflict check; the controller refuses a reviewer who authored an artifact under review.
- `aipt decision propose --run RUN --record decision.json` records an R2 containment or a disputed diagnosis as a proposal for `resolve-decision`; `aipt decision record-user-input --run RUN --record user-input.json` records the user's answer with `channel=cli` and `attested=false`.
- `aipt case report --case CASE --format markdown` renders the derived report, including contested claims, open questions and the requested remediation work order.

## Live coverage

| Host | fixture_replay | native | Last run |
|---|---|---|---|
| first native host (see `docs/compatibility/`) | not yet run | not yet run | — |
| second native host (see `docs/compatibility/`) | not yet run | not yet run | — |
| fixture runner, no host | not yet run | — | — |

This table is updated only from recorded runs; no cell is inferred from parsed files or from a run on another host. This workflow is not in the core cross-host matrix; its live coverage is reported here exactly and is never implied by the core six.
