# W10 · Something changed. What must we revisit?

A source, decision, build or validation in the case has changed and the user asks what that change invalidates, what remains valid and what must be redone. The workflow answers with an impact queue derived from declared dependencies, a correction proposal that states whether the new evidence defeats an existing premise or only narrows its scope, a reviewed authorization of the correction and, when the predicates fire, targeted work orders and an independent revalidation against the new versions. The baseline is never overwritten, protected requirements stay in force, and historical test results keep their recorded outcome.

Entry skill `aipt-process-change` · Manager `audit-manager` · Minimum risk R1 · Core cross-host release test yes

## Purpose and outcome

Change arrives in several forms: a corrected source document, a new negative test, a revised decision, a changed dependency or an unexplained drift in a build. Each can make earlier work stale in a different way, and architecture section 12.2 separates source freshness, factual support, policy approval, implementation validity and test applicability. This workflow processes one accepted change through the ten steps of architecture section 12.1: preserve the old version, classify the change, evaluate contested claims before accepting a correction, traverse declared `depends_on` edges in reverse, queue affected work with typed reasons, keep protected requirements active, request semantic inspection where lineage is missing, generate only the necessary rework, revalidate against the new version and refresh the derived reports.

The outcome the user receives is a short answer to "what must we revisit": the affected versions with the reason each is affected, the versions that remain valid, the lineage gaps the controller could not traverse, the correction the manager authorized or escalated, and the state of any rework and revalidation. In the Reply Assist case at Larkspur Support, a cross-workspace negative test that shows a ws-beta document in a ws-alpha draft produces a queue that reaches the isolation requirement, the retrieval implementation, the earlier positive isolation test and the release decision, and nothing else.

## Inputs

The user supplies the old and new version of the changed source or artifact (or a locator the controller can version), a statement of the intended change when the change was deliberate, and any new evidence such as a test receipt or trace. The dependency graph is not supplied by hand; it is the set of accepted `depends_on` edges already in the case store, each with an `impact_policy` of `review`, `invalidate_applicability` or `none` and a reason.

The case must already contain the baseline version as an immutable `node_versions` row, at least one accepted edge touching it, and the protected requirements as `requirement` nodes with `protected: true`. Without the baseline the workflow cannot compare and returns `needs_input` with the question "Which stored version is the baseline for this change? Supply its version id or the locator to ingest." Without an intended-change statement for a change that is not plainly corrective or environmental, `preserve-versions` classifies it `unexplained` and continues; it does not stop. Without any `depends_on` edge from the changed version, `map-affected` returns an empty queue plus a `missing_lineage` list and the workflow continues to semantic review rather than claiming nothing is affected.

## Outputs

`change-assessment.json` (registry output: part of the revised proposal) — keys `baseline_version`, `changed_version`, `change_kind` (`intended`, `corrective`, `environmental` or `unexplained`), `intended_deltas`, `observed_deltas`, `new_evidence_refs`, `baseline_preserved` (always `true`) and `limitations`. Stored as an `artifact` node with status `proposed`; the new version itself is a fresh `source`, `claim` or `validation` version with a proposed `supersedes` edge to the old one.

`impact-queue.json` (registry output: impact queue) — keys `changed_version`, `impacts` (each `affected_version`, `kind`, `path`, `impact_policy`, `reason`), `protected_requirements_affected`, `missing_lineage` (each `version`, `gap`) and `semantic_review_requested`. Stored as an `artifact` node; on acceptance of the correction the controller writes the rows into the `impact_queue` table.

`correction-proposal.json` (registry output: revised proposal) — the `proposal` schema: `title`, `options` (at least `defeats_premise`, `narrows_scope`, `no_effect`), `recommended_option`, `assumptions`, `evidence_refs`, `constraints`, `unresolved_questions`, `target_refs`, `author_role`, `requested_authority`. Stored as a `proposal` node; each contested claim receives a proposed `contradicts` edge and moves to status `contested`, never directly to `unsupported`.

