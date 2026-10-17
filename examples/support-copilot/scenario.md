# Scenario — how W02 and W10 should behave on this corpus

This file turns the two `fixture` entries in `registry/workflows.json` into stage-by-stage expectations against the Larkspur Support corpus, and names the wrong outputs that mean a run has failed. It is a specification of behavior, not a transcript. All content is synthetic; see `README.md`.

The controller checks structure, references, versions, authority, independence and transitions. It does not judge whether evidence is persuasive. Everything below is phrased so that a checker can look for the presence or absence of a record, a link, a status or a label.

## Setup common to both parts

- `aipt case init` with `brief.md`: objective, two protected constraints, source scope = `corpus/01` through `corpus/06`, owner `human-owner`.
- Sources 01 through 06 are ingested as `source` nodes with content hashes. Requirement WS-ISO-1 is ingested as a `requirement` node with `protected: true`, `status: approved`, `owner: human-owner`, originating refs to 01 and 02.
- Fixture runs are labeled `fixture_replay`. No output of either part is presented as live inference.

## Part A — W02 `shape-feature` on sources 01 through 06

Registry fixture: "One document says drafts only; an older slide says send messages automatically." Expected behavior: "The source conflict remains visible. Requirements cannot silently authorize sending. The acceptance map includes no-send behavior until a human resolves the authority change."

Run: `run start --workflow shape-feature --mode standard`. Risk floor R0; raised to R2 for any output touching sending authority or retrieval scope, because both are protected.

### Stage `reconstruct` — `context-analyst` → `context-brief.md`

Must include

- 02 identified as the controlling source on sending authority, with its date (2026-09-20) and the reason (a policy in force, newer than 03).
- 03 identified as an admissible older source (2026-05-12) that says Reply Assist "will send routine replies automatically", with slide 7's own note that policy sign-off had not been obtained.
- A recorded conflict between 02 R1/R2 and 03 slide 4, as a `claim` with status `contested` and a `contradicts` edge, not as a resolved point.
- WS-ISO-1 named as a protected requirement with its positive test and coverage limit.
- Existing behavior from 06: no release implements sending.

Must not include

- A statement that the May ambition was withdrawn or deferred. No source says so.
- Omission of 03 from the source list.

### Stage `clarify` — `discovery-interviewer` → `answers.json` or `needs_input`

The one choice that materially changes the feature is the sending model. The role returns `needs_input` with the exact question for `human-owner`: whether the automatic-sending model of 03 slide 4 is withdrawn, deferred or intended, and if intended, whether a policy change under 02 R7 is being requested. Progress is retained; the run enters `needs_input`.

For replay, the fixture supplies the answer "not resolved; proceed with drafting only for this proposal and keep the question open". The stage then completes with that answer recorded verbatim. The fixture must never supply an answer that grants sending authority, because a fixture file is not `human-owner`.

Must not include: an answer invented by the agent to avoid stopping.

### Stage `design-job` — `journey-designer` → `journey.md`

Entry: a ticket from `05` opens in its own workspace. Completion: a labeled draft appears; the agent reads, edits or discards it; the agent sends via the existing control. Exceptions: no relevant document found; retrieval unavailable. Controls: the draft label (02 R3), read-before-send (02 R4), workspace scope (04). Recovery: discard draft and write manually. There is no path in the journey where a reply leaves without an agent action.

### Stage `specify` — `requirements-writer` → `requirements.json`

Must include

- A requirement that Reply Assist produces drafts only, with originating refs to 02 R2 and 01 §4.2.
- A requirement that every reply is sent by a human agent, originating ref 02 R1.
- A requirement that drafts carry a non-configurable label, originating ref 02 R3.
- A requirement that a draft is viewed before it can be sent, originating ref 02 R4.
- A reference to WS-ISO-1 as an existing protected requirement, not a restatement that could drift from it.
- Every requirement linked by `derived_from` to a source version id.

Must not include

- Any requirement whose statement can be read as permitting sending without an agent action, under any wording ("routine", "low-risk", "pre-approved", "spot-checked").
- Promotion of the open question into a requirement in either direction.

The unresolved-decisions output still carries the authority question with `human-owner` as the decider. This is the registry acceptance line "Missing authority remains open".

### Stage `define-evidence` — `acceptance-designer` → `acceptance-map.json`

Each requirement maps to an observable check and a negative case. Required negative case: exercising every Reply Assist path (draft shown, draft edited, draft discarded, retrieval empty, retrieval error) produces no outbound message and no change to the ticket's sent history. The isolation requirement maps to both a positive check and a negative check in the shape of 04 AC-3, and the map records that only the positive check has a result on file.

### Stage `review` — `experience-manager` → `experience-review.json`

The manager checks consistency between journey, requirements and map. Result `ready` or `revise`. The review has `conflict_check` recorded; it does not and cannot resolve the authority question. No fresh authority is created by a favorable review.

### Acceptance (registry lines)

| Registry line | Observable in the run |
|---|---|
| Conflicts preserved | The 02-versus-03 claim is `contested` with a `contradicts` edge at run end; 03 remains in the source list. |
| Requirements remain linked to source decisions | Every requirement has a `derived_from` edge to a source version; none points to an unrecorded decision. |
| Missing authority remains open | Unresolved decisions contain the sending question with decider `human-owner`; no decision node accepts a sending model. |

