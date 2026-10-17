# Adaptation notes: Context-files architecture (S04)

Source: the author's March 2026 draft of Universal Context Files Architect. The notes below describe what the adapted `SKILL.md` keeps, changes and leaves out.

## Preserved

- Purpose: design or improve reusable agent context files (root guidance, host-specific guidance, skill files, command files and related operating documents).
- Use when: a repository or personal workflow needs better AI operating context; the requester wants project-agnostic files or templates; existing files are vague, stale or bloated; universal guidance must be separated from project-specific guidance.
- Do not use when: the requester wants one-off prompt wording; there is no intention to maintain the files as living documentation.
- Core principles, now the second paragraph of Purpose: commands early; real examples over abstract style rules; always / ask-first / never boundaries; concise root files; layered global, repository and module guidance; new rules through real friction, not theory.
- Process steps and their order: distinguish file roles (universal rules, project-level context, module-level overrides, specialist agents, reusable commands, reusable skills); decide what belongs where using the default split; optimize for maintainability (concise top-level files, explicit protected paths, runnable commands, obvious ownership and update cadence, precedence notes); create a recommended minimal but expandable file set.
- Output contract: recommended file architecture; responsibilities of each file; what should remain universal; what should be filled per project; starter templates or drafts if requested.
- Guardrails: no turning a universal file into a project-specific dump; no aspirational sections nobody will maintain; no duplicating rules across files without reason; no hardcoding tools the workflow does not use.
- Success criteria: the resulting system is portable, layered, concise, enforceable in practice and easy to evolve through use.

## Changed

- Required inputs are restated as typed versioned references (`source`, `claim` and `requirement` version ids), each with the behavior to follow when it is missing; protected constraints were added as a fifth input because protected paths belong in the root file.
- Outputs are restated as a named artifact, `context-files-plan.md` with fixed headings including a Boundaries section and a Provisional rules section, plus the envelope fields `findings`, `evidence_refs`, `artifact_refs`, `proposed_links`, `uncertainties`, `requested_followups` and `scope_violations`.
- An inventory step was added at the start of the Method so the existing files are read before roles are assigned, and a tracing step was added so every rule is tied to a recorded friction or protected requirement or marked provisional.
- The host-specific guidance file is described generically, and the specialist agent files are described as roles with write-scope boundaries rather than personas, to satisfy the contract's prohibitions on provider names and persona framing.
- Boundaries in a context file are labeled `requested` until enforcement is shown; enforcement specification is deferred to aipt-method-tool-and-permission-boundaries (S16).
- An Example section was added, using the fictional Reply Assist product at Larkspur Support; the source had none.
- An Evidence and uncertainty rules section was added; it defers record keeping to aipt-method-evidence-and-lineage (S12).
- Do-not-use bullets now route to the neighboring skills S05, S16 and S27 so the method stays distinct from structural audit, tool boundaries and controlled learning.
- Each guardrail now states the alternative behavior, as the authoring contract requires; a guardrail against installing or overwriting files was added, since installation is a separate reviewed action in this package.
- Voice changed to second person imperative throughout.

## Omitted

- The pack-level introduction that described the origin of the drafts in the author's prompt archive, its suggested installation directories and its recommended usage order.
- The specific product filename the source used for the host-specific guidance file; the contract prohibits provider names in skill bodies, so the file is described by its role.
- The agent-style title framing ("Architect"); the adapted skill is a method, not a persona.
