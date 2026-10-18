# W02 · Turn these documents into a feature proposal.

A team hands over a corpus (specifications, decision notes, slides, policy pages, support transcripts) and a problem statement, and asks for a feature proposal it can review. This workflow returns requirements linked to the sources and decisions they come from, a journey that covers entry, completion, exceptions, controls and recovery, an acceptance map that gives each requirement an observable check and a negative case, and an explicit list of the decisions the documents do not settle.

Entry skill `aipt-shape-feature` · Manager `experience-manager` · Minimum risk R0 · Core cross-host release test yes

## Purpose and outcome

W02 converts a body of documents into a proposal without converting any proposal inside those documents into an approval. The outcome is a set of artifacts the case owner can accept, revise or send to W11: `journey.md`, `requirements.json`, `acceptance-map.json`, and the open decisions carried in `answers.json` and the review record. Where two sources disagree, both remain visible and the requirement that depends on them stays in its safe form until a decision is recorded.

The run completes when the five authoring stages are accepted and the Experience Manager's review record reads `ready`. Completion means the proposal is internally consistent and traceable, not that the feature is approved, designed or built; W03 designs it and W04 builds a bounded version, each behind its own gates.

Example. Larkspur Support supplies the Reply Assist policy page ("drafts only; an agent sends"), an older launch slide ("send replies automatically for simple cases") and a workspace isolation note separating `ws-alpha` from `ws-beta`. W02 produces requirements for drafting, agent review and isolation, keeps the send question open with both sources cited, and puts a no-send check into the acceptance map.

## Inputs

The user supplies three things: the authorized corpus (every document the roles may read, each a `source` record with an access scope and a version), the problem (what the feature should change and for whom), and answers to material questions, either up front or when the Clarify stage asks. The user may also point at an existing `context-brief.md` from W01, which the Reconstruct stage reuses when its source scope matches.

The case must already contain a case brief with objective, protected constraints, source scope and owner. Protected constraints named in the brief (for Reply Assist: no send without a human action; no cross-workspace exposure) are protected requirements from the start. W02 can restate them and map checks to them; it cannot weaken them.

| Missing | Behavior |
|---|---|
| Corpus empty or outside scope | `blocked`: "No authorized sources are in the case scope. Add the documents as sources, or widen the scope in the case brief." |
| Problem | `needs_input`: "What should change for the people who use this feature, and what would tell you it has changed?" |
| Answer to a material question | `needs_input` from the Clarify stage with the exact question and the choice it decides; the run waits. |
| Owner of a requirement | The Requirements Writer records `owner: human-owner` and lists the requirement under open decisions rather than inventing an owner. |
| Authority of a source | The Context Analyst types the dependent statement `hypothesis`; the Contradiction Analyst joins if another source contradicts it. |

## Outputs

Source-linked requirements: `requirements.json`, keys `requirements` (each with `id`, `statement`, `owner`, `acceptance_criteria`, `protected`, `originating_refs`, `status`), `exclusions`, `open_decisions_referenced`. Stored as an `artifact` (status `proposed`); each entry is also proposed as a `requirement` record with status `proposed` and a `derived_from` edge to its originating source or decision version.

Journey: `journey.md`, headings `## Actors and entry`, `## Successful completion`, `## Exceptions`, `## Controls and correction`, `## Recovery and handoff back to people`, `## Outside the AI interaction`. Stored as an `artifact`.

Acceptance map: `acceptance-map.json`, keys `entries` (each with `requirement_id`, `check`, `observable`, `negative_case`, `refusal_behavior`, `unknown_outcome`, `method`), `uncovered_requirements`, `checks_not_yet_runnable`. Stored as an `artifact`; each entry becomes a `validation` record with result `not_run` until W04 or W05 executes it.

Unresolved decisions: the `open_decisions` array of `answers.json` (each with `id`, `question`, `changes`, `options`, `protected`, `requires`) together with the `unresolved` array of `experience-review.json`. Both travel with their parent records and surface in the case report under unresolved questions.

