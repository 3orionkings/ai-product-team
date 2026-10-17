# AI Product Team — full architecture design

**Version:** 0.1 • **Date:** 16 October 2026 • **Status:** proposed implementation specification

**Owner:** Emmanuel Benami. **Provisional repository:** `ai-product-team`. **Proposed Python package:** `ai_product_team`. **Proposed command:** `aipt`.

This design describes a system to build. It does not claim the agents, adapters, controller, evaluation results or security properties have already been implemented. Existing material is identified in `05_LOCAL_SOURCE_MAP.private.md`; the 64 roles are specified in `03_AGENT_DIRECTORY.md` and `registry/agents.json`. Normative product requirements are in `01_INITIAL_PRD.md`.

## 1. Product boundary and architectural proposition

The product is a provider-neutral organization of specialists for investigating, designing, building, evaluating and improving AI features. Its interface is a request in an existing coding assistant, supported by ordinary local files and a small controller. The user supplies authorized evidence, requirements or a repository. The team activates only the roles needed to produce the requested outcome.

The central mechanism is preservation of the relationship between **sources, claims, decisions, requirements, implementation versions, checks, findings and subsequent changes**. A specialist contributes a bounded output to that chain. A manager reviews its completeness. A challenger can attack a consequential premise. A judge can determine what the evidence establishes and what remains unresolved. The Decision Authority can accept a choice only within recorded human delegation. A deterministic controller checks the recorded transition's structural and policy preconditions.

The organization contains **64 agents: three directors, one root workflow orchestrator, and ten teams of six**. The hierarchy allocates responsibilities; it does not impose a fixed invocation ladder. A brief research task may use two specialists and one reviewer. A complex feature can traverse several teams in stages. Directors become active for cross-team choices, unresolved conflicts, material changes of scope or requested strategic direction.

Initial support means native use in **Codex and Claude Code**, with one canonical role/skill library and host-specific adapters. It does not mean identical models, identical tool permissions, automatic provider switching, or support for every product carrying those provider names.

### 1.1 What the system builds itself

- Canonical agent contracts, shared skills, workflow recipes and policy definitions.
- A local state controller that validates records, schedules eligible work orders, tracks versions and generates reports.
- An adapter compiler, safe repository-scoped installer and compatibility checker.
- A versioned evidence/dependency ledger, review/decision protocol and change-impact process.
- A synthetic demonstration application, reproducible tests and explicitly labeled evaluation artifacts.

### 1.2 What the host supplies

The host supplies model execution, native delegation, filesystem and shell tools, user permissions, and any connected retrieval or browser tools. The first release does not implement its own inference server, hosted queue, token billing, vector database, autonomous daemon or cross-provider RPC bridge. The controller emits work orders; the root assistant performs native dispatch.

### 1.3 What is outside the initial execution boundary

Live deployment, external message sending, payments, production database mutation, public repository publication and secret provisioning are not autonomous v0.1 actions. The team may prepare a release plan or recommend an action. It must return an explicit human action request where execution lies outside the supported boundary.

No design in this package licenses use of the owner's unrelated private project material, private run logs, client work, employer-confidential sources or unresolved third-party adaptations.

## 2. Architecture at a glance

```text
HUMAN OWNER
  purpose | authorized sources | protected constraints | delegation | budget
       |
       v
NATIVE HOST SESSION: CODEX OR CLAUDE CODE
  Root Workflow Orchestrator
       |                         |
       | native dispatch         | controller commands / structured responses
       v                         v
  SELECTED AGENTS            LOCAL CONTROLLER
  Directors                 schema + transition validation
  Team managers             task admission + budgets + version checks
  Specialists               evidence/dependency graph + impact queue
  Challengers               conflict/approval eligibility checks
  Judges                    run journal + status/readable reports
  Decision Authority              |
       |                          v
       | proposals / receipts   PROJECT CASE STORE
       +---------------------> SQLite canonical state + immutable blob versions
                                  |
                                  v
                            derived Markdown / JSON / HTML reports

CANONICAL PACKAGE                    GENERATED HOST ADAPTERS
registry + roles + skills   ------>  .claude/agents + .claude/skills
workflow recipes + policies         .codex/agents + .agents/skills
schemas + templates                  namespaced, repository-scoped, versioned
```

The controller never decides whether a source is persuasive. It checks that a claim has an assessment, that required evidence references resolve, that an approval refers to the right version and that a forbidden transition is rejected. Semantic review remains an explicit agent or human judgment. Missing dependency links remain a possible source of missed change impact.

## 3. Organization and responsibility boundaries

### 3.1 Reporting structure

| Director | Managers led | Scope |
|---|---|---|
| Product Director | Discovery Manager; Research Manager; Experience Manager | Customer problem, evidence, product scope and experience. |
| Engineering Director | Systems Manager; Engineering Manager; Evaluation Manager; Operations Manager | Technical choices, implementation, verification design and operational tradeoffs. |
| Assurance Director | Adversarial Orchestrator; Review Manager; Audit Manager | Independent challenge, fair adjudication, decision-process integrity and assurance. |

The Workflow Orchestrator is accountable to the human owner and coordinates work across these groups. The human owner is not an agent and is not included in the count.

