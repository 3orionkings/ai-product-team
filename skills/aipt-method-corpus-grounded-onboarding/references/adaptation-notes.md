# Adaptation notes: Corpus-grounded onboarding (S02)

Source: the author's March 2026 draft of Corpus-Grounded Onboarding Synthesizer. The notes below describe what the adapted `SKILL.md` keeps, changes and leaves out.

## Preserved

- Purpose: onboard into a new project, codebase, document set or handoff corpus without drifting into generic summaries; convert raw corpus material into an actionable mental model.
- Use when: a handoff has happened between people or agents; a local corpus, repository, document pack or prompt archive exists to absorb; product, architecture, constraints and invariants must be understood before acting; the requester wants evidence-grounded readiness confirmation.
- Do not use when: there is no real corpus; only a quick high-level summary is wanted; immediate execution is needed and the context is already stable and clear.
- Process steps and their order: read before speaking; build a structured mental model under the seven headings (purpose, users or operators, core workflows, architectural components, invariants, governance and verification and rollback expectations, known gaps); separate fact from inference using the three buckets (explicitly stated, strongly implied by multiple artifacts, inferred and unverified); identify operational boundaries (what must not change casually, where work should happen, what is provisional, where evidence is thin); state readiness honestly only after reconstructing the system at useful fidelity.
- Output contract: plain-language understanding of the project; structured system or product model; key invariants and boundaries; open risks and unresolved uncertainties; readiness statement for the next instruction.
- Guardrails: no paraphrasing into fluff; no collapsing architecture and product intent; no claiming verification or maturity the corpus does not evidence; no hiding uncertainty.
- Success criteria: a new operator can read the output and understand what the project is, how it is supposed to work, what cannot be broken and where ambiguity still lives.

## Changed

- Required inputs are restated as typed versioned references (`source`, work order, `requirement` and `artifact` version ids), each with the behavior to follow when it is missing.
- Outputs are restated as a named artifact, `onboarding-model.md` with fixed headings and `[stated]` / `[implied]` / `[inferred]` prefixes, plus the envelope fields `findings`, `evidence_refs`, `artifact_refs`, `proposed_links`, `uncertainties`, `requested_followups` and `scope_violations`.
- The readiness statement now names the task it was judged against and uses three fixed values: `ready`, `ready with limitations`, `not ready`.
- A step was added that maps the three buckets onto claim types (`fact`, `fact` with multiple supports, `hypothesis`) and hands them to aipt-method-evidence-and-lineage (S12) for recording.
- An Example section was added, using the fictional Reply Assist product at Larkspur Support; the source had none.
- An Evidence and uncertainty rules section was added, including the distinction between a test file existing and a `validation` record with a receipt.
- Do-not-use bullets now route to the neighboring skills S01, S05, S06 and S09 so the method stays distinct from discovery, structural audit, research consolidation and implementation.
- Each guardrail now states the alternative behavior, as the authoring contract requires.
- Voice changed to second person imperative throughout.

## Omitted

- The pack-level introduction that described the origin of the drafts in the author's prompt archive, its suggested installation directories and its recommended usage order.
- The agent-style title framing ("Synthesizer"); the adapted skill is a method, not a persona.
