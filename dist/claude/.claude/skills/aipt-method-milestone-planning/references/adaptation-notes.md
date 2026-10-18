# Adaptation notes: milestone planning (S08)

Source: the author's March 2026 draft of the Plan runbook (version 1.0, 6 March 2026). Provenance status `adapt`.

## Preserved

- Purpose: the plan is the single source of truth for execution order.
- The three rules: work is broken into units that can be implemented and validated in one loop; each unit states what is in scope, what is out of scope and how completion is proven; nothing is marked done without command evidence or a documented manual check.
- The template fields, now carried per work order: goal, why now, owner (as role), status, acceptance criteria, automated and manual validation, blocking and follow-on dependencies, risks and decisions.
- Always: prefer the smallest next unit that unlocks downstream work; update before and after each material implementation run.
- Ask first: reordering units with external impact; removing acceptance criteria.
- Never: treat a vague objective as implementation-ready; leave validation empty.
- The Always / Ask first / Never taxonomy, kept as a subsection of Guardrails.

## Changed

- Milestones became controller work orders: each unit now declares a write set (output paths), prohibited actions, blocking dependencies, acceptance checks with receipt requirements, a risk tier and review and independence flags, matching the work-order envelope.
- The plan is a `proposed` artifact; the controller mints and admits orders. "Status" per unit is no longer a hand-edited field; completion is derived from `validation` records with current applicability.
- Required inputs are typed, versioned references: approved `requirement` versions, an accepted `decision`, a snapshot `artifact`, current `validation` records and run constraints, each with a stated behavior when missing.
- Outputs are the plan artifact plus envelope fields (`findings`, `evidence_refs`, `artifact_refs`, `proposed_links`, `uncertainties`, `requested_followups`, `scope_violations`), with `implements`, `depends_on` and `derived_from` links.
- "Command evidence" became receipts, deferred to `aipt-method-evaluation-execution-and-receipts`.
- "Update this file" became "re-derive the plan from state", since the plan is no longer a hand-maintained file.
- Added a requirement for a negative or refusal check on every protected requirement touched, consistent with the package's protected-requirement rule.
- Added the Example (the source had none), on the synthetic Reply Assist case.
- Added the Evidence and uncertainty rules section, deferring record keeping to `aipt-method-evidence-and-lineage`.
- Added Use when, Do not use when and Success criteria sections, which the source stated only implicitly.

## Omitted

- The Markdown file template as a literal artifact; its fields survive as JSON keys of the plan artifact.
- Any reference to companion files in the author's earlier setup.
- The word "milestone" as the unit name in the body; the unit is a work order. The skill title keeps "milestone planning" because the registry fixes it.
