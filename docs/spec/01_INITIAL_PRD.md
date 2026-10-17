# AI Product Team — initial product requirements document

**Version:** 0.1 • **Date:** 16 October 2026 • **Owner:** Emmanuel Benami

**Status:** initial PRD for local implementation. Requirements are proposed product commitments, not claims about a shipped system. The name `AI Product Team` and repository name `ai-product-team` are provisional.

## 1. Product definition

A provider-neutral organization of specialist agents that people use inside Codex or Claude Code to investigate, design, build, evaluate and improve AI features. A user can bring a narrow question, a source collection, a proposed feature, an existing repository, a failed evaluation or a changed constraint. The organization selects the relevant workflow and specialists, preserves evidence and decisions through the work, and returns usable artifacts with honest verification status.

The system combines **64 agents, ten specialist teams, three directors, one workflow orchestrator, 28 shared skill targets and twelve workflows**. It supports breadth through specialization and selective activation. The number of registered agents is not the number invoked for a task.

The owner remains responsible for purpose, protected requirements, data access, delegation and consequential decisions. The team can make bounded delegated local choices; it cannot create new authority for itself.

## 2. Problem and product hypothesis

When a user passes a product problem among research, design and coding assistants, the source of a requirement can be lost, an unresolved assumption can become accepted fact, a change can escape downstream review, and a successful test can be applied to a different code state. Isolated specialist prompts can produce individually plausible documents without preserving their relationships.

**Product hypothesis:** a shared evidence/decision record, explicit work orders, differentiated review and selective routing can make these handoffs more useful and inspectable without imposing the cost of a full organization on every request.

This is a hypothesis to test. The audits establish the existence and described behavior of reusable local methods, not a measured improvement in task success. No current market-demand, adoption or performance claim is adopted from an earlier conversation. The initial release must show real examples and disclose its limits.

## 3. Users and jobs

### Primary users

**Founder or small product team:** wants to investigate and build an AI feature using an existing coding assistant without assembling a new agent framework.

**Product manager or technical product lead:** wants research, product requirements, experience decisions and acceptance criteria to survive the handoff into implementation.

**Engineering or AI lead:** wants bounded technical designs, meaningful evaluations, explicit tool permissions, reproducible tests and traceable changes.

### Secondary users

Researchers and maintainers can use the evidence, challenge, decision and change workflows independently. They do not have to adopt the whole product-development lifecycle.

### Jobs to be done

A user should be able to ask whether AI is justified; shape a feature from source material; design its system; build a small version; evaluate it; diagnose failures; compare models; examine cost and latency; review release readiness; propagate a change; resolve a disputed decision; and improve a skill or workflow from verified outcomes.

## 4. Intended outcomes

The user receives a concrete requested deliverable and can inspect what supports it. A feature brief links to source material. An architecture assigns responsibilities and failure behavior. An implementation links to approved requirements. A validation identifies what actually ran against which version. A decision records who accepted it and what would change it. An incoming correction identifies the work that needs reconsideration.

The creator receives a coherent, repository independent of the owner's unrelated private work with a plain-English catalog, reproducible demonstrations and enough technical substance for an article. Visibility and adoption are desirable results, not guaranteed consequences of this PRD.

## 5. Scope

### Included in v0.1 build target

- All 64 full role definitions and native registrations for both supported hosts.
- Ten teams with explicit manager/director relationships and independent review rules.
- All 28 shared skill targets, adapted from admitted sources or newly authored with precise provenance.
- Twelve complete workflow recipes and a router that activates a justified subset.
- A small local controller for records, transitions, task admission, versions, lineage, receipts and reports.
- Evidence, requirements, implementation, validation and decision traceability.
- Bounded adversarial review, evidentiary adjudication, convergence and delegated decision handling.
- Repository-scoped installation, compatibility checks, upgrade/removal safety and no default telemetry.
- A synthetic support-copilot demonstration, software tests, role scenarios and workflow evaluation instructions.
- An HTML/Markdown plain-English agent directory generated from the same registry.

### Explicitly excluded