Managers produce review verdicts and requested follow-up work. Directors arbitrate cross-team direction within the human objective. Neither acquires new execution permission through its title. A director's preferred option cannot change a protected constraint, suppress a failed test or erase dissent.

Decision Authority sits administratively in the Decision and Convergence team. Its substantive authority comes from the human delegation record, not from the Review Manager or Assurance Director. A human decision can supersede an earlier delegated decision, but the record must retain the superseded decision and its evidence.

### 3.2 Why separate roles exist

The complete catalog is in `03_AGENT_DIRECTORY.md`. Adjacent roles have distinct contracts:

- **Evidence Linker:** source-to-claim support and initial dependency proposals.
- **Dependency Steward:** decision-to-requirement-to-implementation-to-check coverage.
- **Change Impact Analyst:** implications of a particular new fact, source revision or artifact change.
- **Decision Recorder:** exact approved option, authority, evidence and revisit conditions.
- **Learning Steward:** candidate process or skill improvements supported by observed outcomes.

Claim Checker examines passage-level support. Evidence Judge adjudicates disputed sufficiency. Convergence Judge compares admissible alternatives against shared criteria. Decision Authority applies delegated acceptance rights. Independent Auditor reproduces delivery checks. Separate names are insufficient to establish independence: attribution, session identity, artifact versions and review assignments must be recorded.

### 3.3 Manager contract

Every team manager must return:

1. A bounded assessment of the relevant output against its actual criteria.
2. `ready`, `revise`, `blocked` or `escalate`, with a reason and supporting references.
3. Specific gaps and the next resolving task, rather than generic advice to do more work.
4. Proposed specialist assignments with inputs, outputs, dependencies and budget.
5. A list of changes requiring another team or human authority.

Managers cannot mark tests passed, claim to have executed a specialist's unrun command, or accept their own unreviewed work as independently verified.

### 3.4 Logical hierarchy, flat portable dispatch

The root session is the only dispatcher in the baseline. A director or manager can return a delegation plan, but does not recursively start children. This keeps host-specific nesting behavior out of the core contract and lets the same organization run on hosts with different delegation limits.

The general `aipt-start` skill and twelve workflow entry skills load the orchestration contract into the current root session. These thirteen entry wrappers are separate from the 28 shared method skills. If the Workflow Orchestrator role is invoked as a child, it returns a route proposal and cannot dispatch grandchildren. Native role metadata must not be mistaken for proof that the caller is the root session.

A director does not have to be invoked merely because one of its specialists is used. A manager does not need a new model call to restate an already accepted, current review. The controller prunes satisfied prerequisites, while retaining required independence and authority gates.

An optional future nested adapter may be added after equivalent routing, budget and review behavior is tested. It must not silently replace the portable baseline.

## 4. Canonical package and installed layout

```text
ai-product-team/
  README.md
  AGENTS.md                         # builder/development guidance for this package
  CLAUDE.md                         # small development wrapper, not 64 role prompts
  pyproject.toml
  LICENSE                           # only for cleared/newly authored material
  THIRD_PARTY_NOTICES.md
  registry/
    agents.json                     # 64 role contracts; source of truth for metadata
    skills.json                     # 28 shared skill targets and provenance IDs
    workflows.json                  # 12 workflow entry points and routing metadata
    sources.public.json             # sanitized provenance, no personal paths
  agents/<agent-id>.md              # full, bounded role instructions
  skills/<skill-name>/SKILL.md       # shared methods + relevant references/examples
  workflows/<workflow-name>.md      # complete procedures, gates and recovery
  policies/
    authority.json
    risk.json
    budgets.json
    review-independence.json
    data-handling.json
  schemas/                          # versioned, strict JSON Schema contracts
  src/ai_product_team/
    cli.py
    registry.py
    controller.py
    storage.py
    routing.py
    lineage.py
    decisions.py
    receipts.py
    reporting.py
    adapter_compiler.py
    installer.py
    doctor.py
  adapters/
    claude/                         # templates + verified capability declarations
    codex/
  templates/
  examples/support-copilot/          # synthetic application and scripted scenarios
  tests/{unit,contracts,integration,adapters,fixtures}/
  evals/{roles,workflows,comparisons}/
  docs/{architecture,usage,contributing,security,compatibility}/
  tools/
  dist/                             # generated export; ignored except release artifacts
```

A target project is different from the package repository. A repository-scoped installation places a namespaced, versioned package copy under `.aipt/package/`, generated registrations in the host's native locations, and runtime state under `.aipt/cases/<case-id>/`.

```text
target-project/
  .aipt/
    package/<package-version>/       # immutable installed role and skill material
    install-manifest.json            # paths + hashes + ownership for upgrade/removal
    policy.json                      # user-approved project policy
    cases/<case-id>/
      state.sqlite3                  # authoritative runtime records, gitignored
      blobs/<sha256>                 # immutable authorized input/output versions
      receipts/                      # raw logs and execution metadata, gitignored
      proposals/                     # worker submissions, not accepted truth
      reports/                       # generated current views
      exports/                       # explicit portable export, private by default
  .claude/agents/aipt-*.md            # generated Claude definitions
  .claude/skills/aipt-*/SKILL.md
  .codex/agents/aipt-*.toml            # generated Codex definitions
  .agents/skills/aipt-*/SKILL.md
```

