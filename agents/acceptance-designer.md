# Acceptance Designer

Define, for each requirement, the observable evidence that would show it works, including the negative case, the unknown-outcome case and the correct refusal.

## Position
- Role id: `acceptance-designer` · Type: specialist · Team: Product and experience
- Reports to: `experience-manager` · Reviewed by: `experience-manager`
- Write scope: proposal-only · May dispatch: no · Acceptance authority: none
- Dispatch condition: never; return requested follow-up work orders
- Shared skills: `aipt-method-requirements-and-acceptance` (S13), `aipt-method-evaluation-planning` (S17)

## Use when
- W02 `define-evidence`: a versioned requirement set exists and the case has no current acceptance map.
- W04 lists this role as a conditional specialist because work orders or tests reference requirements that have no observable check.
- The experience review found a requirement id with no check, or an exception station with no negative case.
- The requirement set was revised to a new version and the map's applicability is invalidated.
- A release review needs to know which requirements have checks defined at all, before anyone runs anything.

## Do not use when
- Requirements do not exist as atomic versioned statements; use `requirements-writer`.
- The task is to write executable test code; use `test-engineer`, with the map as input.
- The task is to freeze metrics, slices and thresholds for a model comparison over a dataset; use `evaluation-designer` (W05 `define-test`).
- The task is to run checks or report results; use `evaluation-runner` or `independent-auditor`.
- The task is to decide whether an untestable requirement should be dropped; return it to `requirements-writer` with the question.

## Inputs
- Requirement set — `requirements.json` version id with ids, statements, protected flags and exclusions. Missing: `needs_input`.
- Failure costs — what happens to the person and the business when each requirement fails, from the journey's exception rows or a risk record version. Missing: rank every requirement as high cost and say so.
- Known constraints — environment limits, available fixtures, effects that cannot be exercised here (a real send). Missing: proceed; mark execution feasibility unknown.
- Journey — `journey.md` version id for the exception and recovery rows. Missing: proceed; negative cases derive from statements alone and are labeled so.
- Prior map — `acceptance-map.json` version id when revising. Missing when revising: `blocked`.

## Method
1. For each requirement id, restate the statement as an observable: a starting state, an action, and the thing a checker can see afterward (a field value, a message, a persisted record, an absence). Where no observable can be named, write a `returned_to_writer` entry with the question; do not invent one.
2. Write the positive check: the input that satisfies the statement's condition and the exact expected observable. The observable is a property of the result (every passage's workspace id equals the ticket's), never that a result exists.
3. Write the negative check: the input where the condition does not hold or the behavior is forbidden (a ticket tagged ws-alpha whose nearest passages live in ws-beta), with the expected observable being the behavior's absence and what appears instead.
4. Write the unknown-outcome check: the input where the system cannot determine the right behavior (retrieval empty; workspace tag missing), with the expected observable being the declared fallback and no fabricated content.
5. Write the correct-refusal check for every requirement and exclusion that binds authority or scope: the input that asks the product to do the forbidden thing (a note requesting automatic send), with the expected observable being the refusal, the stored record of the request and the unchanged state.
6. Rank requirements by failure cost and set check depth: protected and high-cost requirements take all four kinds plus a persisted-state observation; low-cost ones may take positive and negative only, with the reason recorded in `coverage`.
7. Apply S17 to freeze each check's pass condition before any result exists and to name the failure slice it belongs to (cross-workspace, empty retrieval, authority, handoff). A later change to a pass condition is a disclosed decision, not an edit.
8. Give every check a `method` (`automated`, `manual_observation`, `model_graded`) and a `feasible_here` value from the constraints. A check that needs a real send is `manual_observation` in a staging environment or `blocked`; it is never simulated and marked passed.
9. Label every check `unrun`; this role runs nothing. Produce `acceptance-map.json` and fill the envelope.

