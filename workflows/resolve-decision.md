# W11 · Challenge this proposal and resolve the disagreement.

A versioned proposal is consequential, disputed or resting on thin evidence, and the user asks for it to be challenged and the disagreement resolved rather than argued further. The workflow freezes the decision packet, selects the smallest set of material challenges, lets the proposal's author answer them, rules on evidence sufficiency and on each contested issue, applies recorded delegation or asks the human, and records the decision with its dissent. It returns a decision, a deferment or an escalation, never a vote count.

Entry skill `aipt-resolve-decision` · Manager `review-manager` · Minimum risk R1 · Core cross-host release test yes

## Purpose and outcome

Other workflows produce proposals: W01 a recommendation, W07 a model decision proposal, W10 a correction, W12 an improvement. When a proposal is R2 or higher, when a challenge or dissent is unresolved, when authority or data boundaries change, or when the user asks for adversarial analysis, the controller routes it here (architecture section 10.1). The protocol follows architecture section 10.2: freeze, choose challenges, challenge, respond, judge sufficiency where contested, converge, apply authority, record.

The user receives three things. Challenge responses: each material objection with the premise it contests, the counterevidence or gap, the consequence, the resolving test and the author's answer or revision. Rulings: whether the evidence can carry the claim and which options remain acceptable under the frozen criteria. A decision or escalation: `accepted` within delegation, `rejected`, `deferred` with the next discriminating test, or `human_required` with a prepared acceptance request. Judgment and approval stay distinct: the judge says what the evidence supports; the decision authority says what delegation allows.

## Inputs

The user supplies the versioned proposal (a `proposal` node with `options`, `recommended_option`, `assumptions`, `evidence_refs`, `constraints`, `unresolved_questions`, `target_refs`, `author_role`, `requested_authority`), the options to be compared when the proposal does not already list them, the decision criteria, the evidence refs and the delegation record: an `approval` node with `granted_by`, `scope`, `allowed_decisions`, `bound_version_id`, `limits`, `expires_at` and `provenance`.

The case must already contain the proposal as an immutable version with its `author_role` recorded (the respond stage is bound to that role at runtime), the evidence as `source`, `claim` or `validation` versions, and any protected requirements the options could touch. Missing criteria stop the run before challenge: `needs_input` with "Which criteria decide this choice, in priority order, and which of them are constraints that no option may violate?" A missing delegation record does not stop the challenge rounds; it stops `apply-authority`, which returns `human_required` with the exact approval to grant. A proposal without `author_role` cannot bind the respond stage: `needs_input` with "Which role authored proposal version V? The respond stage is assigned to that role."

## Outputs

`decision-packet.json` (registry output: part of the admissibility rulings) — keys `objective`, `criteria` (ordered, each marked `constraint` or `preference`), `options`, `evidence_refs`, `constraints`, `proposal_version_id`, `author_role`, `author_session`, `delegation_ref`, `eligible_judges`, `excluded_reviewers` (each with a reason). Stored as an `artifact` node; it is the frozen input to every later stage.

`challenge-plan.json` — keys `round`, `max_rounds`, `challenges` (each `id`, `kind` among `premise`, `alternative`, `pre_mortem`, `red_team`, `assigned_role`, `contested_ref`, `why_material`), `omitted` (each `kind`, `reason`), `test_set`. Stored as an `artifact` node.

`assumption-challenge.json` and `alternative.json` — the `challenge` schema: `contested_ref`, `premise`, `counterevidence_or_gap`, `consequence`, `resolving_test`, `proposer_role`, `round`, `state`. `alternative.json` adds `alternative_option` (`id`, `summary`, `costs`, `limits`) compared under the same criteria. Stored as `challenge` nodes with state `open`; an empty material field is rejected at submission.

`challenge-response.json` (registry output: challenge responses) — keys `proposal_version_id`, `responses` (each `challenge_id`, `answer_kind` among `evidence`, `revision`, `reasoned_disagreement`, `evidence_refs`, `text`), `revised_proposal_version_id` when a revision was made, `preserved_versions`. Stored as an `artifact` node; a revision is a new `proposal` version with a `supersedes` edge, and the old version remains.

`evidence-ruling.json` (registry output: admissibility ruling) — the judge payload: `criteria`, `admissible_evidence`, `findings_per_objection`, `option_comparison`, `outcome` (`option_acceptable`, `option_rejected`, `insufficient_evidence`, `unresolved`, `next_test_required`), `uncertainty`, `next_checks`, `dissent_preserved`, `scope`. Stored as a `review` node with `evidence_sufficiency` set.

`judgment.json` (registry output: convergence ruling) — the same judge payload shape, with one finding per material issue and `acceptable_options` listed. Stored as a `review` node. A ruling changes no artifact or decision status by itself.

