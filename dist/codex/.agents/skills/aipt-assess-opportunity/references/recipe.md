# W01 · Should we add AI to this workflow?

A team describes a workflow it wants to improve, usually with an AI feature already in mind, and asks whether adding AI is the right move. This workflow returns an opportunity brief grounded in the authorized sources, a comparison of the proposed AI intervention against simpler alternatives and against doing nothing on the same outcome criteria, and either an advisory recommendation, a next-test request, or a decision proposal routed through W11 when the choice is consequential or disputed.

Entry skill `aipt-assess-opportunity` · Manager `discovery-manager` · Minimum risk R0 · Core cross-host release test yes

## Purpose and outcome

W01 answers one question before anyone shapes, designs or builds: does AI belong in this workflow at all, and if so in what form? The outcome is a packet the case owner can act on. It states the current job as the evidence supports it, which unknowns change the answer, how the AI option compares with ordinary rules or process changes and with leaving things alone, and what the next decision or test is.

The run completes when the three analysis stages are accepted, the Discovery Manager's review record reads `ready`, and the recommendation states its own uncertainty and authority basis. A completed W01 commits the team to nothing. Shaping belongs to W02, design to W03 and any build to W04, each with its own gates.

Example. Larkspur Support asks whether Reply Assist should approve support credits automatically. W01 compares an automatic approver, draft assistance with a person approving each credit, and a fixed credit rule in ordinary code, all against the same criteria (time to resolution, refund error rate, agent effort). With one complaint as the only evidence of demand, it returns a next-test request rather than a verdict.

## Inputs

The user supplies five things: the problem (what outcome is failing and for whom), the current workflow (steps from trigger to completion, including who approves what), the users (who performs the work and who receives its result), constraints (policy, data, budget, time) and existing alternatives (what is already tried or available). Each arrives as a supplied `source` record with its own version, so the brief can cite it.

The case must already contain a case brief with an objective, protected constraints, a source scope and an owner. Every document the roles may read is a `source` record inside that scope; anything outside the scope is not read.

When something is missing, the run does not fill the blank:

| Missing | Behavior |
|---|---|
| Problem | `needs_input`: "What outcome is failing today, for whom, and what evidence shows it?" |
| Current workflow | `needs_input`: "Describe the steps a person follows today from trigger to completion, and who approves each step that spends money or contacts a customer." |
| Users | The Context Analyst records the gap; the Discovery Interviewer asks "Who performs this work and who receives its result?" only if the answer changes which option is viable. |
| Constraints | Proceed with an explicit limitation; the comparison lists constraints as unknown and names which option each unknown would disqualify. |
| Existing alternatives | The Opportunity Analyst constructs doing nothing and at least one non-AI alternative from the workflow itself and labels them reconstructed, not supplied. |
| Source scope empty | `blocked`: no authorized sources; the resolving action is a case brief that names the scope. |

## Outputs

Opportunity brief: `context-brief.md`, headings `## Current job`, `## Actors and volumes`, `## Constraints`, `## Evidence and its limits`, `## Inherited decisions`, `## Open questions`. Stored as an `artifact` record (status `proposed`); each statement under evidence is proposed as a `claim` typed `fact`, `hypothesis` or `observation`.

Questions and decisions: `questions-and-decisions.md`, headings `## Questions asked` (each with a `changes:` line naming the option it decides), `## Answers received`, `## Open decisions`. Stored as an `artifact`; each answer the user gives is recorded as user input with its channel and attestation flag.

Option comparison: `opportunity-comparison.md`, headings `## Outcome criteria`, `## Options` (the proposed AI intervention, at least one non-AI alternative, doing nothing), `## Comparison`, `## Value hypothesis`, `## Evidence required`, `## Recommendation or next test`. Stored as an `artifact` and as a `proposal` record with keys `options`, `recommended_option`, `assumptions`, `evidence_refs`, `constraints`, `unresolved_questions`, `target_refs`, `author_role`, `requested_authority`.

Review: `problem-review.json`, keys `reviewed_refs`, `reviewer_role`, `reviewer_session`, `findings`, `evidence_sufficiency`, `result`, `conflict_check`, `unresolved`, `requested_followups`. Stored as a `review` record.

