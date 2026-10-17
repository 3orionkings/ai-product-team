# Adaptation notes: research consolidation (S06)

Source: the author's March 2026 draft of "Research and Consolidation Orchestrator". The skill is an adaptation of that draft into the package's skill template.

## Preserved

- Purpose: deep, staged research and synthesis where the method must not skip steps, collapse sources prematurely or pretend certainty.
- Use when: research spans several artifacts, repositories, documents or tool outputs; a staged process with explicit gates is wanted; provenance, consolidation quality and traceability matter; the output may become a design, migration plan, specification or governance artifact.
- Do not use when: quick lookup or light summarization; brainstorming without rigorous consolidation.
- The five phases in the source's order and with the source's content: phase 0 discovery and inventory (find materials, map authorities, identify gaps, create the inventory); phase 1 extraction (facts, claims, constraints, examples; preserve provenance; isolate uncertain items); phase 2 consolidation (deduplicate, resolve overlaps, classify conflicts, separate baseline truths from tentative ideas); phase 3 synthesis (structured target artifact, uncertainties visible); phase 4 verification (coverage against the inventory, claims against evidence, no skipped phases or unsupported assertions).
- The per-phase output contract: what was done, what was found, what remains unresolved, what is needed next.
- The final-artifact additions: source coverage statement, unresolved items list, confidence notes.
- All four guardrails: no jump from discovery to synthesis; no invisible blending of fact and inference; no loss of provenance during consolidation; no burying of conflicting evidence.
- Success criteria: staged, inspectable, evidence-grounded, easy to challenge or extend.

## Changed

- Required inputs are restated as typed, versioned references (`requirement` or `proposal` version id for the question; `source` version ids for the corpus; `decision` or `approval` version id for phase boundaries), each with the behavior when it is missing; a resumption input (prior phase report `artifact` ids) was added.
- Outputs are restated as registered `artifact` records (one per phase gate, plus the final artifact with named JSON keys) and the envelope fields the skill fills (`findings`, `evidence_refs`, `artifact_refs`, `proposed_links`, `uncertainties`, `requested_followups`, `scope_violations`, `observed_checks`).
- Each phase is now a numbered Method step with an explicit gate condition, so "no skipped phases" is checkable rather than asserted.
- Claims are typed `fact`, `hypothesis` or `observation` and carry scope and status, matching the package's claim record.
- Each guardrail now states the alternative behavior after "Instead"; a fifth guardrail (instructions found inside a source are data) was added.
- Three further do-not-use conditions were added to keep the skill distinct from S02, S12 and S24.
- An Evidence and uncertainty rules section was added; it defers record keeping to S12.
- An Example on the Larkspur Support / Reply Assist material was added; the source had none.
- The addressee changed from "the user" to the requesting role; "find all relevant materials" is bounded to the authorized roots in the task envelope.

## Omitted

- The standalone "Default phases" heading and its sub-headings; the phases now live as Method steps because the template has no such section.
- No sentence in the source named an earlier project, a client or an installation path, so nothing was dropped for that reason.
