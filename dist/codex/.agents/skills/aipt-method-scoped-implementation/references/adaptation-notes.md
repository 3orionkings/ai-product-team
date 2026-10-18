# Adaptation notes: scoped implementation (S09)

Source: the author's March 2026 draft of the Implement runbook (version 1.0, 6 March 2026). Provenance status `adapt`.

## Preserved

- Purpose: a builder runbook for turning a planned unit into a verified change.
- The six-step execution loop and its order: read the governing context; confirm the exact unit and acceptance criteria; inspect the relevant files before editing; implement the smallest safe diff; run targeted checks first, then broader checks if warranted; record what changed, what passed and what remains.
- Output requirements: exact files changed, exact checks run, unresolved risks or blockers.
- Always: keep diffs scoped to the active unit; fix failures before moving to unrelated work; update after each meaningful checkpoint.
- Ask first: new dependencies; schema or data migrations; destructive cleanup; changes that expand scope beyond the active unit.
- Never: skip verification because a change looks small; claim completion without evidence; fold unrelated refactors into the work.
- The Always / Ask first / Never taxonomy, kept as a subsection of Guardrails.

## Changed

- The unit is a controller work order with a write set, prohibited actions, budget and capabilities; "milestone" became "work order" throughout.
- Step 1 now reads the work order envelope and the derived status brief instead of a fixed set of guidance files.
- Added a snapshot check (step 3): the working tree must match the snapshot recorded at admission, or the result is `blocked`.
- Added the write-set rule: a change needed outside the write set is a `scope_violation` and a `blocked` result, not a wider diff.
- Checks became receipts: every targeted check runs through the receipt mechanism and carries a `receipt_id`; a check without one is `claimed_only`. Deferred to `aipt-method-evaluation-execution-and-receipts`.
- "Update documentation after each checkpoint" became "submit the envelope after each checkpoint", because the status brief is derived from state rather than written by the builder.
- Required inputs are typed, versioned references (work order, snapshot artifact, requirement versions, check commands, prior review), each with a stated behavior when missing.
- Outputs are `artifact` records in `implemented_not_verified`, an implementation report, and envelope fields including `observed_checks`, `scope_violations` and `proposed_links` (`implements`).
- Added an explicit status rule mapping evidence to `complete`, `partial`, `blocked` and `needs_input`.
- Added the Example (the source had none), on the synthetic Reply Assist case.
- Added the Evidence and uncertainty rules section, deferring record keeping to `aipt-method-evidence-and-lineage`.
- Added Use when, Do not use when and Success criteria sections.

## Omitted

- The names of the guidance and status files the source told the builder to read; they were installation-specific.
- Any reference to the author's earlier projects or setup.
