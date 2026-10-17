# W09 · Is this feature ready for the proposed release?

A team has a frozen build of an AI feature, an acceptance map and a set of results, and asks whether it can go to a proposed cohort. This workflow answers with an independent release review that returns pass, fail or blocked per check, a list of unresolved risks, and a human approval request bound to the exact version and cohort. It never deploys; readiness is a request for a human decision, not a release.

Entry skill `aipt-review-release` · Manager `audit-manager` · Minimum risk R2 · Core cross-host release test: no

## Purpose and outcome

Establish whether acceptance evidence exists for the current build version, whether authorization, injection and data-exposure controls are enforced rather than described, and whether a bounded release with stopping conditions and an exercised rollback has been planned. The outcome is a `release-readiness.md` with one of `ready_for_human_review`, `changes_required` or `blocked`, carrying every outstanding finding, and a human approval request stating exactly what approval would authorize.

In the synthetic case, Reply Assist at Larkspur Support is proposed for a cohort of ws-alpha agents. The acceptance map requires drafts-only behavior and workspace isolation between ws-alpha and ws-beta. An older slide in the corpus says "send automatically"; current policy says drafts only. The review treats the policy as controlling, treats the slide as a preserved conflict, and treats untested isolation as missing evidence rather than as a pass.

## Inputs

The user supplies the frozen build as a snapshot (a commit plus dirty-tree hash, or a content manifest covering code, tests and configuration), the accepted acceptance map version, the real results (validation records with receipts), and the proposed rollout scope (cohort, duration, owner and the observation the team will watch).

The case must already contain approved requirements with protected flags, the acceptance map, the authors and reviewers of the build and its prior checks (so independence can be verified), a source scope that authorizes reading the build, and the run budget.

When something is missing, the stage that needs it returns `needs_input` with the exact question and retains progress. Missing snapshot: "Which exact snapshot is proposed for release? Supply the commit and dirty-tree hash or a content manifest covering code, tests and configuration." Missing acceptance map: "Which accepted acceptance-map version governs this release? If none exists, run W02 first." Missing cohort: "Which cohort, duration and owner are proposed? A release without a named owner cannot be planned." Results that exist but are bound to an earlier snapshot are not `needs_input`; they are historical evidence, and `reproduce` reruns the checks.

## Outputs

`release-scope.json` (artifact node, status `proposed`): `snapshot` with `kind`, `commit`, `dirty_hash` or `manifest_ref`, `acceptance_map_version`, `requirements_in_scope[]` with `protected` flags, `proposed_cohort`, `duration`, `owner`, `prior_authors[]`, `prior_reviewers[]`, `results_offered[]` with `applicability` of `current` or `historical`.

`release-audit.json` (review record with validation records and receipts): `scope_version`, `snapshot`, `checks[]` each with `check_id`, `requirement_ref`, `receipt_id`, `result` of `passed`, `failed`, `blocked` or `not_run`, `applicability`, `coverage` with `requirements_total`, `covered`, `uncovered[]`, `independence` with `fresh_context`, `conflict_check` of `verified` or `independence_unverified`, `verdict` of `pass`, `fail` or `blocked`.

`security-review.json` (review record): `controls[]` each with `control`, `requirement_ref`, `evidence_kind` of `observed` or `claimed`, `result`, `findings[]` each with `id`, `severity`, `blocking`, `path`, `required_verification`, `triggered_reviews[]` naming privacy or accessibility review when added.

`rollout-plan.md` (artifact node): headings `## Cohort`, `## Observations`, `## Stopping conditions`, `## Rollback` (including whether it has been exercised and the receipt), `## Ownership`, `## Not authorized by this plan`.

`release-readiness.md` (review record, plus a decision record with status `human_required` when readiness is `ready_for_human_review`): headings `## Readiness`, `## Evidence for the current version`, `## Outstanding findings` (each with owner and blocking flag), `## Unresolved risks`, `## Human approval request`, `## What this review does not authorize`.

## Work graph

| stage id | role | depends on | conditional predicate | artifact | review / independence | write scope |
|---|---|---|---|---|---|---|
| freeze-scope | audit-manager | — | — | release-scope.json | author stage; reviewed at `readiness` | proposal-only |
| reproduce | independent-auditor | freeze-scope | — | release-audit.json | review gate; independence required | proposal-only |
| boundaries | security-reviewer | freeze-scope | — | security-review.json | review gate | proposal-only |
| plan-release | rollout-planner | reproduce, boundaries | — | rollout-plan.md | reviewed at `readiness` | proposal-only |
| readiness | audit-manager | reproduce, boundaries, plan-release | — | release-readiness.md | review gate | proposal-only |

