# W03 · Design how this AI feature should work.

A team has accepted requirements for an AI feature and asks how it should work: which steps are fixed code, which use model inference, which investigate adaptively and which a person decides; what each tool looks like; what the feature may do and when it must stop; and, when the feature retrieves information, how it finds only what the requesting user may see. This workflow returns an architecture, tool and component contracts, a permission and failure policy and, when retrieval is part of the feature, a retrieval contract, each reviewed for invariants and failure behavior before any build begins.

Entry skill `aipt-design-system` · Manager `systems-manager` · Minimum risk R1 · Core cross-host release test no

## Purpose and outcome

W03 turns accepted requirements into a design that can be built in bounded pieces and checked against stated invariants. The outcome is a set of artifacts the case owner and W04 can rely on: `architecture.md`, `tool-contracts.json`, `authority-and-failure-policy.md` and, when `requires_retrieval` is true, `retrieval-contract.md`. Each permission or access decision in the design is allocated to fixed code or to a person, never to a model's judgment, and every component has a stated failure and recovery behavior.

The run completes when the included design stages are accepted and the Systems Manager's review record reads `ready`. Completion means the design is consistent with the requirements and its risks are stated; it does not authorize implementation, which is W04's job under its own write authorization, and it does not approve a release, which is W09's. W03 is not one of the six core cross-host release tests; its live coverage is reported exactly, in the last section.

Example. Reply Assist retrieves prior tickets and help articles whose access is specific to `ws-alpha` or `ws-beta`. A proposed design passes every candidate document to the model and instructs it to ignore text from other workspaces. W03's architecture rejects that allocation: authorization is a fixed-code filter applied before any text reaches the model, scope follows the text through summarization and caching, and the failure plan includes a negative test in which a `ws-alpha` request must surface nothing from `ws-beta`.

## Inputs

The user supplies three things: accepted requirements (a `requirements.json` version whose entries are `approved`, or an accepted W02 proposal the owner has designated), data and tool constraints (what data exists and under which access scopes, which tools exist and their documentation, what the host exposes), and repository context (a `repository-map.md` from an earlier W04 run or a read-only pointer to the target repository).

The case must already contain a case brief with protected constraints and a source scope, and the requirements the design must satisfy. Protected constraints (for Reply Assist: no send without a human action; no cross-workspace exposure) bind the design from the start.

| Missing | Behavior |
|---|---|
| Accepted requirements | `needs_input`: "Which requirements version should this design satisfy? Point at an accepted `requirements.json`, or run W02 first." |
| Tool documentation | Proceed with a limitation: contracts are written only for documented tools, and the rest are listed under `tools_undocumented` with the question to answer. |
| Access scopes for retrieved data | `needs_input` from the `retrieval` stage: "Which access scope applies to each source the feature retrieves, and who assigns it?" Retrieval is not designed on assumed scopes. |
| Repository context | Proceed as a design against a stated greenfield assumption; the review records that W04's `map` stage must run before any work order is issued. |
| Capability report | `blocked`: the design cannot bind tools to what the host supplies; the resolving action is `aipt doctor` for the target host. |

## Outputs

Architecture: `architecture.md`, headings `## Requirements addressed`, `## Steps and responsibility allocation` (per step: fixed code, model inference, adaptive investigation or human decision, with the reason), `## Components and interfaces`, `## Invariants`, `## Tradeoffs linked to requirements`, `## Unresolved design choices`. Stored as an `artifact` (status `proposed`) and as a `proposal` record whose `requested_authority` is R1, or R2 when the design touches a protected boundary.

Component contracts: `tool-contracts.json`, keys `tools` (each with `name`, `purpose`, `input_schema`, `result_schema`, `idempotency` as `{key, safe_to_retry}`, `timeout_s`, `errors` as `[{code, handling}]`, `side_effects`, `permission_required`, `proposed_vs_executed`), `non_idempotent_actions`, `tools_undocumented`. Stored as an `artifact`.

Permissions: `authority-and-failure-policy.md`, headings `## Permitted actions by actor`, `## Enforceable boundaries`, `## Instructions that only request compliance`, `## Escalation`, `## Budgets and termination`, `## Failure and recovery behavior`, `## Negative tests`. Stored as an `artifact`; each boundary the owner later accepts is proposed as a `requirement` record with `protected: true`.

Failure and evaluation plan: the `## Failure and recovery behavior` and `## Negative tests` sections of the policy together with the `## Failure tests` section of the retrieval contract. Each listed test is proposed as a `validation` record with result `not_run`, for W05 to freeze into an evaluation plan and W04 to execute.