A hosted SaaS application, vector database requirement, custom model-serving layer, cross-provider execution bridge, always-on autonomous daemon, automatic publication/deployment, a legal department, factual certification by an LLM judge, guaranteed hallucination elimination, confidential real-case demonstrations and automatic self-rewriting of policy.

Material from the owner's unrelated private projects, and anything whose independence from them cannot be established, remains excluded. Held PRD, PM-course, employer and third-party material is not silently imported. The existing Memory Steward is not required for the core system; the new evidence/decision record must be independently specified rather than dependent on private historical memories.

## 6. Product surfaces

### 6.1 Front-door request

The primary surface is natural language in the native assistant. Workflow names are also exposed as namespaced skills. The response should briefly state the selected route, expected artifact, material missing input and any action/permission boundary. It should then do the work.

### 6.2 Workflow catalog

The README presents twelve user requests, required input and output. Internal agent names must not be necessary to choose a workflow. Users may call a specialist explicitly for narrow work.

### 6.3 Agent directory

A human-readable directory groups 64 cards by team. Each card has a plain name, type and one-sentence job. Expanded documentation shows inputs, outputs, scope, review relationship, skills and tests. No invented executive biographies or decorative personality prompts.

### 6.4 Case brief and decision view

The user can inspect the objective, current approved requirements, evidence limitations, unresolved questions, active decisions, dissent, implementation status, validation coverage and next action. The brief is generated from canonical state.

### 6.5 Work and verification view

A report distinguishes proposed work, actual edits, checks actually run, failed checks, blocked checks, current applicability and independent review status. Code references, dataset/config versions and execution receipts are visible where relevant.

### 6.6 Change-impact view

The system shows what changed, what declared dependencies are affected, what remains valid, what has insufficient linkage, and which decisions or tests need review. It never presents a graph traversal as complete semantic understanding.

## 7. Primary user journeys

### Journey A: assess and shape a feature

A founder supplies a product description, relevant documents and a proposed AI feature. The Context Analyst reconstructs the existing product. Discovery Interviewer asks only unresolved questions that alter the solution. Opportunity Analyst compares viable alternatives. The relevant manager reviews the reasoning. If a choice is consequential or disputed, challenge and adjudication are invoked. The user receives a recommendation or a specific next test, followed by requirements and an experience design when requested.

Success means the proposal is grounded in supplied/authorized evidence and its uncertainty is preserved. A correct outcome may be to avoid AI or defer implementation.

### Journey B: build and evaluate

A technical lead supplies an accepted scope and authorized local repository. Repository Mapper identifies actual files and commands. Implementation Planner produces bounded work orders. The builder implements in the assigned scope. Test Engineer creates or preserves checks linked to acceptance conditions. A fresh reviewer/auditor rechecks the relevant snapshot. The team reports implemented, verified, failed and blocked items separately.

Success means a usable local artifact with evidence. A model stub can be appropriate for a specified test, but cannot be presented as an operational model integration.

### Journey C: investigate and correct

A user supplies a new test result contradicting an earlier architectural assumption. The claim becomes contested. Relevant evidence review accepts or rejects the correction. Dependency Steward and Change Impact Analyst identify affected decisions and artifacts. Protected requirements remain valid. The team proposes the smallest needed revision, executes only authorized work and reruns applicable checks.

Success means the next task no longer relies on a superseded premise and unaffected work is not needlessly restarted.

### Journey D: challenge and decide

A user has two plausible approaches and asks for a decision. The Review Manager freezes common criteria and the proposal versions. The Adversarial Orchestrator requests bounded, materially different challenges. Judges assess evidence and remaining tradeoffs. Decision Authority applies the recorded delegation or returns a human decision request. The record preserves dissent and revisit conditions.

Success can be acceptance, rejection, a conditional choice or a clearly defined unresolved question. Majority agreement is not the acceptance rule.

## 8. Functional requirements

`P0` means required for the v0.1 implementation target. `P1` means a subsequent extension. Test IDs refer to the acceptance plan.

### Organization and shared methods

