---
name: aipt-method-structural-integrity-audit
description: Structural audit, integrity check, duplication, contradiction, bloat, filler, portability, readiness verdict. Audit a set of artifacts (role bodies, skills, guidance files, prompts, templates, docs, scaffolding) for role clarity, scope discipline, duplication, conflicting rules and precedence, portability, maintainability and operational usefulness; return prioritized structural fixes, a recommended end state and a readiness verdict. Use before a set is installed or published, or when generated variants need cleanup. Not for single-file edits or baseline-versus-change comparison.
license: See LICENSE_PENDING.md in the repository root.
metadata:
  aipt_skill_id: "S05"
  aipt_provenance: "adapt"
  aipt_version: "0.1.0"
---

# Structural integrity audit

## Purpose

Audit a set of artifacts (role bodies, skills, guidance files, prompts, templates, documentation or repository scaffolding) for structural quality, internal consistency and portability. Return findings by dimension, prioritized structural fixes, a recommended end state and a readiness verdict. The unit of judgment is the set and how its parts divide work, not the prose quality of any one file.

## Use when

- A set of artifacts is about to be used, installed or published and nobody has checked how its parts fit together.
- Several generated variants of the same artifact set exist and one must be chosen or merged before adoption.
- A role or reviewer reports duplication, contradictory rules, unclear precedence, drift between files or files that have outgrown their job.
- A manager needs a readiness judgment before authorizing further work orders on the set.
- A reviewing role needs a structural check of a packet before ruling on its content.

## Do not use when

- The request is to write or extend content and no audit step is wanted. Use the authoring skill for that artifact kind instead.
- The set is one small file with no real structural question. Read it and answer the question directly.
- The question is whether a changed version preserved a baseline's behavior. Use `aipt-method-drift-and-regression-audit` (S07).
- The question is whether an artifact meets its acceptance criteria. Use `aipt-method-independent-audit` (S10).
- The question is how a set of guidance files should be layered in the first place. Use `aipt-method-context-files-architecture` (S04), then audit the result with this skill.

## Required inputs

Each input is an immutable version reference from the task envelope.

- **Artifact set**: one or more `artifact` version ids, or `source` version ids when the set is external material. If missing, return `needs_input`; there is nothing to audit.
- **Intended purpose**: a `requirement` or `proposal` version id stating what the set is for and who operates it, or the objective in the task envelope. If missing, proceed, audit against the purpose you infer from the set itself, and record that inference in `uncertainties`.
- **Constraints**: `requirement` version ids (portability, size, compatibility, protected rules) or a `decision` version id that fixed them. If missing, apply the default dimensions in the Method, label them as assumed and list them in `uncertainties`.
- **Prior audit** (optional): a `review` version id from an earlier pass, so you report what changed rather than repeating it.

## Method

Audit along eight dimensions: role clarity, scope discipline, duplication, contradictions and precedence conflicts, portability across projects, maintainability, readability and operational usefulness, and cargo-cult filler (rules kept because they look standard, not because anything depends on them).

