# Adaptation notes: Discovery interrogation (S01)

Source: the author's March 2026 draft of Discovery Interrogator. The notes below describe what the adapted `SKILL.md` keeps, changes and leaves out.

## Preserved

- Purpose: force high-quality discovery before solutioning, for product, UX, workflow, system design, process design and ambiguous build requests.
- Use when: the problem is underspecified; the requester wants questions before design; the task involves workflows, trust, permissions, architecture or operating-model choices; the cost of solving the wrong problem is high.
- Do not use when: a complete specification exists and execution is wanted; the task is trivial and the gap does not change the answer; the requester declined questions and enough context exists.
- Operating stance, folded into Method step 1 and the Guardrails: read available context first; no generic template questions; only strategically consequential questions; questions reflect the actual ambiguities.
- Process steps and their order: reconstruct the problem (what the requester wants, who it is for, what outcome matters, what is unclear); identify decision-critical gaps using the seven buckets; ask only consequential questions using the four-part consequence test (direction, priority or scope, risk handling, success measurement); avoid premature solutioning, with a first-pass hypothesis only when explicitly requested.
- Output contract: a short context confirmation paragraph in the skill's own words, then only the questions, grouped where useful.
- Guardrails: no generic preference filler; no pretended certainty; no recommendation masquerading as a question; no over-long questionnaire.
- Success criteria: the requester feels understood; the questions are sharp and non-obvious; each question clearly matters; the next round of answers unlocks materially better work.

## Changed

- Required inputs are restated as typed versioned references (`source`, `requirement`, `decision`, `claim` and `artifact` version ids), each with the behavior to follow when it is missing.
- Outputs are restated as a named artifact, `discovery-questions.md` with fixed headings, plus the envelope fields `findings`, `evidence_refs`, `artifact_refs`, `uncertainties`, `requested_followups` and `scope_violations`.
- An "Assumed unless corrected" section was added to the artifact so that uncertainties discarded by the consequence test remain visible instead of disappearing.
- An Example section was added, using the fictional Reply Assist product at Larkspur Support; the source had none.
- An Evidence and uncertainty rules section was added; it defers all record keeping of sources, claims and links to aipt-method-evidence-and-lineage (S12).
- A rule and envelope field for instructions embedded in sources (`scope_violations`) was added.
- Do-not-use bullets now route to the neighboring skills S08, S09, S13 and S23 so the method stays distinct from planning, implementation, requirements writing and adversarial challenge.
- Each guardrail now states the alternative behavior, as the authoring contract requires.
- Voice changed to second person imperative throughout; "This skill succeeds when" became observable criteria.

## Omitted

- The pack-level introduction that described the origin of the drafts in the author's prompt archive, its suggested installation directories and its recommended usage order.
- The agent-style title framing ("Interrogator"); the adapted skill is a method, not a persona.