`change-review.json` — the `review` schema: `reviewed_refs`, `reviewer_role`, `reviewer_session`, `findings`, `evidence_sufficiency`, `result` (`ready`, `revise`, `blocked` or `escalate`), `conflict_check`, `unresolved`, plus `correction_outcome` (`supported`, `unsupported` or `superseded`) and `protected_scope_touched`. Stored as a `review` node.

`targeted-work-orders.json` (registry output: targeted work orders) — keys `work_orders` (each `id`, `delegated_workflow` among `shape-feature`, `build-prototype`, `evaluate-feature`, `role`, `objective`, `write_scope`, `prerequisites`, `acceptance_checks`, `affected_versions`) and `excluded` (each `version`, `reason`). Stored as an `artifact` node; each order becomes a `planned` task in the delegated run.

`revalidation.json` (registry output: revalidation results) — one `validation` record per check: `method`, `target_refs`, `receipt_id`, `result`, `rubric`, `coverage`, `applicability`, plus `historical` listing the prior validation versions now marked `historical`. Stored as `validation` nodes with the auditor's `review` node over them.

## Work graph

| stage id | role | depends on | conditional predicate | artifact | review / independence | write scope |
|---|---|---|---|---|---|---|
| preserve-versions | change-impact-analyst | — | — | change-assessment.json | — | proposal-only |
| map-affected | dependency-steward | preserve-versions | — | impact-queue.json | — | proposal-only |
| assess-contradictions | contradiction-analyst | preserve-versions | — | correction-proposal.json | — | proposal-only |
| authorize | audit-manager | map-affected, assess-contradictions | — | change-review.json | review gate | proposal-only |
| rework | implementation-planner | authorize | rework_required | targeted-work-orders.json | — | proposal-only |
| revalidate | independent-auditor | authorize; rework when present | revalidation_required | revalidation.json | review gate, independence required | proposal-only |

`map-affected` and `assess-contradictions` both read only the change assessment and run in parallel. Every stage is proposal-only: the workflow proposes versions, edges and queue rows, and the controller commits them after review. Code changes happen only inside a delegated W04 run with its own `assigned-worktree` tasks.

## Stage procedures

### preserve-versions
The change-impact-analyst (`aipt-change-impact-analyst`) receives the baseline version id, the new version or locator, the intended-change statement and the new evidence refs. It applies `aipt-method-drift-and-regression-audit` to compare the two versions against declared invariants and allowed deltas, `aipt-method-corpus-grounded-onboarding` to separate stated facts from inferences in the new material, and `aipt-method-evidence-and-lineage` to store the new version as an immutable node with scope and limitations. The baseline row is not touched; the new version gets a proposed `supersedes` edge. Accepted when the assessment names both version ids, classifies the change, lists observed deltas that are not in the intended list, and `baseline_preserved` is `true`.

### map-affected
The dependency-steward (`aipt-dependency-steward`) receives the accepted change assessment and the case's accepted `depends_on` edges. It asks the controller for `impact(changed_version)`: a reverse breadth-first traversal over accepted `depends_on` edges only, in deterministic order, returning each affected version with its path, `impact_policy` and reason. It applies `aipt-method-evidence-and-lineage` to read the edges and `aipt-method-requirements-and-acceptance` to tell an invalid justification from a requirement that remains mandatory. Protected requirements in the affected set are listed under `protected_requirements_affected` with reason `protected_requirement_implementation_affected`; they are queued for review, never for invalidation. Artifacts with no `depends_on`, requirements with no `implements` and validations with no `verifies` target go to `missing_lineage` with a request for semantic review. Accepted when every queued item carries a declared path and the lineage gaps are reported separately from the traversal.

### assess-contradictions
The contradiction-analyst (`aipt-contradiction-analyst`) receives the change assessment, the contested claims and their dates, scope and authority. It applies `aipt-method-structural-integrity-audit` to check that the contradiction is real rather than a scope difference, `aipt-method-corpus-grounded-onboarding` to read both records in context and `aipt-method-evidence-and-lineage` to record a `contradicts` edge, which moves the old claim to `contested` and no further. The proposal offers at least the options `defeats_premise`, `narrows_scope` and `no_effect` and recommends one with evidence refs. Accepted when the recommended option is one of the listed options, the unresolved questions are explicit, and no claim status has been set to `unsupported` ahead of review.