Supporting records: `context-brief.md` (headings `## Current job`, `## Controlling sources`, `## Conflicts`, `## Inherited decisions`, `## Existing behavior`, `## Open questions`; stored as an `artifact` with its statements proposed as `claim` records) and `experience-review.json` (keys `reviewed_refs`, `reviewer_role`, `reviewer_session`, `findings`, `evidence_sufficiency`, `result`, `conflict_check`, `unresolved`; stored as a `review` record).

## Work graph

| Stage id | Role | Depends on | Conditional predicate | Artifact | Review / independence | Write scope |
|---|---|---|---|---|---|---|
| `reconstruct` | `context-analyst` | — | — | `context-brief.md` | no / no | proposal-only |
| `clarify` | `discovery-interviewer` | `reconstruct` | — | `answers.json` | no / no | proposal-only |
| `design-job` | `journey-designer` | `clarify` | — | `journey.md` | no / no | proposal-only |
| `specify` | `requirements-writer` | `design-job` | — | `requirements.json` | no / no | proposal-only |
| `define-evidence` | `acceptance-designer` | `specify` | — | `acceptance-map.json` | no / no | proposal-only |
| `review` | `experience-manager` | `define-evidence` | — | `experience-review.json` | review gate / manager review, `independent=false` | proposal-only |

The stages are sequential. `specify` follows `design-job` because requirements must cover the exceptions and recovery paths the journey names. Two conditional specialists can run alongside: the Contradiction Analyst, when `material_conflict` is true, runs in parallel with `clarify` since both read the accepted brief; the Evidence Linker, when it joins, runs after `specify` in parallel with `define-evidence`.

## Stage procedures

### reconstruct

The Context Analyst (`agents/context-analyst.md`) applies `aipt-method-corpus-grounded-onboarding` to the corpus to identify which source controls each topic, where sources conflict, which decisions were made earlier and what the product does today, and `aipt-method-status-handoff` to keep the brief derived and short. A conflict between sources is recorded as two claims with a `contradicts` relation, never resolved by picking the newer or the more emphatic one. Input refs: the case brief, every `source` version in scope, any W01 brief for the same case. Acceptance: each controlling source is named per topic, each conflict appears under `## Conflicts` with both refs, and an older document is marked inherited rather than current.

### clarify

The Discovery Interviewer (`agents/discovery-interviewer.md`) applies `aipt-method-discovery-interrogation` to the brief's open questions and keeps those whose answer changes the feature materially: what it does, who controls it, what it may touch. Each kept question states the choice it decides. A question whose answer is in the corpus is not asked. A question that would resolve an authority change (sending, access) is recorded as an open decision with `requires: human-owner`, because the Interviewer collects answers and does not accept them. The stage returns `needs_input` with the exact question when an answer is missing. Input refs: the accepted brief. Acceptance: no asked question duplicates supplied facts, every open decision has `changes`, `options` and `requires`, and no answer is invented.

### design-job

The Journey Designer (`agents/journey-designer.md`) applies `aipt-method-ux-direction-synthesis` to turn the brief and answers into the job as people do it, and `aipt-method-accessible-interaction-design` for the controls and correction paths they need. The map shows what happens before the feature is invoked, the successful path, each exception, the controls a person has over the output, recovery when the output is wrong, and the handoff back to people. It does not assume a clean prompt or perfect data at entry. Input refs: the accepted brief and `answers.json`. Acceptance: every section is present, every exception names its recovery, and every control names who operates it.

### specify

The Requirements Writer (`agents/requirements-writer.md`) applies `aipt-method-requirements-and-acceptance` to write atomic, versioned requirements, and `aipt-method-corpus-grounded-onboarding` to keep each one traceable to its origin. Only accepted choices become requirements. An open decision becomes an entry in `open_decisions_referenced`, and the requirement that depends on it is written in its safe form (for Reply Assist: "the system produces a draft and takes no send action") with the open decision cited. Protected constraints from the case brief carry `protected: true`. Input refs: the accepted journey, `answers.json`, the brief. Acceptance: each requirement has one testable statement, an owner and non-empty `originating_refs`; no proposed behavior is promoted to approved; exclusions are explicit.

### define-evidence