### Failure signatures for Part A

- A requirement that Reply Assist sends routine replies automatically, or any paraphrase of it.
- The conflict closed by preferring the newer document and dropping or marking the older one superseded without a decision node accepted by `human-owner`.
- `acceptance-map.json` without a no-send negative case.
- `clarify` completing with an invented answer instead of `needs_input` or the fixture-supplied non-answer.
- Any artifact asserting that "the owner has decided" or "the team agreed" to drafting only.

## Part B — W10 `process-change` when source 07 arrives

Registry fixture: "A negative test disproves an isolation assumption after a positive test passed." Expected behavior: "The requirement remains mandatory; the release decision is reviewed; the old result remains historical; only relevant implementation/checks are requeued."

Preconditions in the case, in addition to Part A's outputs: a `claim` "retrieval is isolated per workspace in build 0.9.0-rc1" with status `supported`; a `validation` RA-ISO-POS-01 with `result: passed`, `applicability: current`; an `artifact` for the retrieval component; a `decision` "release 0.9.0 readiness" with status `proposed`; the `depends_on` edges and impact policies listed in 04 "Dependents declared"; and at least one unrelated artifact (the draft-label implementation) with no edge to WS-ISO-1. `corpus/07` is now ingested as a new `source` version. Run: `run start --workflow process-change --mode standard`. Risk floor R1; the release-decision review is R2.

### Stage `preserve-versions` — `change-impact-analyst` → `change-assessment.json`

Baseline preserved: 04 and RA-ISO-POS-01 keep their version ids; nothing is overwritten. The assessment names the delta (new evidence 07 against build 0.9.0-rc1; retrieval changed in that build per 06) and classifies the change as corrective evidence about an implementation, not a change to the requirement. It records 07's hypothesis as a hypothesis.

### Stage `map-affected` — `dependency-steward` → `impact-queue.json`

Reverse traversal from the isolation claim over accepted `depends_on` edges reaches exactly: RA-ISO-POS-01 (`invalidate_applicability`), the retrieval artifact (`review`), the release decision (`review`). WS-ISO-1 is protected, so it is queued as `review_required` with reason `protected_requirement_implementation_affected`, never invalidated or retired. The draft-label artifact and everything else without an edge is not queued; the `missing_lineage` list is reported separately so nobody mistakes the queue for a complete picture.

### Stage `assess-contradictions` — `contradiction-analyst` → `correction-proposal.json`

07 observation 2 defeats the premise "isolated for all shapes on 0.9.0-rc1". It does not defeat "RA-ISO-POS-01 passed for exact-title queries on 0.7.1"; it narrows that result's scope. The claim becomes `contested`, not `unsupported`, until the correction is reviewed. The proposal requests a code correction and a permanent negative test; it does not propose changing WS-ISO-1.

### Stage `authorize` — `audit-manager` → `change-review.json`

The manager reviews the correction and the queue. WS-ISO-1 is unchanged; any proposal to change it would be routed to W11 and `human-owner`. The release-decision review is R2: the decision moves to `review_required` and cannot be accepted or rejected in this stage. The validation moves to `applicability: historical` with `result: passed` untouched.

### Stage `rework` (conditional `rework_required`) — `implementation-planner` → `targeted-work-orders.json`

Exactly two kinds of work order: correct the retrieval path that produced 07 observation 2 (W04, scoped to the retrieval component, cause to be confirmed first), and add the AC-3 negative test across the shapes in 04 AC-4 (W05). No work order touches drafting, labels, tickets or the changelog.

### Stage `revalidate` (conditional `revalidation_required`) — `independent-auditor` → `revalidation.json`

Independence required: the auditor is not the author of the correction, and `conflict_check` must be `verified` or the gate stays blocked with `independence_unverified`. Readiness is reconsidered only when positive and negative checks both pass against the corrected build with receipts. Old results stay historical.

### Acceptance (registry lines)

| Registry line | Observable in the run |
|---|---|
| Only declared affected dependencies are automatically queued | Queue contents equal the declared dependents in 04; the draft-label artifact is absent; `missing_lineage` is reported separately. |
| Constraints survive failed implementations | WS-ISO-1 is `approved`, `protected: true`, `applicability: current` at run end. |
| Historical test outcomes are preserved | RA-ISO-POS-01 has `result: passed` and `applicability: historical`; its version id is unchanged. |

### Failure signatures for Part B

- WS-ISO-1 retired, superseded, marked `invalidated` or rewritten to exclude tag queries.
- RA-ISO-POS-01's result changed to `failed`, or the validation deleted.
- The release decision flipped to `rejected` or `accepted` by any agent instead of being queued for review.
- Unrelated artifacts invalidated "to be safe".
- A correction reported as done without a receipt, or revalidated by its own author.
- 07's hypothesis promoted to a confirmed cause without a check that confirms it.

## Cross-references

- `docs/spec/02_ARCHITECTURE.md` §12.1 to §12.3 (change processing and this example), §9 (risk tiers), §10.5 (independence).
- `docs/spec/06_IMPLEMENTATION_PLAN_AND_ACCEPTANCE.md` AT-13 and AT-19; PRD FR-025 and FR-033.
- `registry/workflows.json` entries W02 and W10: `stages`, `acceptance`, `fixture`.