`reproduce` and `boundaries` both read the frozen scope and do not depend on each other; dispatch them in parallel within the concurrency limit. `plan-release` waits for both because stopping conditions and rollback depend on their findings.

## Stage procedures

### freeze-scope

The audit-manager (`agents/audit-manager.md`) applies `aipt-method-structural-integrity-audit` to pin the exact snapshot, acceptance-map version and requirements in scope, and `aipt-method-independent-audit` to record who authored the build and its prior checks so that later reviewers can be assigned without conflict. Input refs: the snapshot, the acceptance map, the proposed rollout scope, the case's author and reviewer records. Accept when `release-scope.json` names one snapshot, marks every offered result as `current` or `historical` against that snapshot, and lists prior authors and reviewers by role and session.

### reproduce

The independent-auditor (`agents/independent-auditor.md`) applies `aipt-method-independent-audit` to rerun the critical checks in a fresh context through `aipt receipt run`, `aipt-method-requirements-and-acceptance` to map every in-scope requirement to a check and a negative case, and `aipt-method-drift-and-regression-audit` to compare the current snapshot with the one the offered results were bound to. Input refs: accepted `release-scope.json`, the acceptance map, the runnable checks. Accept when every check in `release-audit.json` carries a receipt or the result `blocked` or `not_run`, every uncovered requirement is listed, `conflict_check` is `verified`, and no result is copied from a historical record.

### boundaries

The security-reviewer (`agents/security-reviewer.md`) applies `aipt-method-security-and-privacy-review` to inspect authorization, injection handling and data exposure in the build, `aipt-method-tool-and-permission-boundaries` to confirm each permission check is deterministic code rather than a prompt instruction, and `aipt-method-independent-audit` to separate observed enforcement from claimed enforcement. Input refs: accepted `release-scope.json`, the build at the frozen snapshot, the protected requirements. Accept when every control in `security-review.json` has `evidence_kind` filled, every blocking finding names the verification that would close it, and privacy or accessibility review is triggered where the scope touches personal data or a user-facing interface.

### plan-release

The rollout-planner (`agents/rollout-planner.md`) applies `aipt-method-rollout-and-operations` to define cohort, observations, stopping conditions, rollback and ownership, `aipt-method-requirements-and-acceptance` to tie each observation to an acceptance criterion, and `aipt-method-delegated-authority` to state what the plan does not authorize. Input refs: accepted `release-audit.json` and `security-review.json`, the proposed rollout scope. Accept when `rollout-plan.md` names an owner, a stopping condition per blocking risk, and states whether rollback has been exercised with a receipt or remains untested.

### readiness

The audit-manager (`agents/audit-manager.md`) applies `aipt-method-structural-integrity-audit` to check that every in-scope requirement has current-version evidence or an open finding, `aipt-method-independent-audit` to confirm the auditor's independence was verified, and `aipt-method-security-and-privacy-review` to carry every blocking security finding forward unchanged. Input refs: accepted `release-audit.json`, `security-review.json` and `rollout-plan.md`. Accept when `release-readiness.md` returns one of the three states, preserves every outstanding finding with its owner, and states the exact version and cohort a human approval would cover.

## Gates

The run completes only when all five stages have accepted tasks, `reproduce`, `boundaries` and `readiness` each have a review record with result `ready` or `pass`, `reproduce` has `conflict_check: verified`, no `partial` output remains and no `needs_input` is open. `reproduce` is both a review gate and an independence gate: the controller refuses to admit it to any role that authored the build or its prior checks, and if the host cannot create a fresh review context the record says `independence_unverified` and the gate stays blocked. `boundaries` and `readiness` are review gates; the audit-manager may review the auditor's, reviewer's and planner's artifacts but not its own `release-scope.json`, which the readiness review takes as input rather than as an object of review. Review and independence gates are never pruned, whatever artifacts already exist.

A `blocked` or `fail` verdict from `reproduce` or a blocking finding from `boundaries` does not stop the run; it propagates into `readiness`, which returns `blocked` or `changes_required` with the finding intact.

Acceptance lines from the registry: never deploy or publish; current-version acceptance evidence; blocking findings cannot be waived by voting.

## Routing and pruning

`freeze-scope` is satisfied by an accepted `release-scope.json` only when its snapshot, acceptance-map version and cohort match the request exactly; a different snapshot is a new scope. `plan-release` is satisfied by an accepted `rollout-plan.md` bound to the same snapshot and cohort whose rollback status is unchanged. `reproduce`, `boundaries` and `readiness` are never pruned: offered results, a green CI status or an earlier review do not substitute for a fresh run against the current snapshot.