Retrieval contract (conditional): `retrieval-contract.md`, headings `## Sources and access scopes`, `## Authorization before exposure`, `## Scope survival through transformation`, `## Freshness`, `## Context assembly`, `## Failure tests`. Stored as an `artifact`.

Review: `architecture-review.json`, keys `reviewed_refs`, `reviewer_role`, `reviewer_session`, `findings`, `evidence_sufficiency`, `result`, `conflict_check`, `unresolved`. Stored as a `review` record.

## Work graph

| Stage id | Role | Depends on | Conditional predicate | Artifact | Review / independence | Write scope |
|---|---|---|---|---|---|---|
| `allocate` | `workflow-architect` | — | — | `architecture.md` | no / no | proposal-only |
| `specify-tools` | `tool-integration-designer` | `allocate` | — | `tool-contracts.json` | no / no | proposal-only |
| `constrain-authority` | `safety-boundary-designer` | `allocate`, `specify-tools` | — | `authority-and-failure-policy.md` | no / no | proposal-only |
| `retrieval` | `retrieval-designer` | `allocate` | `requires_retrieval` | `retrieval-contract.md` | no / no | proposal-only |
| `review` | `systems-manager` | every included stage | — | `architecture-review.json` | review gate / manager review, `independent=false` | proposal-only |

`specify-tools` and `retrieval` both depend only on `allocate` and run in parallel within the mode's worker limit. `constrain-authority` follows `specify-tools` because it binds each tool action to a permission and an actor. `review` waits for every included stage.

## Stage procedures

### allocate

The Workflow Architect (`agents/workflow-architect.md`) applies `aipt-method-ai-responsibility-allocation` to decide, for each step of the accepted journey, whether fixed code, model inference, adaptive investigation or a human decision is responsible, with a stated reason for every adaptive choice; `aipt-method-tool-and-permission-boundaries` to place the boundary between proposing and executing; and `aipt-method-milestone-planning` to order components into units W04 can build and check separately. A deterministic permission check is never reallocated to model judgment. Input refs: the accepted requirements version, the journey, the data and tool constraints, the repository context. Acceptance: every step has an allocation and a reason, every tradeoff names a requirement id, invariants are listed, and unresolved design choices are explicit rather than silently decided.

### specify-tools

The Tool Integration Designer (`agents/tool-integration-designer.md`) applies `aipt-method-tool-and-permission-boundaries` and `aipt-method-ai-responsibility-allocation` to write one contract per tool the architecture calls: typed inputs and results, an idempotency key and whether a retry is safe, a timeout, error codes with the handling for each, side effects and the permission the call requires. Proposed tool actions are separated from executed ones and bound to explicit identifiers and versions; a non-idempotent external action (for Reply Assist, anything that would send) is listed under `non_idempotent_actions` and never retried blindly. Input refs: the accepted architecture, the tool documentation in scope. Acceptance: every tool named in the architecture has a contract or appears under `tools_undocumented`, every contract has a timeout and an error table, and every side-effecting call names its permission.

### constrain-authority

The Safety Boundary Designer (`agents/safety-boundary-designer.md`) applies `aipt-method-tool-and-permission-boundaries` to bind each executable action to a permission and an actor, `aipt-method-security-and-privacy-review` to inspect trust boundaries and data scope inheritance, and `aipt-method-ai-responsibility-allocation` to confirm that stop conditions sit in code. It separates enforceable boundaries (code-level filters, allowlists, host permissions) from instructions that only request compliance (prompt text), and never presents a written rule as a sandbox. It specifies escalation paths, step and time budgets (with cost recorded as unknown where the host exposes none), termination conditions and the recovery behavior for each failure class. Input refs: the accepted architecture and tool contracts, the protected constraints. Acceptance: every action in the tool contracts appears under `## Permitted actions by actor`, every boundary is classified enforceable or requested, every component has a failure class with a recovery action, and each protected constraint has a negative test.

### retrieval

This stage runs only when `requires_retrieval` is true. The Retrieval Designer (`agents/retrieval-designer.md`) applies `aipt-method-retrieval-and-context-contracts` to specify source acquisition, access filtering before any text is exposed to the model, scope that survives summarization, embedding and caching, freshness rules and context assembly; `aipt-method-tool-and-permission-boundaries` for the retrieval tool's contract; and `aipt-method-security-and-privacy-review` for the failure tests, including a negative cross-scope access test. It rejects any design that relies on the prompt to hide already-retrieved unauthorized text. Input refs: the accepted architecture, the sources and their access scopes. Acceptance: authorization is placed before exposure in every path, every transformed form inherits the scope of its origin, and `## Failure tests` includes a negative access case per scope boundary.

### review