Decision or next-test recommendation: `recommendation.md`, headings `## Question decided or deferred`, `## Options considered`, `## Outcome`, `## Uncertainty`, `## Authority basis`, `## Revisit conditions`. Produced only when the `decide-or-test` stage runs; stored as an `artifact` and as a `decision` record with status `proposed`, `deferred` or `human_required`. When the stage is omitted, the recommendation the user receives is the `## Recommendation or next test` section of the accepted comparison, confirmed by the review record, and it is advisory.

## Work graph

| Stage id | Role | Depends on | Conditional predicate | Artifact | Review / independence | Write scope |
|---|---|---|---|---|---|---|
| `frame` | `context-analyst` | — | — | `context-brief.md` | no / no | proposal-only |
| `resolve-unknowns` | `discovery-interviewer` | `frame` | — | `questions-and-decisions.md` | no / no | proposal-only |
| `compare` | `opportunity-analyst` | `resolve-unknowns` | — | `opportunity-comparison.md` | no / no | proposal-only |
| `review` | `discovery-manager` | `compare` | — | `problem-review.json` | review gate / manager review, `independent=false` | proposal-only |
| `decide-or-test` | `decision-authority` | `review` | `consequential_or_disputed` | `recommendation.md` | no / delegates to W11, whose judge stages are review gates | proposal-only |

The five stages are strictly sequential: each reads the accepted version of the one before it. The only parallel work is conditional research. When the review requests both a Customer Researcher and a Source Researcher, their tasks are read-only and run concurrently within the mode's worker limit.

## Stage procedures

### frame

The Context Analyst (`aipt-context-analyst`) reads the case brief and every source in scope and applies `aipt-method-corpus-grounded-onboarding` to separate current observations, inherited decisions and uncertain assumptions, then `aipt-method-status-handoff` to keep the brief short and derived from the sources rather than from memory. An older specification is recorded as inherited, never as current behavior. Input refs: the case brief version, each `source` version in scope, the five user inputs. Acceptance: every statement cites a source version or is labeled hypothesis, the open-questions list is explicit, and nothing in the brief recommends an option.

### resolve-unknowns

The Discovery Interviewer (`aipt-discovery-interviewer`) applies `aipt-method-discovery-interrogation` to the brief's open questions and keeps only those whose answer changes which option wins or whether an option is admissible. Each question carries a `changes:` line naming that choice. A question whose answer is already in the supplied material is not asked. When a material answer is missing, the stage returns `needs_input` with the exact question and the run waits; otherwise it returns `complete` with the open decisions listed, not assumed. Input refs: the accepted `context-brief.md` version and the user inputs. Acceptance: no question duplicates supplied facts, every question names the choice it decides, and every unanswered material question appears under `## Open decisions`.

### compare

The Opportunity Analyst (`aipt-opportunity-analyst`) applies `aipt-method-outcome-and-value-analysis` to state the outcome that matters as a falsifiable hypothesis and to compare every option on the same criteria, `aipt-method-research-consolidation` to consolidate the supplied evidence with provenance, and `aipt-method-discovery-interrogation` for the residual unknowns each option depends on. Options always include doing nothing and at least one non-AI alternative when one is viable; the analyst does not assume the answer uses a model. Input refs: the accepted brief, the accepted questions-and-decisions file, any recorded answers. Acceptance: one criteria set for all options, no demand or outcome figure without an evidence ref, a value hypothesis that names the measurement that would falsify it, and a `requested_authority` set honestly (R2 when the recommended option changes who approves money or who contacts a customer).

### review

The Discovery Manager (`aipt-discovery-manager`) applies `aipt-method-outcome-and-value-analysis` and `aipt-method-corpus-grounded-onboarding` to check two things: that each claim the recommendation leans on has source support, and that the recommendation follows from the comparison rather than from the request. It returns a `review` record with `result` set to `ready`, `revise`, `blocked` or `escalate`; `pass` is reserved for reviews that cite executed checks and does not apply here. Where support is missing, it returns targeted follow-up work orders that name the gap that would change the decision, not a general request for more research. Because the manager leads the team that authored the artifacts, the record carries `independent=false`. Input refs: the accepted comparison and the brief it cites. Acceptance: a result is recorded, every finding points at a ref, and no unsupported customer-need claim is approved.