| ID | Priority | Requirement | Acceptance condition |
|---|---|---|---|
| FR-001 | P0 | Provide the exact proposed catalog of 64 agents with unique IDs, 10 teams and 4 leadership/coordination roles. | Registry and human directory agree; every role has a full body and valid relationships. AT-01. |
| FR-002 | P0 | Preserve explicit leader → manager → specialist responsibility relationships. | Every nonleadership role has a valid manager or director; decision authority remains delegation-based. AT-01, AT-09. |
| FR-003 | P0 | Give each role distinct triggers, exclusions, method, inputs, outputs, evidence rules and review criteria. | No persona-only stubs; each has one positive and one role-specific negative scenario. AT-02. |
| FR-004 | P0 | Implement 28 shared skill targets without duplicating the same method across role bodies. | Skills resolve; existing/new provenance is correct; no broken referenced files. AT-01, AT-03. |
| FR-005 | P0 | Keep neutral contracts authoritative and host wrappers generated. | Equivalent input/output/authority contracts in both adapters; changes regenerate deterministically. AT-04. |

### Routing and workflow execution

| ID | Priority | Requirement | Acceptance condition |
|---|---|---|---|
| FR-006 | P0 | Implement twelve selectable workflows and narrow direct-specialist invocation. | Every workflow has inputs, work graph, conditional roles, gates, outputs and recovery. AT-05. |
| FR-007 | P0 | Activate only roles justified by missing work, risk or review needs. | A simple source summary does not invoke directors, builders or judges without cause. AT-06. |
| FR-008 | P0 | Use one root dispatcher in the portable baseline; managers return work orders rather than assuming nested execution. | Child agents do not recursively dispatch; hierarchy does not force a process ladder. AT-06. |
| FR-009 | P0 | Make task, concurrency, retry, time and observable-cost limits explicit. | Admission stops at limits; unavailable usage remains unknown; escalation is explicit. AT-07. |
| FR-010 | P0 | Track actual native dispatch and execution mode. | Native claim requires observed child identity; fallback is labeled sequential/manual. AT-04, AT-08. |
| FR-011 | P0 | Support interruption and resumable case state. | Accepted records survive; unfinished tasks remain unfinished; retries do not duplicate decisions. AT-15. |

### Authority, review and convergence

| ID | Priority | Requirement | Acceptance condition |
|---|---|---|---|
| FR-012 | P0 | Separate recommendations, manager reviews, judicial rulings, accepted decisions and executed actions. | State transitions reject conflation; a judge cannot deploy. AT-09. |
| FR-013 | P0 | Bind delegated decisions and human approval records to exact scope and versions. | An approval for proposal v1 cannot authorize v2 or a different target. AT-09. |
| FR-014 | P0 | Block autonomous high-impact external writes in the initial product. | No initial command publishes, sends, pays, deletes production records or deploys. AT-09, AT-16. |
| FR-015 | P0 | Prevent self-authored work from satisfying required independent audit. | Author/reviewer conflict rejected; unobserved fresh-context origin is disclosed. AT-10. |
| FR-016 | P0 | Run a bounded adversarial protocol with material challenge contracts. | Challenge states premise, consequence, evidence/test and resolution; max rounds enforced. AT-11. |
| FR-017 | P0 | Permit deferment and unresolved disagreement. | Judge can return insufficient evidence; no majority-vote rule or forced consensus. AT-11. |
| FR-018 | P0 | Preserve dissent, rejected alternatives and revisit conditions. | Accepting an option retains unresolved objections and why acceptance remains permitted. AT-11. |

### Evidence, implementation and verification