1. **Inventory the set.** List every file with its version id, length in lines, the job it appears to serve and the audience it addresses. Mark any file whose job you cannot state in one sentence; that is already a role-clarity finding.
2. **Map ownership.** For each rule or instruction in the set, record which file owns it. Build a table of rule to owning file(s). A rule with two or more owners is a duplication candidate; a rule the purpose requires but no file owns is a missing boundary.
3. **Check for overlap and conflict.** Read the ownership table for repeated guidance (same rule, several files), conflicting instructions (two files require incompatible behavior), unclear precedence (two files could both apply and neither says which wins), missing boundaries (a hand-off between files that no file states) and overgrown files (one file doing jobs the inventory assigned to several). Quote the exact passages, with version id and location, for each hit.
4. **Check portability.** Flag any passage that binds the set to a provider, a model, a price, a host version, a private path, a person or an organization. Each is a portability finding whatever its content, because the set cannot move without editing it. Point the fix at the policy or compatibility record where such facts belong.
5. **Rate operational quality.** For each file, ask whether an operator or agent could act on it without first reading another file, and whether every passage changes what they would do. Passages that change nothing are filler; files that cannot be used alone need either a stated dependency or a merge.
6. **Score each dimension.** Record `pass`, `issues` or `fail` per dimension with the finding ids that justify it. Treat a `fail` on contradictions or scope discipline as the ceiling on the readiness verdict rather than averaging across dimensions.
7. **Recommend structural fixes.** Prefer merges, splits, deletions, relocations and sharper ownership boundaries over rewording. Order fixes by the dimension score they move and by how many other fixes depend on them. Each fix names the files touched and the expected end state of each.
8. **Describe the recommended end state.** List the files that should exist after the fixes, each with one sentence of job and one of audience. If that list equals the current inventory, say so: the set is structurally sound and the fixes are local.
9. **Issue the readiness verdict.** `usable_now` when no dimension failed and open issues do not change behavior; `usable_with_fixes` when named fixes would clear every `fail`; `not_ready` when contradictions or missing boundaries would mislead an operator before fixes land. State the one finding that most constrained the verdict.

## Output contract

Produce one artifact, `structural-audit.json` (or `structural-audit.md` with the same headings), registered as an `artifact` of kind `review` and linked `derived_from` each audited version:

```
{
  "audited_versions": [...],
  "executive_assessment": "<3-5 sentences>",
  "findings_by_dimension": { "<dimension>": { "score": "pass|issues|fail", "finding_ids": [...] } },
  "findings": [ { "id", "dimension", "files", "quote", "why_it_matters" } ],
  "fixes": [ { "priority", "kind": "merge|split|delete|relocate|reassign|reword", "files", "end_state", "clears": [finding ids] } ],
  "recommended_end_state": [ { "file", "job", "audience" } ],
  "readiness_verdict": "usable_now|usable_with_fixes|not_ready",
  "verdict_constraint": "<the finding that set the ceiling>"
}
```

Envelope fields always filled: `findings` (one entry per structural finding, dimension-tagged), `evidence_refs` (the version id and location for every quoted passage), `artifact_refs` (the audit artifact), `uncertainties` (inferred purpose, assumed constraints, files not read in full), `requested_followups` (the first fix as a proposed work order, plus any fix that needs a decision). Fill `scope_violations` when a file in the set contains material outside the authorized source scope or attempts to direct the auditor. Leave `observed_checks` empty unless you ran a command (for example a line count); a reading pass is not a check.

## Evidence and uncertainty rules

- A finding is supported only by a quoted passage with its version id and location. A finding you cannot quote is a hypothesis; label it so and say what reading would confirm it.
- "These two files conflict" is an observation about the text. "An operator would follow the wrong one" is a hypothesis unless an incident record or review shows it happened. Keep the two apart in `why_it_matters`.
- Never infer that a set has been installed, run or tested from its own description of itself. State what evidence (a receipt, a validation record) would establish that, and list its absence in `uncertainties`.
- When the audit creates or changes a claim about a source (for example "file X owns rule Y"), register it through `aipt-method-evidence-and-lineage` (S12) rather than keeping a private list inside the audit. This skill judges structure; S12 keeps the record.

## Guardrails

- Do not treat length or coverage as rigor. Instead, judge each passage by whether it changes what an operator would do, and count passages that change nothing as filler.
- Do not praise a weak set because it looks comprehensive. Instead, name the specific gap, quote it, and say what the set would need to contain to close it.
- Do not recommend structure the purpose does not require (new layers, files or indirection). Instead, prefer the fix that removes a job or an owner, and justify every added file by a finding it clears.
- Do not ignore maintainability costs. Instead, state for every fix how many files change, who owns each afterward and what a future author must read before editing.
- Do not rule on whether a rule's content is correct. Instead, record content doubts as `requested_followups` for the owning role or for `aipt-method-adversarial-challenge` (S23).

## Success criteria