### decide-or-test

This stage runs only when `consequential_or_disputed` is true: the recommended option is R2 or higher, or a recorded challenge or dissent is open. The Decision Authority (`aipt-decision-authority`) applies `aipt-method-delegated-authority` and `aipt-method-evidentiary-adjudication`. It hands the frozen proposal, the review record and the delegation record to W11 (`resolve-decision`), and after W11's judgment accepts only within a delegation bound to that exact proposal version; otherwise it returns `deferred` or `human_required` with the next resolving test. Input refs: the `proposal` version, the `review` version, the `approval` record that carries the delegation. Acceptance: `recommendation.md` states uncertainty and authority basis, no acceptance occurs outside delegation, and the W11 round count stays within the mode's `max_challenge_rounds`.

## Gates

The run can complete only when all of the following hold:

- `frame`, `resolve-unknowns` and `compare` each have an `accepted` task or a `satisfied_by_version_id` pointing at a current accepted artifact.
- `review` has a `review` record with `result` in {`ready`, `pass`}. This is the workflow's review gate.
- When `decide-or-test` is included, its task is `accepted`. A `deferred` or `human_required` decision is an accepted output; the run then completes with that limitation stated.
- No task is in `needs_input`, no output is `partial`, and the mode's wall-clock limit has not passed.

Review gates in W01 are `review` and, when W11 is invoked, W11's `judge-sufficiency` and `converge` stages. No stage in W01 requires independence at R0; when the recommended option raises the risk to R2, acceptance requires an independent review and attested human acceptance, which W11 and later W09 provide. Review and independence gates are never pruned, whatever artifacts already exist.

The registry's acceptance lines, and what each means at the gate: "No invented demand or outcomes" means every demand or outcome statement in the comparison carries an evidence ref or is typed hypothesis. "A viable non-AI option receives a fair comparison" means at least one non-AI option is scored on the same criteria as the AI option, with the same evidence standard. "Consequential recommendation records uncertainty and authority" means an R2 recommendation names what is unknown and who may decide it.

## Routing and pruning

A stage is satisfied without a model call when the case already holds an accepted artifact of its output kind whose inputs are unchanged. A current `context-brief.md` for the same case and scope prunes `frame`; a current `questions-and-decisions.md` whose open questions are unchanged prunes `resolve-unknowns`; a current `opportunity-comparison.md` whose input versions match prunes `compare`. The route plan records each as `satisfied_by_version_id`. The `review` stage is never pruned, and a pruned comparison still receives a fresh review.

Conditional specialists join under these conditions. The Customer Researcher joins when the review finds a demand claim without support and requests it. The Source Researcher joins when the review requests targeted research inside the authorized source scope. The Prioritization Analyst joins when the request asks to rank this opportunity against others or to sequence it. The Alternative Advocate joins inside W11 when `consequential_or_disputed` is true; that round counts against `max_challenge_rounds`. The Product Director joins only when the recommendation is R2 or higher and crosses team authority, or when W11 escalates to it.

A narrow request produces a narrow plan. "Summarize what we know about this workflow" yields a one-stage plan for `context-analyst`. "Is this one complaint evidence of demand?" yields `context-analyst` and `claim-checker`. Neither involves a manager, a judge or a director.

Budget modes: `focused` (4 tasks, 2 concurrent, 0 challenge rounds) fits the four unconditional stages with no retries and no specialists; use it for a well-documented workflow with a low-risk recommendation. `standard` (12 tasks, 3 concurrent, 1 round) is the default and leaves room for two research follow-ups, one rework attempt and one W11 round. `deep` (24 tasks, 3 concurrent, 2 rounds) is for an explicitly disputed decision. Typical task counts: 4 in focused, 6 to 9 in standard, 12 to 16 in deep when W11 runs two rounds. Every attempt and retry counts; the root orchestrator does not.