| ID | Priority | Requirement | Acceptance condition |
|---|---|---|---|
| FR-019 | P0 | Record sources, claims and immutable versions with access scope and limitations. | Every material evidence claim has a resolving reference or explicit unsupported status. AT-12. |
| FR-020 | P0 | Preserve source conflicts and distinguish fact, hypothesis, observation and decision. | Later summaries cannot silently promote unverified material. AT-12. |
| FR-021 | P0 | Connect requirements, accepted decisions, artifacts and checks through typed links. | Coverage report shows linked, missing and disputed relationships. AT-12, AT-13. |
| FR-022 | P0 | Record real execution receipts and identify what they actually tested. | Command, target/test/data/config versions, exit status and logs are recorded; invented execution fails review. AT-14. |
| FR-023 | P0 | Separate historical validation outcome from current applicability. | Editing the target after a pass makes applicability stale without rewriting the pass. AT-13. |
| FR-024 | P0 | Propagate accepted corrections through declared dependencies and targeted semantic review. | A changed premise queues affected work and preserves unrelated current artifacts. AT-13. |
| FR-025 | P0 | Preserve protected requirements when an implementation fails. | Failed isolation leads to remediation, not deletion of the isolation requirement. AT-13. |
| FR-026 | P0 | Produce concise reports from authoritative records. | Editing a rendered report cannot change the accepted state; regeneration is reproducible. AT-15. |

### Installation, compatibility and provenance

| ID | Priority | Requirement | Acceptance condition |
|---|---|---|---|
| FR-027 | P0 | Install into a selected repository with namespaced files and safe conflict handling. | Dry-run, backup, change manifest and ownership-aware uninstall preserve preexisting files. AT-17. |
| FR-028 | P0 | Verify host/version capabilities before claiming support. | Discovery, dispatch, restrictions and fallback tested independently for each host. AT-04. |
| FR-029 | P0 | Exclude disallowed and uncleared source families from the public package. | Source allowlist and provenance decisions reviewed; no private source map, run logs or confidential examples in export. AT-03, AT-16. |
| FR-030 | P0 | Distinguish adapted local methods from newly authored specialisms. | Every shipped method has a provenance classification and appropriate attribution. AT-03. |
| FR-031 | P0 | Avoid root guidance replacement, global hooks, global installs and automatic schedules by default. | Installation only touches explicitly owned target paths; optional operations require separate authorization. AT-17. |
| FR-032 | P0 | Keep provider names, model IDs, prices and changing capabilities out of core methods. | Model selection and cost analysis use explicit dated configuration; missing facts stay unknown. AT-18. |

### Demonstration and controlled improvement

| ID | Priority | Requirement | Acceptance condition |
|---|---|---|---|
| FR-033 | P0 | Provide a synthetic support-copilot demonstration with a meaningful revision. | Initial build, negative test, premise correction and targeted revalidation can be reproduced. AT-19. |
| FR-034 | P0 | Label mock, replay, native and actual-model executions distinctly. | Replayed outputs never appear as live inference or benchmark results. AT-14, AT-19. |
| FR-035 | P0 | Compare selected workflows against a current native-host baseline. | Same inputs and disclosed budget/criteria; unsuccessful cases and overhead reported. AT-20. |
| FR-036 | P0 | Gate skill/workflow improvements on evidence and regression checks. | Learning Steward produces proposals; protected policies cannot self-modify. AT-21. |
| FR-037 | P0 | Publish precise per-role and per-workflow readiness labels. | Authored, generated, discovered, executed and evaluated states remain distinct. AT-02, AT-20. |
| FR-038 | P0 | Generate a simplified directory from the canonical registry. | All names/counts/types match; the HTML works offline and includes keyboard-accessible controls. AT-01, AT-22. |
| FR-039 | P1 | Add optional nested execution or a cross-provider execution bridge. | Separate threat model, conformance suite and authorization; not required by initial installation. |
| FR-040 | P1 | Add optional recurring compatibility or outcome monitoring. | User-authorized cadence, scopes and outputs; no unattended changes to policy. |

## 9. Nonfunctional requirements

