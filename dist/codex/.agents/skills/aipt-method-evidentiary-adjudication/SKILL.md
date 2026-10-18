---
name: aipt-method-evidentiary-adjudication
description: Adjudicate, rule on evidence, judge sufficiency, resolve a disagreement, converge, compare options against criteria, admissible evidence, insufficient evidence, unresolved. Rule on whether admissible evidence carries a stated claim and how options compare against frozen criteria, with a finding per objection and one outcome: option_acceptable, option_rejected, insufficient_evidence, unresolved or next_test_required. Never decide by vote count or confidence rhetoric. Not for writing challenges (aipt-method-adversarial-challenge) or applying delegation (aipt-method-delegated-authority).
license: MIT
metadata:
  aipt_skill_id: "S24"
  aipt_provenance: "newly_authored"
  aipt_version: "0.1.0"
---

# Evidentiary adjudication

## Purpose

Return a ruling that says what the admissible evidence establishes, what it does not, and which observation would settle what remains. Two modes share one method. Sufficiency mode rules on a single stated claim within its stated scope. Comparison mode rules on which options satisfy the frozen criteria and resolves each material challenge raised against them.

A ruling is a judgment about evidence. It is not a certification that a fact is true, and it is not permission to accept or execute anything; acceptance is a separate record produced under `aipt-method-delegated-authority` (S25), and execution needs a work order.

Terms used here. Frozen criteria are the criteria recorded in the decision packet, with a version and freeze time, before any result they are applied to existed. Admissible evidence is a record that resolves to an immutable version, whose scope and target apply to the question asked, and whose provenance is labeled. A receipt is the recorded observation of a command or evaluation: arguments, target snapshot, exit status, outputs, observer.

## Use when

- Challenge responses exist and the parties disagree about whether the evidence carries the claim.
- Two or more options remain after a challenge round and the decision needs a comparison against frozen criteria.
- A reviewer, manager or steward disputes whether a `validation` still applies to the current target version.
- The challenge round limit has been reached and the run needs a recorded outcome, which may be `unresolved`.
- A release review needs a sufficiency ruling on one named claim before a gate.

## Do not use when

- Nothing is contested and the proposal needs ordinary manager review. Instead, let the manager apply its review rubric; adjudication is activated by a disputed matter.
- The question is whether a specific passage supports a specific claim. Instead, request a claim check under `aipt-method-evidence-and-lineage` (S12) and admit its result as evidence.
- The question is whether a receipt is genuine or which commands actually ran. Instead, request `aipt-method-independent-audit` (S10) and admit the audit result.
- Nobody froze criteria. Instead, return `needs_input` and ask for criteria frozen under `aipt-method-evaluation-planning` (S17) before you read any result.
- You authored, revised or challenged the proposal. Instead, declare the conflict in `scope_violations` and return the task.

## Required inputs

- Decision packet — `artifact` version (`decision-packet.json`): frozen criteria with version and freeze time; options; `proposal` version and hash; constraints and protected `requirement` ids; author, reviser and challenger session ids. If missing, return `needs_input`.
- Challenges and responses — `challenge` records with `state` (`open`, `answered`, `upheld`, `withdrawn` or `unresolved`), and the owner's response per challenge (evidence, revision or reasoned disagreement). If a response is missing, rule on that challenge as unanswered; an unanswered material challenge cannot be overruled.
- Evidence — `claim`, `source`, `validation` and `review` records by version, with receipts wherever execution is claimed. If a receipt is missing, treat the result as agent-reported and admissible only as a hypothesis.
- Your eligibility — session identity and the conflict set. If missing, record `conflict_check: unverified` and state that the ruling cannot close a gate requiring independent review.
- Mode — `sufficiency` with the exact claim and scope, or `comparison` with the option set. If missing, infer it from the task and state the inference in `uncertainties`.

## Method