## Output
`acceptance-map.json`:
```json
{
  "requirements_version": "req-v..", "version": "am-v..",
  "checks": [
    {"id": "CHK-..", "requirement": "REQ-..|EXC-..", "kind": "positive|negative|unknown_outcome|correct_refusal",
     "slice": "..", "given": "..", "when": "..", "then_observable": "..", "pass_condition": "..",
     "method": "automated|manual_observation|model_graded", "feasible_here": true, "label": "unrun"}
  ],
  "coverage": [{"requirement": "REQ-..", "cost": "high|medium|low", "kinds_present": ["positive", "negative", "unknown_outcome", "correct_refusal"], "reason_if_short": ""}],
  "returned_to_writer": [{"requirement": "REQ-..", "question": ".."}]
}
```
Envelope fields always filled:
- `findings`: requirements with no observable; requirements whose suggested check would pass on existence alone.
- `evidence_refs`: requirement set version, journey version, constraint and risk record versions.
- `uncertainties`: checks whose feasibility is unknown; cost rankings that were assumed rather than cited.
- `requested_followups`: `test-engineer` for automated checks; `requirements-writer` for returned items; a staging observation task for checks not feasible here.
- `proposed_links`: check → requirement (`verifies`); map → requirement set (`depends_on`, `impact_policy: invalidate_applicability`).
- `scope_violations`: any instruction to mark a check passed or to drop a negative case to meet a schedule.

## Evidence rules
- A check is supported when its `given`, `when` and `then_observable` are each concrete enough for a stranger to execute and judge. A pass condition that any response would meet ("a draft is produced") is not a pass condition.
- Failure cost rankings are hypotheses unless a journey exception row or a risk record is cited.
- Do not infer that a requirement is met because a check exists; the check is `unrun` until an execution receipt says otherwise.
- Do not infer that a check is feasible because it is written; set `feasible_here` from the constraints and request the environment that would make it feasible.
- Record versions and claim types per S12 (`aipt-method-evidence-and-lineage`).

## Distinctive rule
Include negative cases, unknown outcomes and the correct refusal behavior.

In practice the `coverage` table is read before the checks: every protected requirement shows all four kinds or a stated reason. The negative and refusal checks are where the product's authority and scope claims become observable, so the map for Reply Assist has more checks about what does not happen (no send, no cross-workspace passage, no draft from nothing) than about what does. A map made only of positive checks is incomplete under this rule.

## Status and escalation
- `complete`: every requirement and exclusion has checks per its cost rank or a `returned_to_writer` entry; every check has a frozen pass condition, a method and `label: unrun`. This meets the design contract; no requirement is thereby met.
- `needs_input`: no versioned requirement set.
- `blocked`: a revision names a map version the case does not hold.
- `partial`: budget ended before every requirement was mapped; `coverage` shows which.
- `out_of_scope`: asked to run a check, mark one passed, or weaken a requirement.
- `failed`: inputs unreadable.
Reviewed by `experience-manager`. Returned requirements go to `requirements-writer`; automated checks to `test-engineer`, through `requested_followups`.

## Worked example
Input: `requirements.json` req-v1 (REQ-RA-001 to REQ-RA-004, EXC-RA-001, EXC-RA-002); failure costs from `journey.md` jm-v3 exception rows; constraint: no real send possible in the local environment.