## Status handling and recovery

`needs_input`: the Interviewer's question is preserved verbatim on the task and the run moves to `needs_input`; accepted artifacts are kept. The user receives the exact question and, for each, the choice its answer changes. The answer is recorded in the case ledger as user input, the run returns to `planned`, and `resolve-unknowns` is re-planned with the answer as an input ref.

`blocked`: a required source or capability is unavailable (a source outside scope, a document that cannot be read). The task records the reason, and only independent work continues; for example, the comparison of options that do not depend on the missing source proceeds with the gap stated under `## Evidence required`. The user receives the unavailable capability or evidence and the action that would resolve it.

`failed`: receipts, if any, and the partial response are preserved; the orchestrator investigates within the remaining budget and retries only inside the work order's retry budget. Each attempt counts as a task.

`partial`: completed artifacts are stored and the run stays in `reviewing`; it cannot complete while a partial output exists. The user receives the complete artifacts, the incomplete one and what it lacks.

Budget exhaustion: admission is refused with `BudgetExhausted`. The user receives the accepted artifacts, the stages that remain, and a specific request to expand the mode or task count. The run never switches to `deep` on its own and never hides review work to fit. A W11 challenge triggered by risk that does not fit the budget requires explicit replanning or human approval to expand it.

In every case the packet says what is known, what is not, and the next resolving action.

## Authority boundary

W01 never deploys, publishes, sends, pays, deletes, broadens access or implements anything. It reads authorized sources and returns analysis. A recommendation at R0 is advice; acting on it is a separate request with its own workflow and gates.

When the recommended option would change who approves money, who contacts a customer or what data a feature may read, the proposal carries `requested_authority` R2. Accepting it requires an independent review and attested human acceptance through W11; the Decision Authority cannot grant itself that authority, and input recorded through the CLI is `attested=false` and cannot complete a protected transition. A favorable review from the Discovery Manager creates no authority of any kind; it says the analysis is sound, not that the team may proceed. Nothing in a completed W01 authorizes W04 to write code.

## Fixture

Scenario: "A team asks for an AI assistant to approve every support credit automatically, but supplies only one complaint." Expected behavior: "The result must not infer demand or automatic financial authority. It should compare draft assistance and ordinary rules, identify necessary evidence and preserve the approval question."

In the Larkspur Support case this is Reply Assist asked to approve credits on its own. The expected run produces a brief whose demand evidence is one complaint typed `observation`, an Interviewer question asking for credit volume and the current approval path, a comparison in which draft assistance with human approval and a fixed credit rule are scored beside the automatic approver, a review that returns `revise` or `ready` with a Customer Researcher follow-up, and a proposal with `requested_authority` R2 whose recommendation is a next test, not approval. The approval question stays open.

Fixture: `evals/workflows/assess-opportunity/fixture.json` records this scenario, its expected behavior and the acceptance lines. It has not been run against a model or a host.

## Invocation

Entry skill: `aipt-assess-opportunity`. It runs in your current session, never a forked one, and that session acts as the root orchestrator.

- Claude Code: `/aipt-assess-opportunity` followed by your request and the files or folders to use.
- Codex: `$aipt-assess-opportunity` followed by the same.
- Either host: describe the request in plain language; the `aipt-start` entry skill routes it here when it fits.

Example request: "Should we add an AI assistant that approves support credits automatically? Here is the complaint log and our credit policy."

Before dispatching any role, the session states the route plan: the stages it will run, the stages it will skip and why, the artifacts it will write, any missing input, and anything it will not do. Artifacts and the case ledger go under `aipt-cases/<case-id>/` in your project, as the `aipt-start` skill describes.

This release has no command-line controller. The record-keeping rules in this recipe (version binding, review independence, receipts, impact tracing) are followed by the orchestrating session as instructions; nothing enforces them in code. The experimental controller library in `src/` implements several of these rules in tested code, but it is not connected to either host.

## Live coverage

Per-host status is recorded in `docs/compatibility/`. As of this release, no workflow has been run end to end on either host, and this recipe's fixture is unrun.