Conditional specialists join under these conditions: the privacy-reviewer when `changes_protected_scope` holds for a sensitive data flow or the scope touches personal data; the accessibility-reviewer when the release changes a user-facing interface; the operations-manager when the rollout plan names an alert without an owner or a rollback that has not been exercised; the red-team-tester when `boundaries` finds isolation or injection controls with only `claimed` evidence; the evidence-judge when `material_conflict` holds between a builder's claimed check and the auditor's observed result.

A narrow request such as "did the isolation test pass on this build?" routes to independent-auditor and audit-manager only, still with independence verified, and returns a check result rather than a readiness state.

Budget guidance: `focused` (4 tasks) does not fit the five required stages; the plan is returned with `budget_check.fits: false` and the user must choose `standard` or a narrow request. `standard` (12 tasks) is the default and carries the five stages with two specialists and a retry. `deep` (24 tasks) is for a disputed release where W11 challenge rounds are expected. A full run uses 5 tasks; with privacy and red-team review, 7.

## Status handling and recovery

`needs_input`: the task stores the exact question, the run moves to `needs_input`, accepted artifacts stay in place, and the user receives the question with the scope frozen so far.

`blocked`: when a check cannot be run because a tool or environment is unavailable, `reproduce` records that check as `blocked`, continues the remaining checks, and the user receives the list of unrunnable checks and the capability needed; `readiness` then cannot return `ready_for_human_review` for a protected requirement whose check is blocked.

`failed`: a failing check keeps its receipt and is reported as `failed`, never retried into a pass without a new snapshot; a failed task attempt keeps its receipts and is investigated within the work order's retry budget.

`partial`: when a stage could not cover its listed requirements, completed checks stay accepted and the run cannot reach `completed`; the user receives the coverage gap.

Budget exhaustion: the run returns the accepted artifacts, the stages not reached and a specific request to expand scope, and it never drops a review gate or switches mode to fit.

In every case the user receives a packet stating what is verified for the current version, what is missing and the single next resolving action.

## Authority boundary

This workflow never deploys, publishes, sends, pays, deletes, flips a feature flag, broadens access or changes a cohort in a running system. Release is an R3 external action and sits outside autonomous execution; `ready_for_human_review` prepares a human action request bound to the exact snapshot and cohort, and a human performs the release. A change to release criteria, a protected requirement or a sensitive data flow is R2 and requires W11 when disputed and human acceptance before it takes effect. Blocking findings are not resolved by a majority of favorable reviews; a dispute over whether evidence is sufficient goes to W11, where a judge rules on sufficiency and still cannot authorize release. A favorable audit-manager review records that the evidence is complete for the version reviewed; it creates no authority to release.

## Fixture

Registry scenario: all happy-path tests pass but there is no exercised rollback and isolation remains untested. Expected behavior: `release-audit.json` records the isolation requirement as `not_run` with coverage uncovered, `rollout-plan.md` records rollback as untested, and `release-readiness.md` returns `blocked` or `changes_required` for human review. The workflow neither deploys nor converts the missing evidence into a pass, and the happy-path passes remain recorded as passes with limited coverage.

Fixture path: `evals/workflows/review-release/fixture.json`. A replay of this fixture is labeled `fixture_replay` and is not a live run.

## Invocation

Entry skill: `aipt-review-release`.

- `aipt run start --case CASE --workflow review-release --mode standard` records a run bound to the case, this workflow version, risk R2 and the `standard` budget.
- `aipt run plan --run RUN_ID` records the route plan with the three unprunable review gates and any triggered specialist.
- `aipt task next --run RUN_ID` lists the ready tasks, which after `freeze-scope` are `reproduce` and `boundaries` together.
- `aipt task admit --task TASK_ID` records the admission checks, including that the reviewer is not an author of the artifact under review, and reserves a worker slot.
- `aipt task attach --task TASK_ID --native-child-id CHILD_ID` records the fresh native child for the auditor so independence can be verified rather than claimed.
- `aipt receipt run --task TASK_ID -- <check command>` records a receipt for each rerun check against the frozen snapshot.
- `aipt task submit --task TASK_ID --response response.json` records the response envelope and stores its artifacts as proposed versions.
- `aipt review submit --run RUN_ID --record review.json` records each review gate's result against the exact versions reviewed.
- `aipt decision propose --run RUN_ID --record decision.json` records the human approval request with status `human_required`, bound to the snapshot and cohort.
- `aipt decision record-user-input --run RUN_ID --record user-input.json` records the human's answer with `attested: false`; a protected transition still needs the approval provenance the architecture defines.
- `aipt case report --case CASE --format markdown` renders the case state, including readiness, outstanding findings and coverage.

## Live coverage

| host | fixture_replay | native | last run |
|---|---|---|---|
| `adapters/<host>` (one row per host directory) | not yet run | not yet run | — |

This table is updated only from recorded runs.