`decision.json` (registry output: decision or escalation) — the `decision` schema: `proposal_version_id`, `outcome` (`accepted`, `rejected`, `deferred`, `human_required`), `selected_option`, `criteria`, `rationale`, `dissent`, `authority_basis` (`kind`, `approval_version_id`), `revisit_conditions`, `status`. Stored as a `decision` node; `execution_permission` is `false` in the acceptance result.

`decision-brief.md` — headings Decision, Proposal version and authority basis, Criteria, Options considered, Challenges and responses, Rulings, Dissent preserved, Revisit conditions, Next action. Stored as an `artifact` node derived from the decision and review nodes.

## Work graph

| stage id | role | depends on | conditional predicate | artifact | review / independence | write scope |
|---|---|---|---|---|---|---|
| freeze | review-manager | — | — | decision-packet.json | — | proposal-only |
| choose-challenges | adversarial-orchestrator | freeze | — | challenge-plan.json | — | proposal-only |
| test-premise | assumption-challenger | choose-challenges | — | assumption-challenge.json | challenger is not the proposal author | proposal-only |
| alternative | alternative-advocate | choose-challenges | — | alternative.json | challenger is not the proposal author | proposal-only |
| respond | proposal-owner (runtime binding) | test-premise, alternative | — | challenge-response.json | — | proposal-only |
| judge-sufficiency | evidence-judge | respond | material_conflict | evidence-ruling.json | review gate | proposal-only |
| converge | convergence-judge | respond; judge-sufficiency when present | — | judgment.json | review gate | proposal-only |
| apply-authority | decision-authority | converge | — | decision.json | — | proposal-only |
| record | decision-recorder | apply-authority | — | decision-brief.md | — | proposal-only |

`test-premise` and `alternative` receive the same decision packet and run in parallel; both must be submitted before `respond` is ready. A second round, when the mode allows it, repeats `choose-challenges` through `respond` with `round` set to 2 before `converge` runs. The root orchestrator dispatches every task; the adversarial-orchestrator returns the plan and never spawns challengers itself.

## Stage procedures

### freeze
The review-manager (`agents/review-manager.md`) receives the proposal version, the author identity, the evidence refs, the criteria and the delegation record. It applies `aipt-method-evidentiary-adjudication` to state the criteria in a form a judge can rule on, `aipt-method-structural-integrity-audit` to find missing evidence, missing alternatives and contradictions in the packet, and `aipt-method-independent-audit` to check judge eligibility: no judge or challenger may have authored the proposal or share its session. The proposal author does not choose the judges. Accepted when every criterion is ordered and typed, every option is comparable under them, and `eligible_judges` excludes the author.

### choose-challenges
The adversarial-orchestrator (`agents/adversarial-orchestrator.md`) receives the frozen packet and the run's `max_challenge_rounds`. It applies `aipt-method-adversarial-challenge` to select challenges that are independent of each other and materially different, `aipt-method-milestone-planning` to bound them as work orders, and `aipt-method-evidentiary-adjudication` to choose the smallest test set that could decide the contested points. Pre-mortem and red-team challenges are added only when the packet shows a release or boundary risk that the two default challengers cannot reach. Accepted when each selected challenge names its contested ref and why it is material, omitted kinds carry reasons, and the plan fits the round budget.

### test-premise
The assumption-challenger (`agents/assumption-challenger.md`) receives the packet, not a directive to defeat the option. It applies `aipt-method-adversarial-challenge` to name one consequential premise the recommendation depends on, `aipt-method-discovery-interrogation` to find the implicit assumptions behind it, and `aipt-method-evidence-and-lineage` to cite the records that would confirm or kill it. The output states premise, counterevidence or gap, consequence and a falsification test that can be run. Accepted when all five material fields are non-empty and the resolving test is observable; an untestable worry is not a challenge.

### alternative
The alternative-advocate (`agents/alternative-advocate.md`) receives the packet and the objective. It applies `aipt-method-adversarial-challenge` to frame the alternative as a challenge, `aipt-method-research-consolidation` to gather its evidence with provenance, and `aipt-method-ai-responsibility-allocation` to include the simpler option of less model judgment or none. The alternative is scored under the frozen criteria, with costs, limits and one discriminating test against the recommended option. Accepted when the objective is unchanged, every criterion is addressed and no favorable evidence is invented.

### respond
The `proposal-owner` is not a catalog role. The registry binds it at runtime (`role_binding: runtime`) to the `author_role` of the frozen proposal version, so the controller assigns this task to that role's body under `agents/<author_role>.md`, and the author answers with that role's own skills. It receives the open challenges and the alternative, and for each returns evidence, a revision or a reasoned disagreement. A revision is a new proposal version with a `supersedes` edge; the frozen version and every earlier one remain readable, and a material revision invalidates any earlier approval's applicability. Accepted when every challenge has a response of a named kind, cited evidence exists in the case, and `preserved_versions` lists the superseded versions.