| ID | Requirement | Initial acceptance target / method |
|---|---|---|
| NFR-001 | Portability | Neutral core has no provider API dependency; compile and test both native formats. |
| NFR-002 | Local-first operation | Core state, validation, reports and fixture tests work without network access. External research/model execution is explicitly separate. |
| NFR-003 | Integrity | Transactional updates, immutable versions, optimistic concurrency, idempotent retries and consistent backups. |
| NFR-004 | Privacy | No telemetry or private trace upload by default. Scope inheritance and public-export review are mandatory. |
| NFR-005 | Honest assurance | Distinguish policy instructions, structural validation, observed execution and host-enforced controls. |
| NFR-006 | Efficiency | No full catalog injection; only relevant skill bodies/context are loaded. Measure agent overhead alongside output quality. |
| NFR-007 | Maintainability | One source of truth per contract, deterministic generated files and public provenance records. |
| NFR-008 | Accessibility | Text-first directory, semantic HTML, keyboard controls and readable reports; no color-only status meaning. |
| NFR-009 | Recoverability | Resume and export/import tests preserve accepted decisions, versions and unresolved work. |
| NFR-010 | Installation safety | Never overwrite unowned files or remove user edits without a visible conflict decision. |
| NFR-011 | Observability | Report actual native IDs, versions, checks, durations and unknown telemetry without fabrication. |
| NFR-012 | Setup burden | Repository-scoped install should require only documented local prerequisites; target under ten minutes on a prepared machine, to be measured rather than promised. |
| NFR-013 | Controller responsiveness | Target subsecond metadata/report operations on a 1,000-node synthetic case on a documented test machine; record actual results. Model time excluded. |
| NFR-014 | Bounded failure | Failed tools and exhausted budgets return useful partial state and explicit next actions. |

Latency/setup figures above are design targets, not measured facts or marketing claims.

## 10. Decision-rights matrix

| Role | May propose | May review | May adjudicate | May accept a decision | May execute |
|---|---|---|---|---|---|
| Specialist | Its assigned analysis/artifact | Only as separately assigned, with disclosed authorship | No | No | Only declared local work scope. |
| Manager | Work order and recommendation | Team outputs | No substantive judicial authority | No protected acceptance | No broader authority from title. |
| Director | Cross-team direction | Cross-team coherence | Organizational tradeoff recommendation | Only if the same recorded human delegation explicitly grants it; default none | No automatic external effects. |
| Challenger | Counterargument/test | Proposal weaknesses | No | No | Authorized synthetic/local checks only. |
| Judge | Ruling and next-test request | Evidence/options | Yes, within its assigned question | No | No. |
| Decision Authority | Decision record | Authority and conditions | Uses rulings; does not replace them | Within explicit human delegation only | Acceptance is not execution permission. |
| Independent Auditor | Findings and verification report | Frozen delivered work | No | Can accept its audit output, not the product release | Reproduce authorized checks. |
| Human owner | Purpose and protected scope | Any output | Final unresolved choice | Yes, subject to applicable external constraints | Personally authorizes/executes external actions. |

The controller checks this workflow matrix. Same-user local software does not provide adversarially tamper-proof role authentication. High-impact autonomous execution is excluded accordingly.

## 11. Metrics and validation plan

### User value measures

**Task success:** independent review of whether the requested deliverable meets a predefined rubric, including correct refusal/deferment when evidence is insufficient.

**Decision-to-delivery consistency:** material requirements or constraints lost between accepted decision and implementation divided by reviewed requirements/constraints in the sampled cases.

**Verification integrity:** false completion/approval claims divided by evaluated completion opportunities, with separate counts for correctly blocked cases.

**Change handling:** affected dependencies correctly queued and unaffected work unnecessarily queued, measured against an externally prepared change fixture. Report recall and false-positive counts; small fixtures do not establish broad reliability.

**Effort:** user corrections, agent calls, elapsed time and observable cost per completed task, with missing telemetry explicitly unknown.

### Creator/adoption measures

Voluntary issue reports, reproducible external use cases, repeat usage reported by users, contributions and the relationship between article readers and repository interest are useful signals. There is no telemetry requirement. Stars and impressions can be observed after publication but do not substitute for usefulness.

### Comparison design

Use current Codex and Claude Code baselines with the same input package, objective, allowed tools and explicit budget. Include at least one narrow task where a single assistant may perform better and one consequential change where traceability should matter. Prespecify rubrics, retain failures, disclose model/version/settings and separate development from held-out examples.

Do not claim a measured benefit until actual comparisons exist. A replay fixture validates software flow, not agent effectiveness.

## 12. Release scope and readiness

All 64 roles must be substantive and all twelve workflows must be specified and runnable through the supported controller/host pattern. Work proceeds in vertical slices, so useful behavior appears before the full catalog is polished. This sequence does not authorize stopping at twelve role stubs.