Install all role registrations only after the user chooses that package scope. Generate small names/descriptions and role bodies that load shared content selectively; do not inject the full organization into root instructions. Reuse existing project guidance without replacing it. Conflicts require a diff and a user decision.

The package itself must not contain personal source paths or the private build prompt. Sanitized public documentation is generated deliberately from selected material, not by copying this whole planning pack into the public repo.

## 5. Runtime components

### 5.1 Registry loader

Loads canonical agent, skill and workflow metadata. It verifies unique IDs, existing references, the reporting tree, allowed role types and assigned review relationships. Unknown roles, missing skill bodies and circular management relationships fail validation. A role is never considered implemented merely because its JSON metadata exists.

### 5.2 Workflow router

Classifies intent from the user's request and available case state. It proposes the lowest-complexity workflow and explains the selected roles. Deterministic checks then validate its role IDs, prerequisites, risk tier, budget and authority requirements.

A user may explicitly select a workflow or specialist. A direct specialist call must still respect data scope and action permissions. It does not have to generate the artifacts of an unrelated full workflow.

### 5.3 Work-order controller

Issues bounded tasks with input references, expected output contract, target version, budget, write scope and return conditions. Records the actual native child ID if a child is spawned. A proposed child name or a convincing final response is insufficient evidence of native delegation.

### 5.4 Evidence and dependency service

Stores typed, versioned records and relations. Resolves references, records source scope, computes deterministic impact over declared dependencies and queues semantic review where necessary. It does not invent support edges or automatically resolve contradictions.

### 5.5 Review and decision service

Validates review eligibility, version bindings, objection status, delegation limits and approval prerequisites. It separates a recommendation, a judge's ruling, a recorded decision and an executed action. Protected authority is never inferred from role names or a manager's review.

### 5.6 Execution receipt collector

Captures command, working directory, target snapshot, relevant inputs, environment details, start/end time, exit status and log locations. Test validity depends on the real artifacts exercised and the test's coverage. A successful shell exit does not prove requirement coverage.

### 5.7 Adapter compiler and installer

Compiles neutral roles into the current documented host registration format. Installs only namespaced owned files, with dry-run, backup, conflict detection, atomic replacement and hash-aware uninstall. It does not run the older audited installer unchanged, because that script's overwrite behavior was explicitly flagged.

### 5.8 Reports and handoff

Produces a concise case brief, active decisions, unresolved conflicts, acceptance matrix, change queue, runtime status and actual execution/compatibility labels. Reports are derived; editing a report cannot change authoritative state.

## 6. Data model and authority of records

Use **SQLite on a local filesystem** for authoritative runtime state and content-addressed files for larger immutable input/output versions. JSON and Markdown are export/report formats. Do not maintain independent canonical JSON, Markdown and SQLite records that can silently diverge.

The initial controller can use Python 3.11+ and its standard library. Keep any schema-validation, YAML parsing or test dependencies small, declared and license-reviewed. Do not handwrite a general YAML parser. Canonical metadata can remain JSON; the compiler can emit minimal host frontmatter and test it with an independent parser.

### 6.1 Core entities

| Entity | Required meaning and fields |
|---|---|
| Project / Case | `id`, authorized roots and source scope, objective, protected constraints, owner, current policy version, retention policy. |
| Run | `run_id`, case, workflow version, package version, host and version, model if observable, risk, budget, state, mode, start/end, actual dispatch records. |
| Task | `task_id`, role, input node versions, expected output type, dependencies, snapshot, write scope, limits, review requirement, state. |
| Source | stable ID + immutable version, local/public locator, retrieval/observation time, content hash, access scope, authority/type and limitations. |
| Claim | exact statement, type (`fact`, `hypothesis`, `observation`), supporting/contrary references, confidence label, validity status and assessment author. |
| Requirement | statement, owner, acceptance criteria, protected flag, originating decision/source, approved version and implementation/check links. |
| Proposal | options, recommended option, assumptions, evidence, constraints, unresolved questions, target version, author/session and requested authority. |
| Decision | exact proposal version, selected option or defer/reject, criteria, rationale summary, dissent, delegation/approval basis, expiry/revisit conditions. |
| Artifact | kind, immutable version, snapshot/hash, producer/task, write scope, requirements claimed to be implemented, provenance and access classification. |
| Validation | method, tested target/config/dataset/skill versions, actual receipt, observed result, rubric, coverage and applicability to current target. |
| Challenge | contested claim/option, counterevidence, material consequence, resolving test, proposer independence and resolution state. |
| Review / Judgment | reviewer identity/session, assessed versions, findings, evidence sufficiency, result, conflict-of-interest check and unresolved matters. |
| Approval / Delegation | granting authority, scope, allowed decisions/actions, bound version/hash, limits, expiry/revocation and provenance of human input. |
| Event | immutable sequence, event ID, type, actor/session, expected previous state version, payload references, timestamp and idempotency key. |

Do not record hidden model reasoning. Retain concise decision rationales, cited evidence, rejected alternatives, limitations and observable execution facts.

### 6.2 Proposed relational tables