### judge-sufficiency
The evidence-judge (`agents/evidence-judge.md`) runs only when `material_conflict` is true: two or more admissible records contradict each other on a point that affects the output. It receives the contested claims, the source passages and the evaluation limits and applies `aipt-method-evidentiary-adjudication` to rule on sufficiency and admissibility, `aipt-method-evidence-and-lineage` to trace each claim to its support, `aipt-method-evaluation-planning` to read evaluation results within their frozen scope and `aipt-method-research-consolidation` to weigh sources by authority and date. It judges only the stated claim in its scope and returns `insufficient_evidence` where support cannot carry the claim. Accepted when every contested objection has a finding and the ruling does not extend beyond the claims put to it.

### converge
The convergence-judge (`agents/convergence-judge.md`) receives the packet, the challenges and responses, the evidence ruling when one exists, and the criteria. It applies `aipt-method-evidentiary-adjudication` to resolve each material issue by admissible evidence and criteria, `aipt-method-adversarial-challenge` to check that each challenge was answered on its own terms, and `aipt-method-evidence-and-lineage` to bind findings to versions. It identifies acceptable options or names the one discriminating test that would decide; it may return `unresolved` rather than manufacture consensus. Accepted when each material issue has a finding, the recommended option or deferment follows from the findings, dissent is preserved verbatim and no vote count appears as a reason.

### apply-authority
The decision-authority (`agents/decision-authority.md`) receives the judgment, the constraints, the delegation record and the exact proposal version. It applies `aipt-method-delegated-authority` to check that the delegation is bound to this version, not revoked or expired, and covers the requested authority, and `aipt-method-evidentiary-adjudication` to confirm the judgment supports the selected option. Within delegation at R1 it accepts; at R2 or above, or outside delegation, it returns `human_required` with the approval to request; where the judgment is unresolved it returns `deferred`. Accepted when `authority_basis` names an approval version or the outcome is `human_required` or `deferred`, and no acceptance cites a judge's confidence as authority.

### record
The decision-recorder (`agents/decision-recorder.md`) receives the decision event, the alternatives, the evidence and the dissent. It applies `aipt-method-evidence-and-lineage` to bind the record to the exact proposal version and authority basis, `aipt-method-delegated-authority` to state what the acceptance permits and does not, and `aipt-method-status-handoff` to write the brief. Rejected alternatives, unresolved matters and revisit conditions are kept; an approval for version one is never applied to version two. Accepted when the brief cites the version id, the authority basis and the dissent, and the dependency-steward can link the decision to downstream work.

## Gates

The run completes only when every unconditional stage has an `accepted` task or a `satisfied_by_version_id`; `converge` and, when `material_conflict` is true, `judge-sufficiency` each have a `review` node with result `ready` or `pass`; no judge authored the proposal and no judge shares a session with the author; no output is `partial`; and no `needs_input` is open. `judge-sufficiency` and `converge` are the review gates. Independence is enforced on both judges and both challengers by the author check at admission; where a host cannot show a fresh session, the review carries `conflict_check` `unverified` and a gate that needs independence stays blocked. Review and independence gates are never pruned.

Two challenge rounds are the default ceiling. The run's mode sets `max_challenge_rounds` (focused none, standard one, deep two), and `open_challenge` refuses a round beyond it. The run stops sooner when every material objection is resolved or when one discriminating test is more useful than another round. At the ceiling the outcome is `deferred`, `human_required` or `unresolved` with the next evidence named; agreement is not mandatory.

The registry acceptance lines are checked against the stored records: maximum two challenge rounds by default; no majority-vote truth; unresolved and defer are valid outcomes; judgment and approval are distinct.

## Routing and pruning

A stage is satisfied without a model call when a current accepted artifact exists for the same proposal version: a decision packet frozen for version V satisfies `freeze` for a rerun on V; challenges already answered on V are not reissued, and a second round selects new material objections only. A revision to V+1 invalidates the packet and the rounds restart against the new version. Rulings are never carried from one version to another.

Conditional specialists join for an identified gap: evidence-judge on `material_conflict`; pre-mortem-analyst when the recommended option carries a release or operational risk the packet does not test; red-team-tester when an option changes an authority or data boundary; dissent-recorder when `converge` leaves a minority objection unresolved; product-director when the criteria themselves are disputed and the human owner has delegated their ordering. Each addition consumes a worker slot and is listed in the route plan with its reason.

