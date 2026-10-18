# Adaptation notes: status handoff (S11)

Sources: the author's March 2026 draft of the Documentation runbook, version 1.1 (24 March 2026) as the primary source, and version 1.0 (6 March 2026) for its validation-history idea only. Provenance status `adapt`.

## Preserved

- Purpose: a short, current, human-readable status snapshot that is the fastest resume surface.
- The four sections and their order from version 1.1: Current state (last updated, active unit, branch or snapshot, overall state); Latest progress (what changed, what was validated); Active blockers (blocker, next action); Immediate next queue (three items).
- From version 1.0: the idea that validation history matters to the resume, that both successes and failures affecting next steps are recorded, and that a stale "current state" is never kept after the state changed.
- Always: keep it short and current; keep it aligned with the deeper record; use it as the fastest resume surface for humans.
- Ask first: removing notes that still affect immediate execution.
- Never: turn it into the deep cumulative store; duplicate large sections of the deeper record; use it as a raw log dump.
- The Always / Ask first / Never taxonomy, kept as a subsection of Guardrails.

## Changed

- The brief is derived: the controller renders it from authoritative state, and this method decides what to include and in what order. Editing the brief changes no state.
- The "deeper cumulative memory" the source aligned with became the case store and the full case report; alignment became the rule that every line resolves to a record version.
- "Validated" now means a `validation` record with `result: passed` and `applicability: current`, backed by a receipt. Validation history is counted and referenced, not listed; the records stay in state (this carries the version 1.0 idea without reintroducing a log).
- "Current branch" became the target snapshot; "last updated" became the event sequence the brief was rendered from.
- Required inputs are typed references from the controller (run status, task states, validations, blockers, ready queue, recent reviews and decisions, snapshot, previous brief), each with a stated behavior when missing.
- Outputs are two brief artifacts (Markdown and JSON) plus envelope fields, including `findings` that record the selection rules so the render is reproducible, and `proposed_links` (`derived_from`).
- Added the Example (the sources had none), on the synthetic Reply Assist case.
- Added the Evidence and uncertainty rules section, deferring record keeping to `aipt-method-evidence-and-lineage`.
- Added Use when, Do not use when and Success criteria sections.

## Omitted

- Every reference to the companion memory file named in the sources; the package has no such file, and its role is taken by the case store and case report.
- The "Recent decisions" section of version 1.0; decisions appear in the brief only as the record that changed state, and in full in the case report.
- Any reference to the author's earlier projects or setup.