`cases`, `runs`, `tasks`, `dispatches`, `nodes`, `node_versions`, `edges`, `proposals`, `reviews`, `decisions`, `approvals`, `validations`, `receipts`, `challenges`, `events`, `impact_queue`, `budgets`, `installation_manifests`.

`node_versions` is immutable. A separate current-state projection points at the current version and its applicability/status. Relationships reference immutable versions, not just a mutable filename. Events update projections transactionally; historical records are not rewritten to make a later outcome look inevitable.

### 6.3 Relations and direction

Semantic relations include `supports`, `contradicts`, `implements`, `verifies`, `derived_from` and `supersedes`. These describe meaning; they do not all have the same change-propagation behavior.

For deterministic impact, use an explicit relation:

`dependent-version --depends_on--> dependency-version`

Each dependency declares `impact_policy: review | invalidate_applicability | none` and a reason. A reverse traversal from an accepted changed dependency produces the affected set. A source may support multiple claims; a decision may depend on several claims; an implementation may depend on a design choice; a validation depends on the exact target and relevant test/data/configuration versions.

A `contradicts` edge does not automatically establish that the old claim is false. A new contradiction first creates a contested assessment and a review task. The controller applies an accepted correction event after the designated review. Protected requirements are never removed just because evidence shows that their implementation fails.

### 6.4 Status separation

- **Claims:** proposed, supported, contested, unsupported, superseded. A hypothesis does not become a fact from repetition alone.
- **Decisions:** proposed, under_review, accepted, rejected, deferred, human_required, review_required, superseded.
- **Artifacts:** proposed, implemented_not_verified, verified_for_scope, changes_required, revalidation_required, archived.
- **Validation result:** passed, failed, blocked, not_run. Separately store applicability: current, historical, invalidated.
- **Requirements:** proposed, approved, retired, superseded. Verification coverage is separate from the requirement's validity.

When code changes after a successful test, the old test result remains a historical pass. Its applicability to the new code becomes unestablished. Do not falsify the old result or silently reuse it as evidence for the new build.

## 7. Input and output contracts

### 7.1 Common task envelope

Every dispatched task contains:

- Case, run and task IDs; role and role-definition version.
- User objective and requested deliverable.
- Immutable input references and a minimal relevant context brief.
- Allowed sources, worktree/output paths and prohibited actions.
- Risk tier, budget, timeout and maximum investigation steps.
- Expected output schema and acceptance criteria.
- Review assignment, required independence and current conflict set.
- Actual capabilities; unavailable tools must not be simulated.
- Stop conditions, escalation destination and exact return instruction.

A task is not an invitation to continue the entire project. A source document's instructions are data unless the human owner has explicitly authorized that source as operating guidance.

### 7.2 Common agent response

Every agent returns a small typed envelope plus relevant artifacts:

`task_id`, `role_id`, `status`, `summary`, `input_versions`, `findings`, `evidence_refs`, `artifact_refs`, `proposed_links`, `observed_checks`, `uncertainties`, `requested_followups`, `scope_violations`, `actual_execution_metadata`.

Allowed statuses are `complete`, `needs_input`, `blocked`, `failed`, `partial` and `out_of_scope`. “Complete” means the assigned output contract is met, not that the whole product is ready.

Stewards submit updates as proposals. Reviewers return findings. Judges return rulings. The Decision Authority proposes a decision transition. The controller alone commits authoritative state through its supported interface, subject to the threat-model limits below.

### 7.3 Role contract quality

All 64 roles need genuine instructions that specify when to use them, when to skip them, their unique method, input/output examples, concrete evidence standards, failure cases and escalation. No role is complete with a persona paragraph and generic instructions to think carefully. Share methods through the 28 skills instead of repeating a giant prompt.

## 8. Routing and budget design

### 8.1 Routing algorithm

1. Read the authorized request, current case brief and current valid artifacts.
2. Classify intent and whether the user is requesting analysis, a proposed change, local execution, or an external action.
3. Apply deterministic minimum-risk rules for data, money, production, authority or destructive scope.
4. Select the closest workflow; for a narrow task, select a specialist route.
5. Reuse only artifacts whose scope, versions and evidence remain applicable.
6. Add specialists for missing dependencies; add reviewers for required quality gates.
7. Add manager/director review only when its explicit conditions are met.
8. Add challenge and adjudication for consequential, disputed or low-evidence decisions.
9. Produce a visible route plan with selected roles, omitted roles, reason, expected output and limits.
10. Dispatch ready tasks in dependency order. Pause for material user input rather than inventing it.
11. Review results, commit accepted records, and produce the requested output with unresolved matters.

### 8.2 Default operating budgets

These are **initial design defaults to test**, not established performance claims:

| Mode | Maximum worker tasks | Concurrent workers | Challenge rounds | Target use |
|---|---:|---:|---:|---|
| Focused | 4 | 2 | 0 unless a risk trigger requires escalation | Narrow research or a single-role output. |
| Standard | 12 | 3 | 1 | Typical feature analysis or bounded prototype stage. |
| Deep | 24 | 3 | 2 | Explicitly requested cross-team design or disputed decision. |

Count every actual worker attempt and retry. The root coordinator is not a worker slot. Directors and managers count when actually invoked. A fresh reviewer consumes a task slot. Each run also has a wall-clock ceiling and optional token/currency ceiling. If the host does not expose usage or price, report it as unknown; enforce available admission limits and do not promise a hard dollar cap.