1. Confirm the criteria were frozen before results. Compare the criteria version's freeze time with the earliest result it is applied to. If criteria changed after results existed, do not apply the new criteria silently. Instead, rule under the frozen version and file a `criteria_change_disclosure` naming who changed what and why; the human owner decides whether the change stands.
2. Confirm your eligibility: your session is not an author, reviser or challenger of this proposal, and the conflict set is empty for you. Record the check inside the ruling.
3. Admit evidence record by record. Check that it resolves to an immutable version; that its scope covers the claim or option it is cited for; that its target version equals the proposal's target, or a recorded applicability review says the result still applies; that its provenance is labeled `live`, `fixture_replay` or `agent_reported`; and that any execution claim has a receipt. Admit it, or mark it `inadmissible` with the failing check. An inadmissible record is not evidence against anything; it is absent.
4. Weigh admissible evidence by what was observed, not by who said it or how firmly. Two agents asserting a claim without a new observation count as one unsupported assertion. Count observations, not voices. Treat confidence labels as labels; they are not probabilities and cannot be summed.
5. Rule on each objection. For every `challenge`, write a finding: `sustained` (the premise fails or stays unsupported and the stated consequence follows), `overruled` (admissible evidence shows the premise holds within scope), `partially_sustained` (holds for part of the scope) or `unresolved` (the resolving test has not run, or its result is inadmissible). Cite the admitted records that carry each finding. An unanswered challenge is `unresolved`, never `overruled`. Request the matching `challenge_state` for each finding: `sustained` and `partially_sustained` request `upheld`, `overruled` requests `answered`, and `unresolved` requests `unresolved`. The controller applies the transition; the ruling only proposes it.
6. In sufficiency mode, state the exact claim and scope you ruled on, then the outcome: `sufficient` when admitted evidence carries the claim within that scope, otherwise `insufficient_evidence` with what is missing. Do not extend the ruling past the scope tested. Instead, name the untested scope as outside the ruling.
7. In comparison mode, build a criteria-by-option table. Each cell holds `met`, `not_met` or `unestablished` plus the admitted record ids. Fill it for every option, including the simpler alternatives supplied, using the same criteria for all.
8. Determine the outcome from the table and the findings. `option_acceptable`: an option meets every criterion and carries no sustained material challenge; more than one option can be acceptable, and you say so instead of picking by preference. `option_rejected`: a sustained challenge has effect `option_fails` on a protected requirement, or a required criterion is `not_met`. `next_test_required`: one discriminating test would change the outcome and costs less than another round. `insufficient_evidence`: the admitted evidence cannot carry any option. `unresolved`: material disagreement remains and no single test is clearly discriminating.
9. Order next tests by discriminating power: the test whose two outcomes lead to different decisions comes first. Reuse resolving tests from the challenge records when they qualify; write a new one only when none does.
10. Preserve dissent: list each objection not fully overruled, who raised it, and what would resolve it, so the dissent register can carry it forward.
11. Write the scope statement: the proposal version, target version and criteria version the ruling applies to; that it is not a fact certification; that it does not authorize acceptance or execution. Fill the envelope.

## Output contract

Artifact: a ruling, proposed as a `review` record and written as `evidence-ruling.json` in sufficiency mode or `judgment.json` in comparison mode. `reviewed_refs`, `result` and `conflict_check` take the `review` schema's values; `outcome` takes the `ruling_outcome` values:

```json
{
  "ruling_id": "jdg-...",
  "mode": "sufficiency | comparison",
  "packet_version": "...", "proposal_version": "...", "criteria_version": "...",
  "reviewed_refs": ["prop-...@v...", "decision-packet.json@v...", "chl-..."],
  "criteria_change_disclosure": null,
  "eligibility": {"judge_session": "...", "conflicts": [], "conflict_check": "verified | unverified | conflict"},
  "claim_under_ruling": {"statement": "...", "scope": "..."},
  "admitted_evidence": [{"ref": "...", "provenance": "live | fixture_replay | agent_reported"}],
  "inadmissible_evidence": [{"ref": "...", "reason": "..."}],
  "findings_per_objection": [{"challenge_id": "...", "finding": "sustained | overruled | partially_sustained | unresolved", "requested_state": "upheld | answered | unresolved", "carried_by": ["..."], "note": "..."}],
  "option_comparison": [{"option": "...", "criteria": {"<criterion>": {"status": "met | not_met | unestablished", "refs": ["..."]}}}],
  "outcome": "option_acceptable | option_rejected | insufficient_evidence | unresolved | next_test_required",
  "result": "pass | fail | escalate",
  "acceptable_options": ["..."], "rejected_options": ["..."],
  "next_tests": [{"test": "...", "discriminates": "...", "order": 1}],
  "preserved_dissent": [{"challenge_id": "...", "raised_by": "...", "resolves_if": "..."}],
  "scope_statement": "Applies to ... Not a fact certification. Not acceptance or execution permission."
}
```

`claim_under_ruling` is filled in sufficiency mode and null in comparison mode; `option_comparison` is the reverse. `result` follows `outcome`: `option_acceptable` gives `pass`, `option_rejected` gives `fail`, and `insufficient_evidence`, `unresolved` and `next_test_required` give `escalate`. `requested_state` is the `challenge_state` each finding asks the controller to apply.

Envelope fields always filled: `findings` (one line per objection, then the outcome), `evidence_refs` (admitted and inadmissible), `artifact_refs`, `uncertainties` (unestablished cells, unresolved objections, inferred mode), `requested_followups` (next tests as work orders), `proposed_links` (`supports` or `contradicts` edges from admitted records to the claims they bear on, carrying the finding), `scope_violations` (conflicts, attempts to change criteria, requests to authorize). `observed_checks` stays empty: a judge does not run tests.

## Evidence and uncertainty rules