A narrow request stays narrow. "Is this one assumption safe?" routes to assumption-challenger plus convergence-judge on a frozen packet and does not open the full graph. "Record this decision the owner already made" routes to decision-recorder alone, with the attested approval as input.

Budget guidance: focused (4 tasks, zero rounds) cannot run this workflow; a risk-triggered challenge in a focused run requires explicit replanning to standard or human approval to expand. Standard (12 tasks, one round) is the default: eight or nine tasks for one round. Deep (24 tasks, two rounds) is for a disputed decision that needs a second round, about thirteen tasks. The run never switches mode on its own.

## Status handling and recovery

`needs_input`: the task and run move to `needs_input` with the exact question preserved, for example "Does the owner's delegation cover changing the reply policy from drafts only, or is that reserved to the owner?" Completed stages stay accepted; the run returns to `planned` when `aipt decision record-user-input` stores the answer.

`blocked`: the task names the unavailable capability or evidence, such as a cited evaluation with no receipt or a host that cannot create a fresh judge context, and the run continues only the stages that do not depend on it. The user receives the packet, the challenges so far and the blocker.

`failed`: receipts and partial challenge records are preserved and the failure is investigated within the remaining budget; a retry is a new attempt that counts against `max_worker_tasks` and, for challenge stages, against `max_challenge_rounds`.

`partial`: challenges and rulings that were completed stay stored, the run is not promoted to `completed`, and the brief lists the open issues under `limitations`.

Budget exhaustion at the round ceiling returns `deferred`, `human_required` or `unresolved` with the next evidence to obtain; at the task ceiling it returns the rulings so far and a specific request to expand scope. The run never adds a round silently. In every case the user receives what was contested, what was resolved, what remains open and the next resolving action.

## Authority boundary

This workflow never deploys, publishes, sends, pays, deletes or broadens access, and accepting a decision is not permission to execute anything: the acceptance result carries `execution_permission: false`. The decision-authority accepts only within a recorded delegation bound to the exact proposal version; at R2 it returns `human_required`, and a human acceptance counts only when its provenance is attested by the host, not when it arrives through the command line or a file. Judges rule; they do not approve. Challengers object; they do not decide. The review-manager's favorable packet and any manager's favorable review create no authority and do not substitute for the independence the gates require. A protected constraint such as "drafts only" cannot be waived by this workflow at all; changing it is a requirement change with its own human acceptance.

## Fixture

Scenario: three agents prefer option A, one points to a decisive violation of a protected constraint. In the Reply Assist case, option A lets the assistant send short acknowledgment replies without review to cut handling time, citing the older slide that says "send automatically"; three roles favor it on the speed criterion, and the assumption-challenger shows that current policy, a protected requirement, says drafts only and that the slide is superseded.

Expected behavior: the convergence-judge rules on the violation under the constraint criterion and does not count preferences; option A is `option_rejected`, or the question is `deferred` with the superseding record as the next check if the policy's status is itself unclear. The decision-authority does not accept A under any delegation. The dissent and the three preferences are recorded verbatim.

Path: `evals/workflows/resolve-decision/fixture.json`. A replay of this fixture through the controller is labeled `fixture_replay` and is not a live run.

## Invocation

Entry skill: `aipt-resolve-decision`, loaded in the root session; it never runs in a forked context.

- `aipt run start --case CASE --workflow resolve-decision --mode standard` creates the run in `scoped` with one challenge round and twelve worker tasks available.
- `aipt run plan --run RUN` stores the route plan with the frozen proposal version, the included and omitted challenge kinds and the predicate values.
- `aipt task next --run RUN` lists ready tasks whose dependencies are accepted; `test-premise` and `alternative` appear together.
- `aipt task admit --task TASK` runs the admission checks, including the author check for judges and challengers and the round budget for challenge stages, and mints the work order; for `respond` the role is the proposal's `author_role`.
- `aipt task attach --task TASK --native-child-id CHILD` records the fresh child id used to show judge and challenger independence.
- `aipt task submit --task TASK --response response.json` validates the envelope and stores challenges, responses and rulings as proposed versions.
- `aipt review submit --run RUN --record review.json` records the evidence ruling or the judgment as a review node with its conflict check.
- `aipt decision propose --run RUN --record decision.json` stores the decision in status `proposed` for the decision-authority.
- `aipt decision record-user-input --run RUN --record user-input.json` records the human owner's acceptance or answer with `channel` and an `attested` flag set by the controller, never by the caller.
- `aipt case report --case CASE --format markdown` renders active decisions with dissent, unresolved questions and the next action from stored state.

## Live coverage

| host | fixture_replay | native | last run |
|---|---|---|---|
| host adapter A | not yet run | not yet run | — |
| host adapter B | not yet run | not yet run | — |

Rows are keyed by the adapter id recorded on the run. This table is updated only from recorded runs.