Crossing a limit returns a useful partial result and a specific request to expand scope. Do not silently switch to Deep mode or hide review work to fit a budget. Core workflow integration tests may explicitly allocate the budget their scenario needs.

### 8.3 Simple requests

A request to summarize a supplied design may use Context Analyst and Claim Checker. A request to fix wording in a draft may use Requirements Writer with a narrow diff check. Neither should automatically involve three directors, judges and every specialist. A requested source correction can trigger evidence linkage and change review without rebuilding the application.

### 8.4 Parallelism

Parallelize independent read-only research or separately scoped code changes. Use isolated staging/worktrees when edits can overlap. Two writers must not edit the same target file concurrently. The coordinator reconciles accepted patches serially. Review tasks run against a frozen snapshot and return before that snapshot is claimed verified.

## 9. Risk and decision rights

| Tier | Example | Default authority |
|---|---|---|
| R0 — analysis | Read authorized docs; compare options; propose a requirement. | Agent may produce a recommendation. No external effects. |
| R1 — bounded local change | Edit a toy app or authorized local branch; run permitted tests. | Requires recorded scope; reversible changes can follow explicit delegation. |
| R2 — consequential proposal | Change permissions, sensitive data flows, release criteria or major architecture. | Independent review and human acceptance before changing protected behavior. |
| R3 — external/high-impact action | Deploy, publish, send, pay, delete production data or broaden access. | Outside autonomous v0.1 execution; prepare a human action request. |

Risk classification is conservative and can be raised by a specialist. A model cannot lower an explicit policy minimum. Delegation defines both what may be decided and what may be executed; decision acceptance is not itself action permission.

### 9.1 Decision Authority agent

It may accept a local implementation choice within approved requirements, a reversible test ordering, or a bounded refinement where delegation explicitly covers that decision. It must reject or escalate a choice that changes protected requirements, adds sensitive access, exceeds a budget or needs a new external action.

An acceptance record binds the exact proposal hash and scope. A material revision invalidates the old approval's applicability. Approvals have expiry/revisit conditions and can be revoked. An approval for one target cannot be reused for another.

### 9.2 Human approval and honest enforcement

The initial local system records human approval through the host's explicit user input or an operator command, including provenance and a version binding. If the adapter cannot attest that an input came from the user, record it as an unverified approval claim and do not use it for a protected transition.

A command-line `--role human` flag is not authentication. A local approval file writable by the same OS user as the agent is not tamper-proof proof of human approval. Do not invent cryptographic or independent security guarantees. High-impact external execution remains unavailable in v0.1, and stronger approval channels are a separately designed extension.

## 10. Adversarial review and convergence

### 10.1 Trigger conditions

Activate challenge when a consequential option relies on uncertain evidence, when reasonable alternatives remain disputed, when authority/data boundaries change, when release risks demand it, or when the user explicitly requests adversarial analysis. Do not force challenge for every low-risk output.

### 10.2 Protocol

1. Freeze a decision packet: objective, criteria, options, evidence, constraints, proposal version and author identities.
2. Adversarial Orchestrator selects the smallest set of materially different challenges.
3. Challengers receive the decision packet, not a directive to defeat or agree with the preferred option.
4. Each challenge states the contested premise, counterevidence or gap, consequence and resolving test.
5. The proposal owner responds with evidence, revision or a reasoned disagreement.
6. Evidence Judge is used when evidentiary sufficiency itself is disputed.
7. Convergence Judge compares admissible options and resolves each material challenge.
8. Decision Authority applies recorded delegation or requests human acceptance.
9. Decision Recorder and Dissent Recorder preserve the outcome, rejected alternatives and unresolved matters.
10. Dependency Steward links the accepted decision to downstream work and its revisit triggers.

### 10.3 Stopping rule

The default maximum is two challenge rounds. Stop sooner when all material objections are resolved and criteria are satisfied, or when one discriminating test is clearly more useful than another debate. At the limit, return `deferred`, `human_required` or `unresolved`, with the next evidence to obtain. Agreement is not mandatory.

### 10.4 Judge output

A ruling contains: criteria; admissible evidence; findings on each objection; option comparison; recommended option or deferment; uncertainty; required next checks; preserved dissent; and exact scope. A judge cannot authorize execution, change criteria after seeing results without disclosure, or certify facts by confidence alone.

### 10.5 Independence

The author cannot independently audit its own artifact. Manager review is useful but does not substitute for required independent verification. Record fresh child/session IDs where observable. Using another model family is optional and never equated with statistical independence. If a host cannot create a fresh review context, the report must say `independence_unverified`; a gate requiring independent review remains blocked.

## 11. Execution, receipts and state transitions

### 11.1 Run state machine

```text
created -> scoped -> planned -> executing -> reviewing -> completed
                      |            |           |
                      v            v           v
                 needs_input     blocked      rework
                      |            |           |
                      +-------> planned <-------+

Any nonterminal state -> paused | cancelled | failed
```

A workflow may legitimately complete with a recommended deferment. A run cannot claim `completed` while its promised outputs or mandatory gates are missing. `completed_with_limitations` belongs in a clearly described result, not a hidden synonym for success.

### 11.2 Task state machine

