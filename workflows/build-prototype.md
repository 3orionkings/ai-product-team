# W04 · Build a bounded version we can test.

This workflow answers the request "build the piece we agreed on so we can test it". An accepted scope and an architecture exist, a target repository is named, and the user has authorized writes to a scratch branch or worktree. It returns a patch confined to the authorized write set, verification results bound to the exact snapshot that was tested, an independent audit of those results from a fresh review context, and a handoff that states what is built, what was observed and what remains unproven. It never merges into a protected branch, deploys or publishes.

Entry skill `aipt-build-prototype` · Manager `engineering-manager` · Minimum risk R1 · Core cross-host release test yes

## Purpose and outcome

Use this workflow when a bounded change must exist as working code before anyone can judge it: a prototype of the Reply Assist draft-only reply path at Larkspur Support, a workspace scope filter between ws-alpha and ws-beta, or a harness that exercises a designed component. The outcome is not "the feature is done". The outcome is an implemented, audited, honestly labeled state of a scratch tree: which requirements the patch claims to implement, which checks ran with receipts, which checks were never executed, and whether the approved code state and the tested code state are the same version.

Three properties define a successful run. The builder never approves its own work. A check that was not executed is reported as `not_run`, never as passed. The version the manager accepted for integration is the version the auditor reproduced checks against, or the run says so and stays open.

## Inputs

The user supplies:
- Accepted scope: the `requirement` version ids (status `approved`) that bound the prototype, or a pointer to the `shape-feature` run that produced them. Protected requirements are listed explicitly.
- Architecture: the `architecture.md` artifact version from `design-system`, or a user-supplied design note registered as a `source`.
- Target repository: an authorized root inside the case `source_scope`, the branch or worktree the builder may use, and the commands the user expects to work.
- Write authorization: an `approval` record whose `allowed_actions` cover `assigned-worktree` writes under named `output_paths`, bound to the requirement versions. The controller records provenance; an unattested approval limits the run to proposal-only output.

The case must already contain the approved requirements, the source scope with the repository root, and the protected constraints from `case init`. A `shape-feature` acceptance map is used when present; when absent, `acceptance-designer` joins as a conditional specialist.

When something is missing, the run returns `needs_input` and retains progress:
- No approved requirements: "Which requirement versions define the bounded prototype? Supply version ids, or run shape-feature first."
- No architecture: "No accepted architecture is in the case. Supply a design note to register as a source, or run design-system before building."
- No repository root in source scope: "Which repository root may the builder read, and which paths may it write? Give the absolute root and the branch or worktree name."
- No write authorization: "Writes require an approval record bound to the requirement versions. Record one with `aipt decision record-user-input`, or ask for a proposal-only plan instead."
- A required command is unavailable on the host: the task returns `blocked`, and the runnable instruction is preserved in the handoff.

## Outputs

| Artifact | Shape | Stored as |
|---|---|---|
| `repository-map.md` | Headings: Entry points · Commands observed · Dependencies · Protected paths · Target snapshot · Unknowns. Each command carries a `receipt_id` or the label `read_only_observation`. | `artifact` node, kind `repository-map`, status `proposed` |
| `work-orders.json` | `{target_snapshot, work_orders: [{id, objective, requirement_refs, write_set, depends_on, checks: [{id, command, expected}], risk_tier, acceptance}], out_of_scope: []}` | `artifact` node, kind `work-orders`, status `proposed` |
| `patch.diff` | Unified diff restricted to the work order `write_set`; a build-notes trailer lists every mock and stub by name. | `artifact` node, kind `patch`, status `implemented_not_verified`; `implements` edges proposed to requirement versions |
| `verification-results.json` | `{snapshot, checks: [{id, kind: positive/negative/boundary/regression, command, receipt_id, result: passed/failed/blocked/not_run, test_ids}], limitations}` | `artifact` node plus one `validation` record per check; a result other than `not_run` requires a `receipt_id` |
| `engineering-review.json` | `review` fields `reviewed_refs, reviewer_role, reviewer_session, findings, evidence_sufficiency, result: ready/revise/blocked/escalate, conflict_check, unresolved`, plus `integration_order` and `integrated_snapshot` | `review` node via `aipt review submit` |
| `audit.json` | `review` fields plus `audited_snapshot`, `reproductions: [{check_id, receipt_id, result}]`, `verdict: pass/fail/blocked`, `conflict_check: verified/unverified/conflict` | `review` node; the independence gate is met only when `conflict_check=verified` |
| `handoff.md` | Headings: Run summary · What was built · Checks executed · Not run or blocked · Setup steps · Remaining failures · Readiness claim · Next action. | `artifact` node, kind `handoff`, derived from recorded state |