### authorize
The audit-manager (`aipt-audit-manager`) receives the impact queue, the correction proposal and the identities of their authors. It applies `aipt-method-structural-integrity-audit` to check that the queue and the proposal agree, `aipt-method-independent-audit` to decide what revalidation must be rerun rather than reread, and `aipt-method-security-and-privacy-review` when the change touches access scope or data flow. If `changes_protected_scope` is true the result is `escalate`: the correction is handed to W11 (`resolve-decision`) and, for R2, to human acceptance, and the correction stays `proposed` until that returns. Otherwise the result is `ready` with `correction_outcome`, and the controller applies `accept_correction` and the impact rows. Accepted when the review names the reviewed versions, the reviewer is not the author of either input, and every protected requirement in the queue is still `approved`.

### rework
The implementation-planner (`aipt-implementation-planner`) runs only when `rework_required` is true: the accepted correction invalidated the applicability of at least one implementation or specification artifact. It receives the accepted change review and the affected versions and applies `aipt-method-milestone-planning` to cut bounded work orders with write sets and prerequisites, and `aipt-method-requirements-and-acceptance` to attach the exact checks each order must pass. Each order names the workflow that executes it (W02 for specification, W04 for implementation, W05 for evaluation); orders for unaffected artifacts are listed under `excluded` with a reason. Accepted when every order maps to a queued version and no order touches work outside the queue.

### revalidate
The independent-auditor (`aipt-independent-auditor`) runs only when `revalidation_required` is true: at least one validation lost applicability. It receives the frozen new versions, the acceptance criteria and the runnable checks, in a fresh review context whose child id is recorded. It applies `aipt-method-independent-audit` to rerun the checks and report unavailable tools as `blocked`, `aipt-method-drift-and-regression-audit` to compare against the baseline results, and `aipt-method-requirements-and-acceptance` to confirm coverage of each affected requirement. Old validation versions are marked `historical` with their result untouched. Accepted when each new validation carries a `receipt_id` or is `not_run`, `conflict_check` is `verified`, and the historical list is complete.

## Gates

The run completes only when `preserve-versions`, `map-affected`, `assess-contradictions` and `authorize` each have an `accepted` task or a `satisfied_by_version_id`; `authorize` has a `review` node with result `ready` or `pass`; `revalidate`, when its predicate is true, has `conflict_check` equal to `verified`; no output is `partial`; and no `needs_input` is open. `authorize` is the review gate: the audit-manager may not have authored the correction proposal or the impact queue. `revalidate` is the independence gate: the auditor may not be the producer of any revalidated artifact and may not share a session or child id with one. Review and independence gates are never pruned, whatever artifacts already exist. If the host cannot provide a fresh review context, the report says `independence_unverified` and the run stays `blocked` at that gate.

The registry acceptance lines are checked against the stored records: only declared affected dependencies are automatically queued; constraints survive failed implementations; historical test outcomes are preserved.

## Routing and pruning

A stage is satisfied without a model call when a current accepted artifact of its type exists for the same changed version: an earlier change assessment and impact report may already exist, so a run started after one records `satisfied_by_version_id` on `preserve-versions` and, when the queue was accepted, on `map-affected`. A correction proposal accepted in an earlier run for the same contradiction satisfies `assess-contradictions`. The authorize review is never satisfied by an earlier review of a different version.

Conditional specialists join for an identified gap, not by default: evidence-curator when new evidence arrives without a `source` record; claim-checker when a contested claim's support is itself in doubt; requirements-writer, through W02, when an authorized correction requires rewording a requirement; refactoring-engineer and test-engineer, through W04 and W05, when rework or retest tasks are issued; decision-recorder when the authorize stage returns a decision from W11. `rework` joins on `rework_required`; `revalidate` joins on `revalidation_required`; W11 joins on `changes_protected_scope`.