The Systems Manager (`agents/systems-manager.md`) applies `aipt-method-structural-integrity-audit`, `aipt-method-ai-responsibility-allocation` and `aipt-method-tool-and-permission-boundaries` to review guarantees, dependencies and failure behavior before component counts: does the design cover every requirement, hold its invariants, specify every failure case and name its unresolved choices? An agent loop without termination or permission boundaries comes back as `revise`. It returns a `review` record with `result` in `ready`, `revise`, `blocked` or `escalate`, and targeted revisions as work orders. The manager leads the authoring team, so the record carries `independent=false`. Input refs: every accepted design artifact and the requirements they claim to address. Acceptance: a result is recorded, each finding points at a ref, and every unresolved design choice appears in `unresolved`.

## Gates

The run can complete only when:

- `allocate`, `specify-tools` and `constrain-authority` each have an `accepted` task or a `satisfied_by_version_id` pointing at a current accepted artifact.
- When `requires_retrieval` is true, `retrieval` is `accepted` or satisfied; a pruned retrieval stage is recorded with the version it reuses.
- `review` has a `review` record with `result` in {`ready`, `pass`}. This is the workflow's review gate.
- No task is in `needs_input`, no output is `partial`, and the mode's wall-clock limit has not passed.

W03 has one review gate, `review`, and no stage requiring independence at R1. When the design touches a protected boundary (workspace isolation, who may send, what data a tool may read), `changes_protected_scope` raises the run to R2: the architecture becomes a proposal for W11, an independent review is required, and attested human acceptance precedes any change to a protected requirement. Review and independence gates are never pruned, whatever artifacts already exist.

The registry's acceptance lines, and what each means at the gate: "Deterministic authority stays outside model judgment" means every permission, access or send decision in the architecture is allocated to fixed code or a human, never to model inference. "Failure and recovery behavior specified" means every component in `architecture.md` has a failure class and a recovery action in the policy. "Architecture tradeoffs linked to requirements" means every entry under `## Tradeoffs linked to requirements` names a requirement id that exists in the accepted version.

## Routing and pruning

A stage is satisfied when a current accepted artifact of its kind exists for the same requirements version. An `architecture.md` accepted against the same requirements prunes `allocate`; a `tool-contracts.json` whose tools match the architecture prunes `specify-tools`; a `retrieval-contract.md` whose sources and scopes are unchanged prunes `retrieval`. A changed requirements version invalidates all of them. The route plan records each as `satisfied_by_version_id`. The `review` stage is never pruned; reused artifacts still receive a fresh review.

Conditional specialists join under these conditions. The Retrieval Designer joins when `requires_retrieval` is true, as the `retrieval` stage. The Model Selection Analyst joins when a requirement constrains latency, quality or availability so that model choice becomes a design decision, or when the user asks; it reads dated facts from `policies/` and embeds none in the design. The Security Reviewer joins when `changes_protected_scope` is true or the design has an injection or data-exposure surface, as a review criterion at R2. The Privacy Reviewer joins when retrieved content, logs or evaluation data include personal data. The Engineering Director joins only when an R2 architecture crosses team boundaries or the Systems Manager escalates.

A narrow request produces a narrow plan. "Write the tool contract for the ticket lookup" yields `tool-integration-designer` alone. "Does this prompt enforce workspace isolation?" yields `safety-boundary-designer` and `security-reviewer`, with no director or judge.

Budget modes: `focused` (4 tasks, 2 concurrent, 0 challenge rounds) fits exactly the three unconditional stages and the review, with no retrieval, no specialists and no retries; `standard` (12 tasks, 3 concurrent, 1 round) is the default and fits the five stages plus two specialists, one rework and one W11 round; `deep` (24 tasks, 3 concurrent, 2 rounds) is for an explicitly requested cross-team design. Typical task counts: 4 in focused, 5 to 9 in standard, 10 to 14 in deep. Every attempt and retry counts; the root orchestrator does not.

## Status handling and recovery

`needs_input`: the question (which requirements version, which access scope) is preserved verbatim and the run moves to `needs_input`; accepted artifacts are kept. The user receives the exact question and the design decision it unblocks. The answer is recorded with `aipt decision record-user-input`, the run returns to `planned`, and the waiting stage is re-planned with the answer as an input ref.

`blocked`: a tool's documentation or the capability report is unavailable, or a source's scope cannot be determined. The task records the unavailable item, and independent stages continue; `constrain-authority` can proceed for documented tools while the undocumented one is listed. The user receives the unavailable capability or evidence and the resolving action.

`failed`: the partial response and any receipts are preserved; the orchestrator investigates within the remaining budget and retries only inside the work order's retry budget. Each attempt counts as a task.