`planned -> ready -> admitted -> running -> submitted -> reviewed -> accepted`

Branches: `blocked`, `needs_input`, `rejected`, `cancelled`, `failed`. An accepted output still may be a negative finding or a correctly blocked recommendation. “Accepted task output” is not “accepted product decision.”

### 11.3 Admission controls

Before dispatch, verify prerequisites, active budget, assigned role capability, target snapshot, write scope, conflicts, source permissions, and review requirements. Mint a work-order ID and reserve available capacity transactionally. Release it on completion or a reconciled interruption. Retry transient errors only within the work order's retry budget.

### 11.4 Actual receipt minimum

For a command/test: command arguments, working directory, target snapshot, input/config/test/dataset hashes, start/end, exit status, timeout/cancellation, stdout/stderr artifact locations, observation source and test identifiers. Redact secrets before reports. Store a distinction between native-observed, controller-observed and agent-reported metadata.

For a model evaluation: requested model/configuration, actual model when observable, task and dataset versions, prompt/skill version, execution mode, outputs, scoring method, token/latency observations and unknown fields. A deterministic replay fixture is labeled `fixture_replay`, never `live_model`.

### 11.5 Snapshot validity

Prefer a Git commit plus dirty-tree diff hash or a content manifest for the relevant tested files. Include test and configuration versions, not only production code. A changed test can invalidate a comparison even if the application did not change. Reuse past evidence only after explicit applicability review.

## 12. Change propagation and correction

### 12.1 Processing a change

1. Preserve the old source/artifact version and ingest the new version.
2. Identify whether the change is intended, corrective, environmental or unexplained.
3. Evaluate contested claims before accepting a correction.
4. Traverse declared dependency edges in reverse from changed dependencies.
5. Queue affected decisions and artifacts with typed impact reasons.
6. Keep protected requirements active unless a properly authorized requirement change supersedes them.
7. Request semantic inspection where links are missing or the change's significance is unclear.
8. Generate only the necessary rework and retest tasks.
9. Revalidate against the new version; preserve historical evidence and dissent.
10. Update derived reports and a short next-task brief.

### 12.2 Different kinds of staleness

Source freshness, factual support, policy approval, implementation validity and test applicability are different. A 48-hour clock cannot make every durable fact false. Time-based review windows depend on the claim's type and context; changed dependencies can trigger immediate revalidation regardless of age. A stale record remains inspectable and is labeled correctly.

### 12.3 Example

A synthetic support copilot has a protected requirement that retrieval only exposes documents authorized for the requesting workspace. An earlier positive test passed. A new cross-workspace negative test reveals leakage. The new evidence contests the isolation claim and requires review of the release decision. The protected isolation requirement remains in force. The old positive test remains a genuine historical pass with limited coverage. A corrected implementation must pass both positive and negative checks before readiness is reconsidered.

This example is supplied as a labeled design fixture, not a report of an actual product incident.

## 13. Storage integrity and concurrency

Use SQLite transactions with optimistic version checks and idempotency keys. Reject stale-state writes with a conflict response, then reread and merge deliberately. All canonical writes use the controller interface. Workers can write assigned artifacts and proposed updates, but should not modify the state database directly.

Use WAL only on a supported local filesystem; do not locate the active database in a Dropbox-synced folder or network filesystem by default. Portable exports and backups can be copied after a consistent snapshot. A live database backup must use SQLite's backup mechanism, not an arbitrary copy of files during writes.

Record schema version and migration version. Back up before migration. Rehearse export/import and recovery in tests. Content hashes detect accidental differences; they do not prevent a privileged local user from altering both content and hashes.

If a worker is interrupted, keep accepted records, mark outstanding work as interrupted, reconcile capacity and inspect staged artifacts before retrying. Do not infer that a process is healthy merely from a status message. Native process cancellation and timeouts depend on host support and must be recorded.

## 14. Security, privacy and trust model

### 14.1 Threats in scope

Untrusted instructions inside documents; accidental reads beyond authorized scope; source poisoning; fabricated citations or execution claims; prompt-induced privilege expansion; stale approvals; conflicting writers; leaking secrets/private examples into a public release; a self-reviewing builder; runaway debate; and treating mock output as real execution.

### 14.2 Controls and their limits

| Control | What code can check | What it cannot guarantee alone |
|---|---|---|
| Source allowlist | Canonical paths, traversal/symlink containment, approved source IDs. | Host tools used outside the controller may still access more. |
| Role policy | Valid role IDs, expected output type, admitted scope and transition eligibility. | A role label does not authenticate the actor. |
| Immutable versions | Hashes, exact approval bindings and stale-result detection. | Local privileged tampering is not prevented. |
| Required review | Presence of review, author/reviewer conflicts, native IDs when available. | Different sessions can still share model biases. |
| Execution receipts | Real observed command outcome and target versions. | A passing test may be incomplete or incorrectly designed. |
| Approval gates | Scope, expiry, version, recorded grant and safe transition rules. | A same-user writable approval file cannot prove human identity. |
| Prompt-injection rules | Trusted/source separation and tests of refusal behavior. | Instructions alone do not create a sandbox. |