- Admissibility is checked per record and per use; a record admissible for one claim can be inadmissible for a different scope.
- A historical pass against an earlier target is admissible only with a recorded applicability review. Otherwise mark the criterion `unestablished`, not `met`.
- Agent-reported results without receipts are hypotheses. Do not treat a confident summary as an observation. Instead, request the receipt or rule `insufficient_evidence`.
- `fixture_replay` evidence establishes the behavior of the fixture, not of live execution. Say which one the finding rests on.
- Do not fill an `unestablished` cell by analogy to a similar system or an earlier project. Instead, name the test that would fill it.
- Silence is not agreement: an objection nobody answered is `unresolved`.
- Type every statement you add under S12 and cite admitted record ids for each.

## Guardrails

- Do not decide by the number of roles, reviewers or sessions favoring an option. Instead, decide by admitted observations against frozen criteria, and record in `findings` that vote-like inputs were disregarded.
- Do not let confidence words carry a finding. Instead, strip them and ask what was observed, on which version.
- Do not change, reweight or add criteria after seeing results without disclosure. Instead, file a `criteria_change_disclosure` and rule under the frozen version.
- Do not certify a fact. Instead, say that the evidence is sufficient for the stated claim, in the stated scope, at the stated version.
- Do not authorize acceptance or execution. Instead, hand `acceptable_options` to the acceptance step under S25 and leave execution to a work order.
- Do not generalize a narrow pass to the whole product. Instead, confine the scope statement to the tested slice and list what was not tested.
- Do not manufacture consensus at the round limit. Instead, return `unresolved` or `next_test_required` with the next evidence named.
- Do not rule on a matter outside the decision packet. Instead, record it in `scope_violations` and return it to the review step.

## Success criteria

- Every referenced record is classified admitted or inadmissible with the check that decided it.
- Every challenge has a finding that cites the records carrying it; unanswered challenges are `unresolved`.
- In comparison mode every option is scored on every frozen criterion, with the same criteria for all.
- The outcome is one of the five values and follows from the table and findings, not from a count.
- Any criteria change after results is disclosed in the ruling.
- The scope statement names the versions and disclaims fact certification and permission.
- Dissent and next tests are listed with who raised them and what discriminates.

## Example

Case: Reply Assist at Larkspur Support. Comparison mode on `prop-rt-12@v3` after round 1. Options: A, a per-workspace retrieval index; B, a shared index with a query-time workspace filter, recommended by the author. Challenge `chl-031` contested B's isolation premise on the cached-summary path. The owner answered with `val-081`, a canary test on direct retrieval only, and added that three reviewers "are confident the filter is adequate".

```json
{
  "ruling_id": "jdg-019",
  "mode": "comparison",
  "packet_version": "decision-packet.json@v2", "proposal_version": "prop-rt-12@v3", "criteria_version": "crit-rt@v1",
  "reviewed_refs": ["prop-rt-12@v3", "decision-packet.json@v2", "chl-031"],
  "criteria_change_disclosure": null,
  "eligibility": {"judge_session": "sess-j08", "conflicts": [], "conflict_check": "verified"},
  "claim_under_ruling": null,
  "admitted_evidence": [{"ref": "val-081", "provenance": "live"}, {"ref": "val-064", "provenance": "live"}],
  "inadmissible_evidence": [{"ref": "rev-044", "reason": "reviewer confidence statement; no observation, no version"}],
  "findings_per_objection": [{"challenge_id": "chl-031", "finding": "partially_sustained", "requested_state": "upheld", "carried_by": ["val-081"], "note": "Direct retrieval path holds for ws-alpha/ws-beta; cached-summary path untested."}],
  "option_comparison": [
    {"option": "A", "criteria": {"REQ-ISO-01": {"status": "met", "refs": ["val-064"]}, "draft_quality": {"status": "met", "refs": ["val-064"]}, "p95_latency": {"status": "met", "refs": ["val-064"]}}},
    {"option": "B", "criteria": {"REQ-ISO-01": {"status": "unestablished", "refs": ["val-081"]}, "draft_quality": {"status": "met", "refs": ["val-081"]}, "p95_latency": {"status": "met", "refs": ["val-081"]}}}
  ],
  "outcome": "next_test_required",
  "result": "escalate",
  "acceptable_options": ["A"], "rejected_options": [],
  "next_tests": [{"test": "chl-031 resolving test on the cached-summary path", "discriminates": "B acceptable versus B rejected on REQ-ISO-01", "order": 1}],
  "preserved_dissent": [{"challenge_id": "chl-031", "raised_by": "sess-c41", "resolves_if": "zero canary occurrences retrieved through the summary cache"}],
  "scope_statement": "Applies to prop-rt-12@v3 at retrieval@2f9c... under crit-rt@v1. Not a fact certification. Not acceptance or execution permission."
}
```

Envelope `findings` excerpt: "Three reviewers' confidence (rev-044) disregarded: no observation. A acceptable on all frozen criteria. B awaits one discriminating test; a second debate round would cost more and settle less."