A narrow request stays narrow. "Rewrite one approved requirement for clarity" routes to requirements-writer plus change-impact-analyst and does not open this workflow's full graph; a detected semantic permission change in that rewrite still escalates. "Tell me what this new test result affects" can stop after `map-affected` with a derived change impact report.

Budget guidance: focused (4 tasks, no challenge round) fits the four unconditional stages only when neither predicate fires; use it for a corrective change with no implementation downstream. Standard (12 tasks, one round) is the default: four to six tasks here plus a delegated W11 when protected scope is touched. Deep (24 tasks, two rounds) is for a disputed correction whose W11 needs a second challenge round. A W11 that does not fit the current mode requires explicit replanning or human approval to expand; the run does not switch mode on its own.

## Status handling and recovery

`needs_input`: the task and run move to `needs_input` with the exact question preserved, for example "Is the new test the authoritative check for requirement REQ-ISO-01, or a diagnostic probe?" Completed artifacts stay accepted; the run returns to `planned` when the answer is recorded in the case ledger as user input.

`blocked`: the task reports the unavailable capability or evidence, such as a missing receipt or a host that cannot open a fresh review context, and the run continues only the stages that do not depend on it. The user receives the queue and proposal so far and the named blocker.

`failed`: receipts are preserved and the failure is investigated within the remaining budget; a retry is a new attempt that counts against `max_worker_tasks`.

`partial`: completed artifacts stay stored and visible, the run is not promoted to `completed`, and the report lists the missing outputs under `limitations`.

Budget exhaustion returns a useful partial result and a specific request to expand scope, naming the stages not run. The run never switches to deep mode silently and never drops the review or independence gate to fit. In every case the user receives what is known, what is affected, the lineage gaps and the next resolving action.

## Authority boundary

This workflow never deploys, publishes, sends, pays, deletes or broadens access, and never edits product code: rework is proposal-only here and executes only in a delegated W04 run with its own write authorization. It never retires or weakens a protected requirement; a failed implementation queues the requirement for review with reason `protected_requirement_implementation_affected` and leaves it `approved`. A correction that touches a protected requirement, an authority rule, a sensitive data flow or a release criterion is R2: it requires W11 and human acceptance with attested provenance before the correction event is applied. The audit-manager's favorable review authorizes the correction event within delegation and nothing else; it creates no new authority and is not independent verification.

## Fixture

Scenario: a negative test disproves an isolation assumption after a positive test passed. In the Reply Assist case, the earlier positive test showed a ws-alpha query returning only ws-alpha documents; the new cross-workspace negative test shows a ws-beta document in a ws-alpha draft.

Expected behavior: the isolation requirement remains mandatory and is queued as `review_required`; the release decision that depended on the isolation claim is queued for review; the old positive test keeps result `passed` with applicability `historical`; only the retrieval implementation and its isolation checks are requeued, through W04 and W05, and unrelated completed work is untouched.

Fixture: `evals/workflows/process-change/fixture.json` records this scenario, its expected behavior and the acceptance lines. It has not been run against a model or a host.

## Invocation

Entry skill: `aipt-process-change`. It runs in your current session, never a forked one, and that session acts as the root orchestrator.

- Claude Code: `/aipt-process-change` followed by your request and the files or folders to use.
- Codex: `$aipt-process-change` followed by the same.
- Either host: describe the request in plain language; the `aipt-start` entry skill routes it here when it fits.

Example request: "This new negative test contradicts the isolation assumption. What must we revisit?"

Before dispatching any role, the session states the route plan: the stages it will run, the stages it will skip and why, the artifacts it will write, any missing input, and anything it will not do. Artifacts and the case ledger go under `aipt-cases/<case-id>/` in your project, as the `aipt-start` skill describes.

This release has no command-line controller. The record-keeping rules in this recipe (version binding, review independence, receipts, impact tracing) are followed by the orchestrating session as instructions; nothing enforces them in code. The experimental controller library in `src/` implements several of these rules in tested code, but it is not connected to either host.

## Live coverage

Per-host status is recorded in `docs/compatibility/`. As of this release, no workflow has been run end to end on either host, and this recipe's fixture is unrun.