The registry outputs map as follows: implemented prototype is `patch.diff`; observed test receipts are `verification-results.json` with its receipts; independent audit is `audit.json`; handoff is `handoff.md`.

## Work graph

| Stage id | Role | Depends on | Conditional predicate | Artifact | Review / independence | Write scope |
|---|---|---|---|---|---|---|
| `map` | `repository-mapper` | — | — | `repository-map.md` | — | proposal-only |
| `plan` | `implementation-planner` | `map` | — | `work-orders.json` | — | proposal-only |
| `build` | `prototype-engineer` | `plan` | — | `patch.diff` | — | assigned-worktree |
| `check` | `test-engineer` | `build` | — | `verification-results.json` | — | proposal-only; tests arrive as a proposed patch, commands run through receipts |
| `review-integration` | `engineering-manager` | `check` | — | `engineering-review.json` | review | proposal-only |
| `audit` | `independent-auditor` | `review-integration` | — | `audit.json` | review · independence required | proposal-only |
| `handoff` | `workflow-orchestrator` | `audit` | — | `handoff.md` | — | proposal-only |

`build` expands to one task per work order. Work orders with disjoint write sets run in parallel up to the mode's concurrency; two tasks never share a target file. Test authoring inside `check` may begin once `plan` is accepted, but test execution depends on the `build` task it checks. Every other edge follows stage order. Conditional specialists attach as extra tasks under the stage they serve.

## Stage procedures

### `map` — repository-mapper
Read `agents/repository-mapper.md`. Apply `aipt-method-corpus-grounded-onboarding` to build a model of the repository that separates observed facts from inference, and `aipt-method-structural-integrity-audit` to flag duplicated or contradictory entry points. Input refs: the repository root from the case source scope, the accepted requirement versions, the architecture version. Follow execution paths from the actual entry points, run only read-only discovery commands through `aipt receipt run`, and record the target snapshot as a commit plus dirty-tree hash or a content manifest. Accepted when every command in the map has a receipt or is labeled as read from a manifest, protected paths are listed, and no script or entry point appears that does not exist in the tree.

### `plan` — implementation-planner
Read `agents/implementation-planner.md`. Apply `aipt-method-milestone-planning` to cut the scope into bounded work orders and `aipt-method-requirements-and-acceptance` to attach the observable check each order must produce. Input refs: `repository-map.md`, the requirement versions, the architecture version, the acceptance map when present. Each work order declares its write set under the authorized `output_paths`, its prerequisites, the exact check commands and the evidence expected. Unrelated cleanup goes under `out_of_scope`; it is not added to the order. Accepted when write sets are disjoint or ordered, every check names a command the map observed or a test the order will add, and no order touches a protected path without its risk tier raised to R2.

### `build` — prototype-engineer
Read `agents/prototype-engineer.md`. Apply `aipt-method-scoped-implementation` for the smallest safe diff, `aipt-method-requirements-and-acceptance` to keep the patch traceable to requirement ids, and `aipt-method-ai-responsibility-allocation` where the prototype decides what is fixed code and what is model inference. Input refs: one work order, the target snapshot, the architecture version. Work only in the assigned worktree; preserve existing behavior unless the order authorizes a change; name every mock or stub in the build notes. For Reply Assist, a mocked model response in the draft path is labeled `mock` and is never described as a live integration. Accepted when the diff stays inside the write set, `implements` links name requirement versions, and every `observed_checks` entry carries a receipt id or is listed as not run.

### `check` — test-engineer
Read `agents/test-engineer.md`. Apply `aipt-method-evaluation-execution-and-receipts` to run each check against the frozen snapshot through `aipt receipt run`, `aipt-method-requirements-and-acceptance` to cover positive, negative, boundary and regression cases, and `aipt-method-independent-audit` to judge results against the acceptance criteria rather than against the patch's intent. Input refs: the patch version, the work order checks, the acceptance map. New tests return as a proposed patch under `proposals/`. For the workspace filter, the negative case is a ws-alpha request that must not retrieve ws-beta documents. A failing test is reported as failed; instead of rewriting it to match the implementation, the engineer records the failure and requests a follow-up. Accepted when every check has a result, every result other than `not_run` cites a receipt, and limitations name the checks that could not run and why.