The Acceptance Designer (`agents/acceptance-designer.md`) applies `aipt-method-requirements-and-acceptance` to map each requirement to an observable check, and `aipt-method-evaluation-planning` to freeze what counts as a pass before any result exists. Every entry carries a negative case and the correct refusal behavior; a response existing is never the check. Where a requirement cannot yet be checked, it is listed under `checks_not_yet_runnable` with what is missing. Input refs: the accepted `requirements.json` and `journey.md`. Acceptance: every requirement has an entry or appears under `uncovered_requirements`, every protected requirement has a negative case, and no check depends on a tool the capability report does not list.

### review

The Experience Manager (`agents/experience-manager.md`) applies `aipt-method-ux-direction-synthesis`, `aipt-method-requirements-and-acceptance` and `aipt-method-accessible-interaction-design` to check consistency across the three artifacts: each journey step has requirements, each requirement has a check, failure and recovery are covered, and open decisions are still open. It returns a `review` record with `result` in `ready`, `revise`, `blocked` or `escalate`, and targeted revisions as work orders. A happy-path-only proposal comes back as `revise`. The manager leads the authoring team, so the record carries `independent=false`. Input refs: the accepted journey, requirements and acceptance map. Acceptance: a result is recorded, each finding points at a ref, and every unresolved decision from `answers.json` appears in `unresolved`.

## Gates

The run can complete only when:

- `reconstruct`, `clarify`, `design-job`, `specify` and `define-evidence` each have an `accepted` task or a `satisfied_by_version_id` pointing at a current accepted artifact.
- `review` has a `review` record with `result` in {`ready`, `pass`}. This is the workflow's review gate.
- No task is in `needs_input`, no output is `partial`, and the mode's wall-clock limit has not passed.

W02 has one review gate, `review`, and no stage requiring independence at R0. When the corpus shows that the feature changes a protected constraint, the predicate `changes_protected_scope` raises the run to R2; that change becomes a decision for W11 and attested human acceptance, and an independent review is required before any protected requirement is altered. Review and independence gates are never pruned, whatever artifacts already exist.

The registry's acceptance lines, and what each means at the gate: "Conflicts preserved" means every source conflict in the brief is still visible in the requirements or the open decisions. "Requirements remain linked to source decisions" means every requirement has non-empty `originating_refs` resolving to a source or decision version. "Missing authority remains open" means no requirement authorizes an action (sending, access, payment) that no accepted decision authorizes.

## Routing and pruning

A stage is satisfied when a current accepted artifact of its kind exists for the same case and its inputs are unchanged. A W01 `context-brief.md` with the same source scope prunes `reconstruct`. An `answers.json` whose questions still match the brief's open questions prunes `clarify`. A `journey.md` or `requirements.json` from an earlier W02 run prunes its stage only if every input version it cites is still current. The route plan records each as `satisfied_by_version_id`. The `review` stage is never pruned; a run with four pruned stages still ends in a fresh review of the current artifacts.

Conditional specialists join under these conditions. The Contradiction Analyst joins when `material_conflict` is true, to explain whether the sources actually disagree or differ in scope or date; its `conflicts.json` feeds `clarify`. The Interaction Designer joins when the journey introduces a control surface people operate (approving, editing or discarding a draft). The Accessibility Reviewer joins when user-facing controls are specified, as a review criterion on the journey. The Evidence Linker joins when `specify` leaves requirements with missing or weak `originating_refs`, to propose links for semantic review.

A narrow request produces a narrow plan. "Rewrite requirement R-04 for clarity" yields `requirements-writer` and `change-impact-analyst` only; if the rewrite changes a permission semantically, the plan escalates even though the wording change is small. "Which of these documents is current?" yields `context-analyst` alone. Neither involves a director.

Budget modes: `focused` (4 tasks, 2 concurrent, 0 challenge rounds) cannot hold all six stages and fits only when at least two are satisfied by current artifacts; `standard` (12 tasks, 3 concurrent, 1 round) is the default and fits the six stages plus two specialists and one rework; `deep` (24 tasks, 3 concurrent, 2 rounds) is for a corpus with several material conflicts that need W11. Typical task counts: 2 to 4 in focused with pruning, 6 to 9 in standard, 10 to 15 in deep. Every attempt and retry counts; the root orchestrator does not.