`partial`: a design artifact that covers part of its scope (contracts for some tools, a policy without a failure class for one component) is stored, and the run stays in `reviewing` until the gap is closed or the review records it as a stated limitation. The user receives what is covered and what is not.

Budget exhaustion: admission is refused with `BudgetExhausted`. The user receives the accepted artifacts, the stages not yet run and a specific request to expand the mode or task count. The run never moves to `deep` on its own and never drops the review to fit. A W11 challenge triggered by an R2 boundary change that does not fit the budget requires explicit replanning or human approval to expand it.

In every case the packet says what is known, what is not, and the next resolving action.

## Authority boundary

W03 designs and never deploys, publishes, sends, pays, deletes or broadens access. It reads repository context and writes only under `proposals/`; it never edits the target repository, and a design that mentions a tool does not call it. Its minimum risk is R1 because its outputs shape a bounded local change; it executes none.

Permissions written in `authority-and-failure-policy.md` are proposals. They become protected requirements only when the human owner accepts them through W11 with attested input, which the CLI cannot supply (`attested=false`). A design that loosens a protected boundary is an R2 proposal and cannot be accepted by the Decision Authority alone. The Systems Manager's `ready` says the design is sound and complete; it grants no authority to build, which requires W04 with recorded write authorization, and none to release, which requires W09 and human acceptance.

## Fixture

Scenario: "Retrieved documents have workspace-specific access, and the proposed prompt tells the model to hide unauthorized text." Expected behavior: "The architecture rejects prompt-only isolation and specifies pre-exposure filtering plus a negative access test."

In the Larkspur Support case Reply Assist retrieves tickets and articles scoped to `ws-alpha` or `ws-beta`, and the supplied design asks the model to ignore the other workspace. The expected run allocates the access check to fixed code before retrieval results reach the model, writes a retrieval contract in which every summary and cache entry inherits the scope of its source, classifies the prompt instruction as a request for compliance rather than an enforceable boundary, and adds a negative test: a `ws-alpha` request against a corpus containing `ws-beta` documents must return no `ws-beta` text, with the check recorded as `not_run` until W04 executes it. The review returns `ready` with the test listed under unresolved evidence.

Fixture path: `evals/workflows/design-system/fixture.json`. A replay of this fixture is labeled `fixture_replay` and is not a live run; it checks the controller's transitions with predetermined outputs and demonstrates nothing about a model's judgment or a host's execution.

## Invocation

The entry skill is `aipt-design-system`. It loads the orchestration contract into the current root session and never runs in a forked context.

- `aipt run start --case CASE --workflow design-system --mode standard` creates the run, binds it to the case, the workflow version and the mode, sets the risk floor to R1, and moves it from `created` to `scoped`.
- `aipt run plan --run RUN_ID` records the route plan: whether `requires_retrieval` included the `retrieval` stage, which stages are satisfied by current artifacts, omitted roles with reasons, and the budget check.
- `aipt task next --run RUN_ID` lists the ready tasks in dependency order: `allocate` first, then `specify-tools` and `retrieval` together.
- `aipt task admit --task TASK_ID` runs the admission checks (dependencies, budget, role and write scope, source permissions, wall clock), reserves a slot and mints the work order.
- `aipt task attach --task TASK_ID --native-child-id CHILD_ID` records the native child that executes the task; without it, a response claiming `native` is stored as `sequential` with `claimed_native_unobserved=true`.
- `aipt task submit --task TASK_ID --response response.json` validates the agent response, stores the design artifact as `proposed`, stores proposed validations and links as proposed records and edges, and preserves any `needs_input` question.
- `aipt review submit --run RUN_ID --record review.json` records the Systems Manager's review with its result and conflict check; the author of a reviewed artifact is refused as its reviewer.
- `aipt decision propose --run RUN_ID --record decision.json` records the architecture's `requested_authority` as a proposed decision for W11 when the design touches a protected boundary.
- `aipt decision record-user-input --run RUN_ID --record user-input.json` records the owner's answer or acceptance with channel `cli` and `attested=false`; it resolves `needs_input` and cannot complete a protected transition.
- `aipt case report --case CASE --format markdown` renders the derived report: objective, requirements addressed, active decisions, validation coverage (every design test still `not_run`) and the next action.

## Live coverage

| Host | fixture_replay | native | Last run |
|---|---|---|---|
| native host 1 (adapter record in `docs/compatibility/`) | not yet run | not yet run | — |
| native host 2 (adapter record in `docs/compatibility/`) | not yet run | not yet run | — |
| sequential fallback (no native dispatch) | not yet run | — | — |

This table is updated only from recorded runs: a `fixture_replay` result from `aipt eval fixtures`, or a native run whose dispatch rows carry a recorded child id. No cell changes on the basis of a description, a parsed file or a self-report.