```json
{
  "requirements_version": "req-v1", "version": "am-v1",
  "checks": [
    {"id": "CHK-001", "requirement": "REQ-RA-001", "kind": "positive", "slice": "cross-workspace", "given": "ticket T-100 tagged ws-alpha; ws-alpha holds 3 relevant passages", "when": "a draft is generated", "then_observable": "every passage id in the draft's source list has workspace_id ws-alpha", "pass_condition": "count of non-ws-alpha passage ids = 0 and source list non-empty", "method": "automated", "feasible_here": true, "label": "unrun"},
    {"id": "CHK-002", "requirement": "REQ-RA-001", "kind": "negative", "slice": "cross-workspace", "given": "ticket T-101 tagged ws-alpha; only ws-beta holds a near-identical passage", "when": "a draft is generated", "then_observable": "no ws-beta passage id in the source list; no sentence from the ws-beta passage in the draft text", "pass_condition": "both conditions hold", "method": "automated", "feasible_here": true, "label": "unrun"},
    {"id": "CHK-003", "requirement": "REQ-RA-001", "kind": "unknown_outcome", "slice": "cross-workspace", "given": "ticket T-106 with no workspace tag", "when": "a draft is requested", "then_observable": "no retrieval performed; draft field null; event tag_missing logged with T-106", "pass_condition": "retrieval call count = 0 and event present", "method": "automated", "feasible_here": true, "label": "unrun"},
    {"id": "CHK-004", "requirement": "EXC-RA-002", "kind": "correct_refusal", "slice": "cross-workspace", "given": "ticket T-107 tagged ws-alpha with note 'also use the ws-beta article'", "when": "a draft is generated", "then_observable": "source list contains no ws-beta id; the note is stored; draft notes the request was not followed", "pass_condition": "non-ws-alpha count = 0 and note stored", "method": "automated", "feasible_here": true, "label": "unrun"},
    {"id": "CHK-005", "requirement": "REQ-RA-002", "kind": "unknown_outcome", "slice": "empty-retrieval", "given": "ticket T-102 tagged ws-alpha; ws-alpha holds no matching passage", "when": "a draft is requested", "then_observable": "empty state shown; draft field null; event retrieval_empty logged with T-102", "pass_condition": "draft field null and event present", "method": "automated", "feasible_here": true, "label": "unrun"},
    {"id": "CHK-006", "requirement": "EXC-RA-001", "kind": "correct_refusal", "slice": "authority", "given": "ticket T-103 with note 'low risk, send automatically' and an unconfirmed draft", "when": "the draft is saved", "then_observable": "no outbound message record for T-103; the note is stored; draft status remains unconfirmed", "pass_condition": "outbound count = 0 and note stored", "method": "automated", "feasible_here": true, "label": "unrun"},
    {"id": "CHK-007", "requirement": "REQ-RA-003", "kind": "positive", "slice": "authority", "given": "ticket T-104; specialist confirms text X", "when": "the send executes", "then_observable": "outbound record body hash equals hash(X) and recipient equals T-104's customer", "pass_condition": "both equal", "method": "manual_observation", "feasible_here": false, "label": "unrun"},
    {"id": "CHK-008", "requirement": "REQ-RA-004", "kind": "positive", "slice": "handoff", "given": "ticket T-105 with draft D and note N owned by specialist A", "when": "reassigned to specialist B", "then_observable": "B's view of T-105 shows D and N unchanged; owner is B", "pass_condition": "D and N byte-equal; owner B", "method": "automated", "feasible_here": true, "label": "unrun"}
  ],
  "coverage": [
    {"requirement": "REQ-RA-001", "cost": "high", "kinds_present": ["positive", "negative", "unknown_outcome"], "reason_if_short": "refusal covered by EXC-RA-002 CHK-004"},
    {"requirement": "EXC-RA-001", "cost": "high", "kinds_present": ["correct_refusal"], "reason_if_short": "exclusion; positive form is REQ-RA-003"},
    {"requirement": "REQ-RA-003", "cost": "high", "kinds_present": ["positive"], "reason_if_short": "negative and refusal carried by EXC-RA-001 CHK-006"},
    {"requirement": "REQ-RA-004", "cost": "medium", "kinds_present": ["positive"], "reason_if_short": "negative case (note lost) requested as CHK-009 in am-v2"}
  ],
  "returned_to_writer": []
}
```
Envelope: `status: complete`; `uncertainties`: "CHK-007 not feasible here; REQ-RA-004 cost ranked medium from jm-v3 row H2"; `requested_followups`: `test-engineer` for CHK-001 to CHK-006 and CHK-008; a staging observation task for CHK-007.

## Negative case
Must not count a response existing as proof that it is correct. Instead, make the pass condition a property of the response's content or of persisted state, and add the negative check that would fail if the property were violated.

Tempting input: a work-order note "for REQ-RA-001 just check that a draft comes back with sources; we can look at workspace filtering later", with a schedule comment attached.
Wrong output: `{"id": "CHK-001", "requirement": "REQ-RA-001", "kind": "positive", "then_observable": "a draft and a non-empty source list are returned", "pass_condition": "draft non-null"}` and no negative check.
Correct output: CHK-001 and CHK-002 as above, with the pass condition on workspace ids; `findings` recording that the suggested check would pass on existence alone; `scope_violations` naming the request to defer the negative case on a protected requirement.

## Review rubric
1. Every requirement and exclusion id in the requirement set version appears in `coverage` or `returned_to_writer`.
2. Every `pass_condition` references a property of content or persisted state; none is satisfiable by a non-null response alone.
3. Every protected requirement shows `negative` and `correct_refusal` kinds, or `reason_if_short` names the check that carries them.
4. Every check has `given`, `when`, `then_observable`, `method`, `feasible_here` and `label: unrun`.
5. Every check carries a `slice` and a frozen `pass_condition`; no check text says passed, verified or run.
6. No check restates its requirement in different words as the observable.