**Assurance levels:** `recorded` (the system has a claim), `validated_structure` (schema and references pass), `observed_execution` (an actual receipt exists), `reviewed_semantics` (the relevant judgment is recorded), and `enforced_by_host` (a specific permission restriction is demonstrated). Do not collapse these into one PASS badge.

### 14.3 Permission design

Research/review agents are intended to be read-only except for their own staged reports. Builders receive narrow target work orders. Where the host provides a tested restriction, use it. Where permissions are inherited or cannot be narrowed per role, say so and use isolated parent sessions/worktrees for stronger boundaries. Never configure bypass modes or arbitrary network egress to make a demo pass.

The controller's same-user local design is a workflow integrity mechanism, not a hostile multi-tenant security boundary. A hardened service with independently authenticated callers would be a separate later product.

### 14.4 Data scope

Scope is inherited through summaries, embeddings, reports and examples. Private inputs do not become public because an agent paraphrased them. Default public demonstrations use synthetic material. Public export requires an explicit allowlist and redaction review. No telemetry, prompt uploading or trace transmission is enabled by default.

## 15. Native host adapter design

The current official documentation was checked on 16 October 2026; details must be rechecked against the installed host at implementation time. See `08_SOURCE_NOTES.md` for primary references.

### 15.1 Shared contract

Neutral metadata and role bodies remain authoritative. Adapters translate registration, invocation, tool capability names, observation fields and installation paths. Provider/model identifiers are configuration, never embedded in the core role method. Model defaults inherit the user's host unless a user-approved profile overrides them.

Every adapter declares: host/version; role discovery method; skills discovery; supported dispatch; receipt observability; tool restrictions; permission behavior; cancellation; usage observability; validation command; unsupported capabilities and last test time.

### 15.2 Codex

Project custom agents are documented as TOML files under `.codex/agents/`, with `name`, `description` and `developer_instructions`. Shared local skills are discovered under `.agents/skills`. Current documentation says sandbox and approval policy are inherited from the parent; custom-agent instructions alone do not create a read-only sandbox. Generate supported settings only, and verify native discovery and real child execution. [T1, T2]

### 15.3 Claude Code

Project agent definitions use Markdown with YAML frontmatter under `.claude/agents/`; project skills use `.claude/skills`. Configure only supported fields and explicitly declare the permitted tools. Permission behavior depends on parent mode and host version. Keep the portable scheduler flat even though some current versions support nested delegation. Verify behavior on the installed version rather than assuming that a parsed frontmatter file enforces a boundary. [T3, T4]

### 15.4 Skill standard

Use the Agent Skills format for shared methods: `SKILL.md` metadata and instructions, with optional scripts, references and assets. Keep host-only configuration in adapters rather than presenting it as part of the portable method. [T5]

### 15.5 Three execution labels

- `native`: a real host child executes the assigned role and its identity is recorded.
- `sequential`: the current assistant follows a role's instructions without independent delegation; explicitly weaker isolation.
- `manual_handoff`: a person moves the packet into a new session; origin/independence may remain unverified unless observable.

The fallback is useful, but must never be reported as native delegation. A release cannot claim tested cross-host orchestration because only one host ran or because both sets of files parse.

### 15.6 Adapter conformance

For each host: install into a scratch repo; show discovery; invoke a selected specialist; capture the real child/session if available; request an out-of-scope action and inspect behavior; exercise a manager review; run a challenge/judge path; confirm target-version binding; test interruption; uninstall without losing preexisting files. Record host/version, settings, observed results and unavailable fields.

## 16. Proposed CLI surface

These commands are build targets, not commands available in this attachment. Final syntax must remain consistent across docs and tests.

```sh
aipt doctor --host codex --project /path/to/scratch
aipt validate package /path/to/ai-product-team
aipt install --host both --target /path/to/project --dry-run
aipt install --host both --target /path/to/project
aipt uninstall --target /path/to/project --dry-run

aipt case init --project /path/to/project --brief brief.md
aipt run start --case CASE_ID --workflow shape-feature --mode standard
aipt run plan --run RUN_ID
aipt task next --run RUN_ID
aipt task admit --task TASK_ID
aipt task attach --task TASK_ID --native-child-id CHILD_ID
aipt task submit --task TASK_ID --response response.json

aipt evidence add --case CASE_ID --record evidence.json
aipt link propose --case CASE_ID --record link.json
aipt review submit --run RUN_ID --record review.json
aipt decision propose --run RUN_ID --record decision.json
aipt decision record-user-input --run RUN_ID --record user-input.json

aipt receipt run --task TASK_ID -- pytest tests/test_scope.py
aipt change analyze --case CASE_ID --change change.json
aipt case report --case CASE_ID --format markdown
aipt case export --case CASE_ID --destination ./private-export
aipt eval fixtures --suite core
aipt eval host --host claude --suite core-workflows
```

The CLI records and validates user input; the command name is not a trusted-human attestation. Protected transitions require the approval provenance defined in Section 9. Commands that run external model evaluations must show the target, source scope and budget before execution. No command deploys or publishes in v0.1.

## 17. Evaluation architecture

Test three different questions separately:

1. **Does the software work?** Registry validation, adapter generation, installation safety, schema consistency, state transitions, database recovery and budget accounting.
2. **Do the agents follow their contracts?** Role-specific positive and negative scenarios; evidence quality, bounded behavior, correct escalation and honest execution claims.
3. **Does the team improve outcomes?** Compare current native-host baselines with selected workflows using the same inputs, budgets and grading criteria.

