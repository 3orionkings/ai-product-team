# Adaptation notes: drift and regression audit (S07)

Source: the author's March 2026 draft of "Non-Regression / Drift Auditor". The skill is an adaptation of that draft into the package's skill template.

## Preserved

- Purpose: compare a baseline and a changed system, document semantic or structural drift, and determine whether parity or intended behavior has been preserved.
- Use when: a migration, refactor, consolidation or rewrite has happened; parity with an existing system is wanted; the risk is subtle drift rather than obvious breakage; an artifact has several generations.
- Do not use when: there is no baseline; the task is greenfield and parity is irrelevant.
- The process and its order: define the comparison contract (invariants, acceptable deltas, unacceptable drift, surface area in scope); compare at multiple levels (structure, behavior, semantics, governance and safety constraints, output contract, user-facing workflow); classify findings (exact parity, acceptable intentional change, ambiguous difference requiring judgment, regression, hidden drift); root-cause real regressions (missing logic, changed assumptions, renamed but semantically altered structure, lost constraints, incomplete backfill, broken sequencing); recommend the repair path as the minimum fix or a formal blessing of an intentional deviation.
- The output contract's six parts: scope and comparison contract, drift findings by category, severity and impact, root-cause notes, repair recommendations, verdict with the three values parity preserved / partial drift / regression.
- All four guardrails: word overlap is not semantic parity; not every change is a regression; hidden governance and sequencing differences count; no parity claim without checking the critical paths.
- Success criteria: the reader can see what changed, whether it matters, why it happened, and what to fix or accept.

## Changed

- Required inputs are restated as typed, versioned references (`artifact`, `source` or `validation` version id for the baseline; `artifact` version id for the changed version; `requirement` or `decision` version ids for invariants; `proposal` or `decision` version id for allowed deltas), each with the behavior when it is missing. Derived invariants are labeled and need confirmation before a parity verdict.
- Outputs are restated as a registered `artifact` of kind `review` with named JSON keys, plus the envelope fields the skill fills (`findings`, `evidence_refs`, `artifact_refs`, `proposed_links`, `uncertainties`, `requested_followups`, `observed_checks`, `scope_violations`).
- The five process steps are expanded to eight numbered steps so that severity assignment, the critical-path check and the verdict are explicit steps; the critical-path check was a guardrail in the source and is now also a step with a recorded checklist.
- Category names are fixed as machine-readable values and the rule that an unlisted difference is `ambiguous`, never `intentional_change` on the auditor's judgment, is stated in the Method.
- Each guardrail now states the alternative behavior after "Instead"; a fifth guardrail (no self-authorized blessing of deviations) was added.
- Three further do-not-use conditions were added to keep the skill distinct from S10, S12, S13 and S19; the distinction from S12 is stated in the Purpose, the inputs and the Evidence rules: this skill compares, it does not maintain the ledger.
- An Evidence and uncertainty rules section was added; it defers record keeping to S12 and applies the package's rule that a pass against the baseline is historical until a validation exists for the changed version.
- An Example on the Larkspur Support / Reply Assist material was added; the source had none.
- The addressee changed from "the user" to the requesting role.

## Omitted

- The source's list of things that may have "multiple generations" named a model and an agent pack; these were replaced by "prompt set, role catalog, repository, schema or architecture" so the skill carries no reading as a provider or model reference and no host-specific packaging term.
- The source's sub-headings inside Process; the steps are now a numbered list because the template has no sub-sections under Method.
- No sentence in the source named an earlier project, a client or an installation path, so nothing was dropped for that reason.
