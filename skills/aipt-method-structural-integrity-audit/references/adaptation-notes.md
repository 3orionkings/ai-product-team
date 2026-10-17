# Adaptation notes: structural integrity audit (S05)

Source: the author's March 2026 draft of "Structural Audit / Integrity Checker". The skill is an adaptation of that draft into the package's skill template.

## Preserved

- Purpose: audit a set of artifacts (prompts, agent files, skills, templates, docs, scaffolding) for structural quality, internal consistency and portability.
- Use when: audit before use or publication; several generated outputs need comparison and cleanup; concerns about duplication, drift, bloat or contradictory rules; a readiness judgment is needed before further execution.
- Do not use when: content creation with no audit step; one tiny file with no structural question.
- The eight audit dimensions, in the source's order: role clarity, scope discipline, duplication, contradictions and precedence conflicts, portability, maintainability, readability and operational usefulness, cargo-cult filler.
- The process and its order: inventory the set; check for overlap and conflict (repeated guidance, conflicting instructions, unclear precedence, missing boundaries, overgrown files); rate operational quality; recommend structural fixes, preferring merges, splits, deletions, relocations and sharper ownership over wordsmithing.
- The output contract's five parts: executive assessment, findings by dimension, prioritized concrete fixes, recommended end-state structure, readiness verdict with the three values usable now / usable with fixes / not ready.
- All four guardrails: verbosity is not rigor; no praise for weak but comprehensive-looking artifacts; no unnecessary complexity; maintainability costs count.
- Success criteria: the reader can see what is wrong structurally, why it matters, what to change first and what good looks like.

## Changed

- Required inputs are restated as typed, versioned references (`artifact` or `source` version ids for the set; `requirement` or `proposal` version id for purpose; `requirement` or `decision` version ids for constraints), each with the behavior when it is missing.
- Outputs are restated as a registered `artifact` of kind `review` with named JSON keys, plus the envelope fields the skill fills (`findings`, `evidence_refs`, `artifact_refs`, `uncertainties`, `requested_followups`, `scope_violations`, `observed_checks`).
- The four process steps are expanded to nine numbered steps so that ownership mapping, portability checking, dimension scoring and the end-state description are explicit steps rather than implied by the output list.
- Each guardrail now states the alternative behavior after "Instead".
- A fifth guardrail (do not rule on content correctness) and three further do-not-use conditions were added to keep the skill distinct from S04, S07, S10 and S23.
- An Evidence and uncertainty rules section was added; it defers record keeping to S12.
- An Example on the Larkspur Support / Reply Assist material was added; the source had none.
- The addressee changed from "the user" to the requesting role and the case record.

## Omitted

- The standalone "Audit dimensions" heading; the template has no such section, so the dimensions are stated at the head of the Method.
- No sentence in the source named an earlier project, a client or an installation path, so nothing was dropped for that reason.