### `review-integration` — engineering-manager
Read `agents/engineering-manager.md`. Apply `aipt-method-independent-audit` to compare claimed and observed checks, `aipt-method-scoped-implementation` to reject edits outside the authorized change set, and `aipt-method-milestone-planning` to set the serial integration order. Input refs: all patch versions, `verification-results.json`, the work orders. The manager treats the builder's summary as a claim, identifies untested dependencies between patches, and integrates accepted patches one at a time into the scratch branch, recording the integrated snapshot. Accepted when `result` is `ready`, `revise`, `blocked` or `escalate` with findings tied to refs, and `integrated_snapshot` is recorded for the auditor.

### `audit` — independent-auditor
Read `agents/independent-auditor.md`. Apply `aipt-method-independent-audit` to reproduce the important checks in a fresh review context, `aipt-method-drift-and-regression-audit` to confirm the audited snapshot equals the integrated snapshot, and `aipt-method-requirements-and-acceptance` to check coverage against the acceptance map. Input refs: the integrated snapshot, `verification-results.json`, `engineering-review.json`, the requirement versions. The auditor never audits a patch it authored; the controller refuses that assignment at admission. A check it cannot run is `blocked`, not inferred from the builder's receipt. Accepted when `conflict_check` is `verified`, every reproduced check carries its own receipt, and the verdict separates pass, fail and blocked per check.

### `handoff` — workflow-orchestrator
Read `agents/workflow-orchestrator.md`. Apply `aipt-method-status-handoff` to derive the brief from recorded state and `aipt-method-delegated-authority` to phrase the readiness claim within what was authorized. Input refs: the run record, all accepted artifacts, the audit. The handoff lists setup steps that were observed to work, remaining failures with receipt ids, and an exact readiness claim such as "implemented and audited for R-12 and R-14 at snapshot `a1b2c3`; not evaluated against the product task; not reviewed for release". Accepted when every sentence in the handoff resolves to a recorded artifact, receipt or review.

## Gates

The run completes only when all of the following are true:
- Every non-conditional stage has an accepted task or a `satisfied_by_version_id` pointing at a current artifact.
- `review-integration` has a `review` node with `result` in `{ready, pass}`. This stage is a review gate.
- `audit` has a `review` node with `result` in `{ready, pass}` and `conflict_check=verified`. This stage is a review gate and an independence gate: the auditor's session differs from every author session of the audited patches.
- No `partial` outputs remain and no `needs_input` is open.
- `audited_snapshot` in `audit.json` equals `integrated_snapshot` in `engineering-review.json`.

Review and independence gates are never pruned, whatever artifacts already exist. If the host cannot provide a fresh review context, the audit records `independence_unverified` and the run stays blocked instead of completing.

Acceptance lines from the registry: No builder self-approval. Unexecuted checks remain untested. Approved code state and tested code state match.

## Routing and pruning

A stage is satisfied without a new task when a current, accepted artifact of its type exists for the same inputs: `map` when a `repository-map` is current for the same snapshot; `plan` when `work-orders` are current for the same requirement versions and snapshot; `build` only when a `patch` with status `verified_for_scope` already covers the requested scope, in which case the run narrows to re-check and audit; `check` when `validation` records are current for the snapshot under test. `handoff` is regenerated on every run because it is derived from state.

Conditional specialists join as extra tasks when a named condition holds:
- `integration-engineer` when two or more patches touch a shared interface, or when the integrated snapshot fails a check that each patch passed alone.
- `refactoring-engineer` when the planner records that a behavior-preserving restructure must precede the feature change; it gets its own work order with its own checks.
- `operations-engineer` when the prototype needs local runtime scaffolding (configuration, run scripts, logging) inside the authorized roots.
- `acceptance-designer` under `missing_current_artifact` for the acceptance map.
- `changes_protected_scope` raises the risk tier to R2 and routes the affected decision through `resolve-decision` before the build task is admitted.

A narrow request, such as "make the ws-alpha/ws-beta negative test pass", produces a narrow plan: `map` and `plan` are pruned when current, then one `build` task, one `check` task, the manager review and the audit. The gates stay; the discovery stages go.

Budget guidance: focused (4 tasks) fits only when `map` and `plan` are already current, leaving build, check, review and audit; standard (12 tasks) covers a typical prototype of one to three work orders with a rework round, usually 6 to 9 tasks; deep (24 tasks) is for a multi-component prototype or one carrying an R2 design question that needs a challenge round. The root orchestrator's handoff does not consume a worker slot. Every attempt and retry counts.

## Status handling and recovery