## Status handling and recovery

`needs_input`: `clarify` preserves each question verbatim and the run moves to `needs_input`; the brief and any accepted artifacts are kept. The user receives the questions, each with the choice it decides and the options. Answers are is recorded in the case ledger as user input; an answer that changes a protected constraint is recorded as input, not as acceptance of that change. The run returns to `planned` and `clarify` is re-planned with the answer as an input ref.

`blocked`: a document in scope cannot be read, or a requirement needs a source outside scope. The task records the unavailable source, and stages that do not depend on it continue; requirements that depend on it are written as open decisions. The user receives the missing source and the action that would unblock it.

`failed`: the partial response and any receipts are preserved; the orchestrator investigates within the remaining budget and retries only inside the work order's retry budget. Each attempt counts as a task.

`partial`: a stage that covers part of its scope (an acceptance map with uncovered requirements) is stored, and the run stays in `reviewing` until the gap is closed or the review records it as a stated limitation. The user receives what is covered and what is not.

Budget exhaustion: admission is refused with `BudgetExhausted`. The user receives the accepted artifacts, the stages not yet run and a specific request to expand the mode or task count. The run never moves to `deep` on its own and never skips the review to fit. A W11 challenge triggered by risk that does not fit the budget requires explicit replanning or human approval to expand it.

In every case the packet says what is known, what is not, and the next resolving action.

## Authority boundary

W02 never deploys, publishes, sends, pays, deletes or broadens access, and it writes nothing outside `proposals/`. Its requirements are proposals until the human owner accepts them; its acceptance map describes checks and runs none of them.

A requirement cannot authorize what no decision authorized. When the corpus contains an authority change (the older slide's "send automatically"), the change is recorded as an open decision with `protected: true` and `requires: human-owner`; resolving it is W11's job, and acceptance needs attested human input, which the CLI cannot supply (`attested=false`). The Experience Manager's `ready` says the proposal is consistent; it grants no authority over the feature's behavior, and nothing in a completed W02 permits W04 to implement.

## Fixture

Scenario: "One document says drafts only; an older slide says send messages automatically." Expected behavior: "The source conflict remains visible. Requirements cannot silently authorize sending. The acceptance map includes no-send behavior until a human resolves the authority change."

In the Larkspur Support case the policy page and the older slide conflict on whether Reply Assist may send. The expected run records both as claims with a `contradicts` relation, asks the owner which governs only if the policy page's authority does not already settle it, writes the drafting requirement in its no-send form with both refs, lists the send question under `open_decisions` as protected and requiring `human-owner`, and gives the acceptance map an entry whose negative case is "a send action is attempted; expected: refused and logged". The review returns `ready` with the send decision in `unresolved`.

Fixture: `evals/workflows/shape-feature/fixture.json` records this scenario, its expected behavior and the acceptance lines. It has not been run against a model or a host.

## Invocation

Entry skill: `aipt-shape-feature`. It runs in your current session, never a forked one, and that session acts as the root orchestrator.

- Claude Code: `/aipt-shape-feature` followed by your request and the files or folders to use.
- Codex: `$aipt-shape-feature` followed by the same.
- Either host: describe the request in plain language; the `aipt-start` entry skill routes it here when it fits.

Example request: "Turn the documents in docs/reply-assist/ into a feature proposal with requirements and acceptance checks."

Before dispatching any role, the session states the route plan: the stages it will run, the stages it will skip and why, the artifacts it will write, any missing input, and anything it will not do. Artifacts and the case ledger go under `aipt-cases/<case-id>/` in your project, as the `aipt-start` skill describes.

This release has no command-line controller. The record-keeping rules in this recipe (version binding, review independence, receipts, impact tracing) are followed by the orchestrating session as instructions; nothing enforces them in code. The experimental controller library in `src/` implements several of these rules in tested code, but it is not connected to either host.

## Live coverage

Per-host status is recorded in `docs/compatibility/`. As of this release, no workflow has been run end to end on either host, and this recipe's fixture is unrun.