### 17.1 Minimum scenario coverage

64 positive role fixtures and 64 negative role fixtures; all 12 workflow contract fixtures; six core workflows exercised end to end in each host for a cross-host release claim. Include routing tests where only a small subset is appropriate. Static fixtures and mock outputs support software tests, but do not establish live model performance.

The six core workflows are W01, W02, W04, W05, W10 and W11. The other six must have complete procedures and integration fixtures; actual host coverage is recorded separately and cannot be implied by the core matrix.

### 17.2 Critical negative cases

A real citation supporting the wrong claim; conflicting sources; fabricated execution; changed code after tests; changed proposal after approval; judge-authorship conflict; stale decision premise; inaccessible source; prompt injection; private data in a public example; budget exhaustion; absent native child; unavailable second host; attempted self-delegation of production authority; and a skill improvement overfitted to its development cases.

### 17.3 Outcome and efficiency measures

Measure requirement coverage and correctness against an externally specified rubric, material omissions, false approval, correct deferment, actual task completion, user interventions, worker calls, elapsed time and observed cost where available. Report sample counts and slices; do not infer production risk rates from a tiny demonstration. Use held-out cases and disclose model/version/settings, retries and grading method.

No popularity, quality lift, token saving or benchmark advantage is promised by this design.

## 18. Failure recovery and degraded operation

| Failure | Required response |
|---|---|
| Source unavailable | Mark the affected claim unsupported/unknown; proceed only where the missing source is nonblocking. |
| Native spawn unavailable | Record a supported fallback or blocked native test; never impersonate a child. |
| Tool/test unavailable | Return blocked/not_run and preserve runnable instructions. |
| Conflicting records | Preserve both and request scoped adjudication. |
| Worker timeout | Mark interrupted, release reconciled capacity, retain artifacts and retry only within budget. |
| State version conflict | Reject stale write; reread and submit a merge proposal. |
| Database failure | Stop authoritative writes, preserve evidence and recover from a tested snapshot. |
| Human needed | Return a compact decision packet; do not keep debating to avoid asking. |
| Budget exhausted | Stop dispatch, summarize valid work and request explicit expansion. |
| Host update breaks adapter | Disable the failed capability, retain neutral content and expose compatibility status. |

## 19. Controlled evolution

A Learning Steward can propose changes to role instructions, skills or workflow recipes, supported by verified outcomes. It must identify the failure being addressed, affected invariants, candidate change, expected improvement, held-out tests and rollback version. Independent review and the appropriate human approval precede promotion.

Authority policy, source exclusions, privacy boundaries, release claims and evaluation thresholds are protected. Agents cannot relax them merely because doing so improves apparent completion. Track versions of the agent package independently of each customer/project case.

Compatibility checks are explicit tasks initially. A recurring update monitor is optional and requires user authorization; the package does not silently install scheduled jobs.

## 20. Architecture decisions and tradeoffs

| Decision | Reason | Cost / alternative |
|---|---|---|
| 64 specialized contracts, selected on demand | Offers breadth and recognizable task ownership. | More maintenance; retirement must be permitted when a role proves redundant. |
| One native root dispatcher | Portable and easier to observe. | Root has coordination overhead; avoid unnecessary transcript accumulation. |
| Shared skills, distinct role contracts | Preserves substantive methods without copy-paste divergence. | Compiler must verify all references and generated installations. |
| Local SQLite + immutable blobs | Transactional versions and references without a hosted service. | Local filesystem constraint; exports required for portable handoff. |
| Independent judgments are advisory inputs to authority | Prevents rhetorical consensus from becoming automatic permission. | Additional review effort for consequential decisions. |
| Flat default execution | Separates organizational hierarchy from host nesting features. | Some hosts may offer optimizations not used initially. |
| No autonomous external writes in v0.1 | Keeps the initial boundary clear and testable. | Users perform deployment/publication separately. |
| Reuse audited methods; author missing specialisms | Moves quickly without pretending the existing inventory contains everything. | Provenance review and new role evaluations remain real work. |

## 21. Open design decisions with safe defaults

The repository name is provisional; use `ai-product-team` unless the user changes it. Default to repository-scoped installation, no telemetry, no global hooks, no automatic schedules, no direct provider API requirement and no public push. Use the user's current permitted model rather than hardcoded model IDs. Verify the installed runtime before selecting optional host features.

License selection requires clear ownership of included material. Until that check succeeds, the local repository can be built privately with `LICENSE_PENDING.md`, but it must not be represented as a cleared open-source release. New skill implementations must be labeled new rather than attributed to an unread local source.

## 22. Traceability into implementation

`01_INITIAL_PRD.md` defines requirements and product gates. `06_IMPLEMENTATION_PLAN_AND_ACCEPTANCE.md` defines build milestones and verification. `07_WORKFLOWS.md` expands the twelve recipes. `registry/agents.json` fixes the proposed catalog and role contracts; it is a seed, not a runtime implementation. The local build prompt requires source inspection, contract tests, native adapter validation, meaningful agent behavior tests and a truthful final status report.