- `needs_input`: the task and the run move to `needs_input`; the exact question is preserved in the run record and shown to the user; accepted artifacts stay accepted; the run returns to `planned` once `aipt decision record-user-input` supplies the answer.
- `blocked`: the task records the unavailable capability or evidence (a test runner missing on the host, a snapshot that cannot be frozen, an auditor context that cannot be made fresh); independent tasks continue; the handoff lists the runnable instruction so a person can complete the step. The user receives the blocker, what was completed and the next resolving action.
- `failed`: receipts from the failed command are preserved; the controller investigates within the remaining budget and retries only within the work order's retry budget; a timeout is distinguished from a failing exit status.
- `partial`: completed work orders stay accepted and their patches remain integrated in the scratch branch; the run cannot complete while any output is partial; the handoff says which orders are done and which are not.
- Budget exhaustion: dispatch stops; the handoff summarizes accepted artifacts, receipts and open gates and asks for an explicit expansion of mode or scope. The run never switches to deep on its own and never drops the audit to fit the budget.
- Scope violation: a patch that touches a path outside its write set blocks the build task with the violations listed; the diff is not integrated.

In every case the user receives a packet: what is known, what was observed, what is blocked or missing, and the single next action.

## Authority boundary

This workflow never deploys, publishes, sends a message, pays, deletes data or merges into a protected branch. Writes happen only inside the assigned worktree under the authorized `output_paths`; everything else is a proposal. An accepted audit means the patch met its contract at one snapshot; it is not release readiness, which belongs to `review-release` (W09). A change that touches a protected requirement, authority rule, sensitive data flow or release criterion is R2: it needs `resolve-decision` (W11) and human acceptance before the protected behavior changes, and the acceptance binds the exact proposal hash. For Reply Assist, a work order that would let drafts be sent automatically is refused by the planner and recorded as an open authority question, however the request is phrased; the older slide saying "send automatically" is a source conflict, not an authorization. A manager's favorable review creates no authority: the Engineering Manager has `acceptance_authority: none`, and its `ready` result permits integration into the scratch branch and nothing more.

## Fixture

Scenario: A builder implements a scope filter and cites a test that was never executed. Expected behavior: the auditor returns `not_run` or `blocked` for that check, not `passed`; the controller has already flagged the builder's `observed_checks` entry without a `receipt_id` as `claimed_only`. After the test is executed through `aipt receipt run` and reproduced independently, the validation record is bound to the tested snapshot and the run can complete with the evidence pointing at that version.

Fixture path: `evals/workflows/build-prototype/fixture.json`. A replay of this fixture is labeled `fixture_replay` and is not a live run.

## Invocation

Entry skill: `aipt-build-prototype`, loaded in the root session only.

- `aipt run start --case CASE --workflow build-prototype --mode standard` records a run in state `created` then `scoped`, with the case, workflow version, mode, risk floor R1 and the host when observable.
- `aipt run plan --run RUN` records the route plan: selected and omitted roles with reasons, included stages, satisfied-by versions, evaluated predicates and the budget check; tasks enter `planned` and `ready`.
- `aipt task next --run RUN` lists the ready tasks whose dependencies are accepted, in dependency order.
- `aipt task admit --task TASK` runs the admission checks (dependencies, budget, write scope, snapshot, author-as-reviewer, source scope, wall clock) and mints the work order with a reserved slot.
- `aipt task attach --task TASK --native-child-id CHILD` records the native child identity and execution mode; without it, a native claim is downgraded to `sequential` with `observed_by=agent_reported`.
- `aipt task submit --task TASK --response response.json` validates the envelope, stores artifacts as proposed nodes, flags checks without receipts as `claimed_only` and moves the task to `submitted`.
- `aipt receipt run --task TASK -- <command>` executes a check and stores the receipt with command, working directory, snapshot, exit status and log locations.
- `aipt review submit --run RUN --record review.json` records the manager review or the audit with its conflict check; the controller refuses a reviewer who authored the artifact under review.
- `aipt decision propose --run RUN --record decision.json` records an R2 proposal for `resolve-decision`; `aipt decision record-user-input --run RUN --record user-input.json` records the user's answer or approval with `channel=cli` and `attested=false`.
- `aipt case report --case CASE --format markdown` renders the derived report, including implementation status and validation coverage with applicability.

## Live coverage

| Host | fixture_replay | native | Last run |
|---|---|---|---|
| first native host (see `docs/compatibility/`) | not yet run | not yet run | — |
| second native host (see `docs/compatibility/`) | not yet run | not yet run | — |
| fixture runner, no host | not yet run | — | — |

This table is updated only from recorded runs; no cell is inferred from parsed files or from a run on another host.