### Per-role states

`specified -> authored -> contract_validated -> adapter_generated -> native_discovered -> scenario_executed -> evaluated`

### Per-workflow states

`specified -> implemented -> fixture_passed -> native_codex_passed / native_claude_passed -> comparison_reported`

A claim that the package has “64 agents” requires 64 full definitions and valid registrations. It does not permit a claim that all 64 have been empirically validated. Display actual coverage.

### Cross-host v0.1 claim

Require actual discovery for the catalog on each host, relevant adapter conformance checks, and six core workflows (W01, W02, W04, W05, W10, W11) run end to end on each host. The remaining six workflows have complete implementations/fixtures and precisely disclosed live coverage. A missing host or unavailable capability leaves that compatibility claim blocked; work on independent tasks can continue.

## 13. Packaging and publication requirements

The README must state the user problem, supported workflows, install/removal steps, actual compatibility, example inputs/outputs, evidence boundaries and limitations. It must show what a user gets without requiring them to understand internal agent orchestration first.

The repository includes a plain-English organization view, full technical role contracts, readable examples, license/attribution records and a comparison report when measurements exist. A public launch should link directly to usable material. It should not describe 64 autonomous employees, guaranteed accuracy, proven safe concurrency, or certified legal/security judgments.

The initial local build does not publish a repository, send a LinkedIn post or deploy a site. Publication is a separate user action after provenance and release review.

## 14. Reuse policy

The March seven-skill pack supplies S01–S07 after local source inspection. The admitted Plan, Implement, Audit and Documentation runbooks inform S08–S11. S12–S28 are new work or new combinations, and must be labeled accordingly. No implementation is inferred from a role name or audit summary alone.

The resource map identifies exact source locations where the audits do so, and bounded discovery patterns where they do not. It separately marks optional/reference-only, held and excluded material. Never resolve a missing admitted source by searching the owner's private projects, private run logs, all home directories or confidential client work.

## 15. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Organization becomes ceremony | Selective routing, hard budgets, narrow entry points and baseline comparisons. |
| Many roles are cosmetic | Unique output contracts, negative cases and independent quality review. |
| Native platforms subsume a skill | Recheck capabilities; keep domain methods separate and retire redundant wrappers. |
| Shared model biases produce consensus | Evidence-first review, fresh contexts, explicit uncertainty and valid deferment. |
| Ledger creates false confidence | Distinguish typed references from semantic support and measured behavior. |
| Local gates are mistaken for security isolation | Document trust model and leave external effects out of v0.1. |
| Reuse leaks private IP | Allowlisted provenance review, private build workspace and explicit public-export scan. |
| Implementation expands into a framework project | Native host execution, standard-library controller where practical and fixed vertical milestones. |
| Catalog breadth outruns testing | Per-role/workflow coverage labels and gated public claims. |
| Debate consumes time without progress | Material challenges, discriminating tests and bounded rounds. |

## 16. Open questions and default decisions

**Brand/name:** use the provisional name, with no time spent on a logo before a working slice.

**Local path:** the build prompt proposes `$HOME/Projects/ai-product-team`; inspect before use and do not overwrite an existing repository.

**Model selection:** inherit permitted host defaults. Do not add hardcoded provider model names or demand an API key for the core package.

**License:** prepare a permissive-license proposal for clearly new/admitted material after attribution checks. Do not claim a cleared release while source rights remain unresolved.

**Telemetry and scheduling:** disabled by default.

**Memory Steward:** optional future supporting method, not a prerequisite or centerpiece.

**Breadth:** 64 roles are the requested proposed scope. The local builder can identify redundancy with evidence but must not silently reduce or rename the catalog; propose changes in a scope-decision record.

## 17. Definition of done for the local build

The local repository contains real role and skill bodies, working controller/adapter/installer code, runnable examples and tests, current provenance decisions, the full directory and workflow documentation, and a candid requirement/compatibility matrix. Every claimed command was actually executed or labeled as unrun. Every missing capability is specifically identified. Source originals and unrelated projects remain unchanged. Nothing is published without separate authorization.