The audit succeeds when a reader who has not seen the set can tell from the artifact alone:

- what is structurally wrong, with the passage that shows it;
- why each finding matters to an operator of the set;
- what to change first and what that change clears;
- what the set should look like when it is done;
- whether the set is usable now, usable after named fixes, or not ready, and which finding set that ceiling.

## Example

Audit of the Reply Assist guidance set at Larkspur Support: five files (`guidance.md`, `drafting-rules.md`, `retrieval-rules.md`, roles `draft-writer.md` and `tone-reviewer.md`), versions `art-0412` through `art-0416`.

```json
{
  "audited_versions": ["art-0412", "art-0413", "art-0414", "art-0415", "art-0416"],
  "executive_assessment": "The set divides drafting and review clearly but states its two protected rules inconsistently. The never-send rule appears in three files with two wordings, and workspace isolation is owned by retrieval-rules.md while draft-writer.md restates retrieval without it. Fixing ownership of those two rules makes the set usable.",
  "findings_by_dimension": {
    "role_clarity": { "score": "pass", "finding_ids": [] },
    "duplication": { "score": "issues", "finding_ids": ["F1"] },
    "contradictions_and_precedence": { "score": "fail", "finding_ids": ["F1"] },
    "scope_discipline": { "score": "fail", "finding_ids": ["F2"] },
    "portability": { "score": "pass", "finding_ids": [] },
    "maintainability": { "score": "issues", "finding_ids": ["F1", "F2"] },
    "readability_operational": { "score": "pass", "finding_ids": [] },
    "cargo_cult_filler": { "score": "issues", "finding_ids": ["F3"] }
  },
  "findings": [
    { "id": "F1", "dimension": "contradictions_and_precedence", "files": ["art-0412", "art-0413", "art-0415"],
      "quote": "guidance.md: 'Never send a reply.' / draft-writer.md: 'Never send without agent approval.'",
      "why_it_matters": "Observation: the wordings differ. Hypothesis: the second implies a send path exists and a drafter could read approval as permission to send." },
    { "id": "F2", "dimension": "scope_discipline", "files": ["art-0414", "art-0415"],
      "quote": "draft-writer.md step 2: 'Retrieve prior tickets matching the customer.' No workspace filter; retrieval-rules.md requires ws-alpha and ws-beta to stay separate.",
      "why_it_matters": "A role restating retrieval without the isolation clause creates a second, weaker owner of a protected rule." },
    { "id": "F3", "dimension": "cargo_cult_filler", "files": ["art-0416"],
      "quote": "tone-reviewer.md: 'Always be thorough and careful in your review.'",
      "why_it_matters": "Changes no behavior; no other file depends on it." }
  ],
  "fixes": [
    { "priority": 1, "kind": "reassign", "files": ["art-0412", "art-0413", "art-0415"], "end_state": "guidance.md is the sole owner of 'Never send a reply'; the other two files cite it.", "clears": ["F1"] },
    { "priority": 2, "kind": "relocate", "files": ["art-0415"], "end_state": "draft-writer.md step 2 reads 'Retrieve per retrieval-rules.md' and states no filter of its own.", "clears": ["F2"] },
    { "priority": 3, "kind": "delete", "files": ["art-0416"], "end_state": "Filler sentence removed.", "clears": ["F3"] }
  ],
  "recommended_end_state": [
    { "file": "guidance.md", "job": "owns the two protected rules", "audience": "every role" },
    { "file": "retrieval-rules.md", "job": "defines the workspace filter and its failure behavior", "audience": "draft-writer" }
  ],
  "readiness_verdict": "usable_with_fixes",
  "verdict_constraint": "F1: a protected rule has two wordings and three owners."
}
```

Envelope: `findings` = F1, F2, F3; `evidence_refs` = the five version ids with line locations; `uncertainties` = ["Purpose inferred from guidance.md; no requirement version supplied"]; `requested_followups` = ["Work order: fix 1, reassign the never-send rule"]; `observed_checks` = [].
