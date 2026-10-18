# Adaptation notes: independent audit (S10)

Source: the author's March 2026 draft of the Audit runbook (version 1.0, 6 March 2026). Provenance status `adapt`.

## Preserved

- Purpose: an independent verification runbook.
- The audit loop and its order: read the active unit; read the claimed implementation summary; inspect the changed files without assuming the builder is correct; re-run or replay the listed checks where possible; record pass, fail or blocked with reasons.
- The findings format: status (pass, fail, blocked), scope checked, evidence, findings, required follow-up; now the headings of the audit report.
- Always: verify the actual acceptance criteria, not a paraphrase; prefer reproducible evidence over narrative claims; call out missing evidence explicitly.
- Ask first: relaxing a failed acceptance criterion; waiving a required verification step.
- Never: reuse the builder's conclusion as the audit result; mark a failed check acceptable without an explicit waiver.
- The Always / Ask first / Never taxonomy, kept as a subsection of Guardrails.

## Changed

- The target is a frozen `artifact` version with a content hash, audited in a fresh context; a moving target yields `blocked`.
- Added the author/reviewer conflict rule as step 1: same role as the producer is refused as `author_cannot_review_own_artifact`; same session is `conflict`; unknown identity is `unverified` and leaves independence gates blocked; manager review is never an independent audit.
- "Re-run or replay" became fresh receipts in the audit context, with fixture replay labeled `fixture_replay`; deferred to `aipt-method-evaluation-execution-and-receipts`. The builder's receipts are history, not audit evidence.
- Added the controller's rule that a `pass` citing any check without a receipt is rejected.
- Added coverage as a separate finding: a passing check proves exit status, not the criterion's full statement.
- Added an explicit overall decision rule for `pass`, `fail` and `blocked`.
- Required inputs are typed, versioned references (artifact, requirement versions and work order criteria, builder envelope, receipts, snapshot, reviewer and producer identities, capabilities), each with a stated behavior when missing.
- Outputs are a `review` record, one `validation` record per re-run check, the audit report, and envelope fields including `observed_checks`, `proposed_links` (`verifies`) and `scope_violations`.
- Waivers are routed to the decision path as follow-ups; the auditor cannot grant one.
- Added the Example (the source had none), on the synthetic Reply Assist case, showing a coverage gap that fails the requirement.
- Added the Evidence and uncertainty rules section, deferring record keeping to `aipt-method-evidence-and-lineage`.
- Added Use when, Do not use when and Success criteria sections.

## Omitted

- The names of the plan and status files the source told the auditor to read; they were installation-specific. The audit now reads the work order and the builder's submitted envelope.
- Any reference to the author's earlier projects or setup.
