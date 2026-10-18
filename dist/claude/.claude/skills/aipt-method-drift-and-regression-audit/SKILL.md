---
name: aipt-method-drift-and-regression-audit
description: Drift audit, regression check, parity, baseline versus changed, invariants, allowed deltas, hidden drift, migration, refactor, rewrite, consolidation. Compare a baseline version and a changed version of an artifact or behavior against declared invariants and allowed deltas; classify each difference as exact parity, intentional change, ambiguous, regression or hidden drift; root-cause regressions and name the minimum repair or the decision that would bless the deviation. Use after a migration, refactor or rewrite when parity matters. Not for greenfield work with no baseline.
license: MIT
metadata:
  aipt_skill_id: "S07"
  aipt_provenance: "adapt"
  aipt_version: "0.1.0"
---

# Drift and regression audit

## Purpose

Compare a baseline and a changed version of an artifact, system or behavior; document semantic and structural drift; and determine whether parity or intended behavior was preserved. The comparison runs against a declared contract (invariants, allowed deltas, surfaces in scope), so the verdict is about agreement with that contract, not about whether the change is good.

## Use when

- A migration, refactor, consolidation or rewrite has produced a new version and the old one is still available as a baseline.
- The requesting role wants parity with an existing system or behavior, or a work order claims behavior-parity evidence that must be checked.
- The risk is subtle drift (a dropped clause, a renamed field with changed meaning, a reordered check) rather than obvious breakage.
- A prompt set, role catalog, repository, schema or architecture has several generations and a role must say which differences matter.
- A change-impact or dependency role needs to know which invariants and dependents the change touched.

## Do not use when

- There is no baseline to compare against. Use `aipt-method-independent-audit` (S10) to verify the artifact against its acceptance criteria instead.
- The task is greenfield and parity is irrelevant. Review the artifact on its own terms with the authoring role's reviewer.
- The question is whether the changed version passes its checks. Use `aipt-method-evaluation-execution-and-receipts` (S19) to run them and S10 to judge the result; feed any failure into this skill as a candidate regression.
- The task is to record sources, claims and dependency links. Use `aipt-method-evidence-and-lineage` (S12). This skill compares two versions; it does not maintain the ledger.
- The question is which invariants the system should have. Use `aipt-method-requirements-and-acceptance` (S13) to write them; this skill audits against invariants already stated.

## Required inputs

Each input is an immutable version reference from the task envelope.

- **Baseline**: an `artifact` version id, or a `source` version id for external behavior, or a `validation` version id for recorded behavior. If missing, return `out_of_scope`; this skill cannot run without a baseline.
- **Changed version**: an `artifact` version id. If missing, return `needs_input`.
- **What must remain equivalent**: `requirement` version ids (protected flags noted) or a `decision` version id that names the invariants. If missing, derive candidate invariants from the baseline's own stated rules and output contract, label each `derived`, and ask for confirmation in `requested_followups` before issuing a parity verdict.
- **What is intentionally allowed to differ**: a `proposal` or `decision` version id listing allowed deltas. If missing, treat every difference as unclassified until step 3 and never promote one to intentional on your own authority.
- **Surface area in scope** (optional): the files, flows or behaviors the audit covers. If missing, cover every surface the invariants touch and record anything else as not examined.

## Method

1. **Define the comparison contract.** Before reading the diff, write down the invariants (each with the requirement or decision version that states it), the acceptable deltas, the unacceptable drift (invariant violations and any rule the requester called out) and the surfaces in scope. Give every invariant an id. Mark `derived` invariants as such.
2. **Compare at every level in scope.** For each invariant, locate the clause, structure or behavior that carries it in the baseline and the corresponding place in the changed version. Compare at six levels: structure (files, sections, fields), behavior (what happens on a given input), semantics (what a term or field means), governance and safety constraints (permissions, refusals, protected rules), output contract (keys, statuses, shapes) and user-facing workflow (the steps a person performs). Record one row per invariant per level with both locations and what differs.
3. **Classify each difference.** Use exactly these categories: `exact_parity` (same meaning and effect), `intentional_change` (listed in the allowed deltas, cited by id), `ambiguous` (meaning may or may not have changed; state both readings and the judgment needed), `regression` (an invariant no longer holds), `hidden_drift` (meaning changed without a visible structural change, or a constraint disappeared with no delta listing it). A difference absent from the allowed deltas is `ambiguous` with a requested decision, never `intentional_change` on your judgment alone.
4. **Assign severity and impact.** For each `regression`, `hidden_drift` and `ambiguous` row, state the invariant at stake, who or what depends on it (cite dependent versions where known) and the observable consequence if the change shipped. Severity follows the protected flag and the consequence, not the size of the diff.
5. **Root-cause real regressions.** For each `regression` and `hidden_drift`, name the mechanism: missing logic, changed assumption, renamed but semantically altered structure, lost constraint, incomplete backfill or broken sequencing. Quote the baseline passage and the changed passage side by side.
6. **Check the critical paths.** List the paths the invariants depend on most. Confirm each was compared at every level in scope. Any critical path you could not compare blocks a `parity_preserved` verdict.
7. **Recommend the repair path.** For each regression or hidden drift, state the minimum change that restores the invariant, or the decision that would formally bless the deviation as intentional (a `decision` on the invariant's requirement; a protected requirement needs the human owner). Prefer the smallest diff a reader can verify against the baseline passage.
8. **Issue the verdict.** `parity_preserved` when every invariant row is `exact_parity` or `intentional_change` and every critical path was checked; `partial_drift` when `ambiguous` or `hidden_drift` rows remain and no invariant is violated; `regression` when any invariant row is `regression`. Name the row that set the verdict.

## Output contract

Produce `drift-audit.json` (or `drift-audit.md` with the same headings), registered as an `artifact` of kind `review` and linked `derived_from` both compared versions:

```
{
  "baseline": id, "changed": id,
  "comparison_contract": {
    "invariants": [ { "id", "statement", "source": version id, "derived": bool } ],
    "allowed_deltas": [ { "id", "statement", "source" } ],
    "surfaces": [...]
  },
  "findings": [ { "id", "invariant", "level", "category", "baseline_location", "changed_location", "difference", "severity", "impact" } ],
  "root_causes": [ { "finding", "mechanism", "baseline_quote", "changed_quote" } ],
  "repairs": [ { "finding", "minimum_fix", "or_bless_by": "decision on <requirement id>" } ],
  "critical_paths": [ { "path", "checked": bool, "levels": [...] } ],
  "verdict": "parity_preserved|partial_drift|regression",
  "verdict_set_by": "<finding id>"
}
```

Envelope fields: `findings` (one per non-parity row, category-tagged), `evidence_refs` (both version ids with every quoted location), `artifact_refs` (the audit), `proposed_links` (`contradicts` from the changed version to the violated requirement for each regression; `verifies` where parity was shown, for the dependency role to accept), `uncertainties` (derived invariants, surfaces not examined, ambiguous rows), `requested_followups` (decisions on ambiguous rows, confirmation of derived invariants, repair work orders). Fill `observed_checks` only when you executed a comparison command or replayed a check; a textual comparison is a reading, not a check. Fill `scope_violations` when the changed version reaches outside its declared write scope.

## Evidence and uncertainty rules

- A parity claim is supported only by the two located passages, or two observed behaviors with receipts, placed side by side. A row with one location is `ambiguous`, not parity.
- "The clause is gone" is an observation. "The behavior changed" is a hypothesis until a validation shows it or the clause was the only carrier of the behavior; say which applies.
- Treat a check that passed against the baseline as a historical pass whose applicability to the changed version is unestablished; cite it as parity evidence only when a validation record exists for the changed version.
- Record the comparison's claims and links through `aipt-method-evidence-and-lineage` (S12). This skill produces the comparison; S12 owns how the resulting claims, versions and dependency edges are kept.

## Guardrails

- Do not treat word overlap as proof of semantic parity. Instead, compare the meaning of each invariant's carrier at the semantic and behavior levels, and classify a passage that reads the same but means something else as `hidden_drift`.
- Do not label every change a regression. Instead, check each difference against the allowed deltas first and reserve `regression` for a violated invariant.
- Do not ignore hidden governance or sequencing differences. Instead, compare the governance and workflow levels for every invariant, including the order of checks and the behavior when a required input is absent.
- Do not claim parity without checking the critical paths. Instead, list them, mark each checked or not, and return `partial_drift` when one could not be checked.
- Do not bless a deviation as intentional on your own judgment. Instead, mark it `ambiguous` and request a decision on the requirement it affects.

## Success criteria

The audit succeeds when a reader can see:

- what changed, by invariant and level, with both locations;
- whether it matters, through category and severity tied to a named dependent;
- why it happened, through the root-cause mechanism and side-by-side quotes;
- what to fix or accept, through a minimum repair or a named decision;
- how far the verdict can be trusted, through the critical-path checklist and the derived-invariant list.

## Example

Reply Assist retrieval instructions at Larkspur Support: baseline `art-0520` against changed `art-0531`, produced by a consolidation work order. Invariants come from protected requirements `req-014` (drafts are never sent) and `req-017` (retrieval returns records only from the requesting agent's workspace and denies when the workspace id is missing). Allowed delta `dec-088`: tone wording and section order may change.

```json
{
  "baseline": "art-0520", "changed": "art-0531",
  "comparison_contract": {
    "invariants": [
      { "id": "I1", "statement": "Output action is draft_only; no send path.", "source": "req-014", "derived": false },
      { "id": "I2", "statement": "Retrieval filters by the requesting agent's workspace_id and denies when it is missing.", "source": "req-017", "derived": false }
    ],
    "allowed_deltas": [ { "id": "D1", "statement": "Tone wording and section order.", "source": "dec-088" } ],
    "surfaces": ["retrieval section", "output contract", "tone section"]
  },
  "findings": [
    { "id": "R1", "invariant": "I1", "level": "output_contract", "category": "exact_parity", "baseline_location": "art-0520 Output", "changed_location": "art-0531 Output", "difference": "none; action enum unchanged", "severity": "none", "impact": "" },
    { "id": "R2", "invariant": "I2", "level": "semantics", "category": "hidden_drift", "baseline_location": "art-0520 Retrieval para 2", "changed_location": "art-0531 Retrieval para 1", "difference": "Filter field renamed from workspace_id to tenant; tenant is not defined in the schema the drafter receives.", "severity": "high", "impact": "Dependent: draft-writer role (art-0415). A drafter cannot populate an undefined field, so the filter may be skipped." },
    { "id": "R3", "invariant": "I2", "level": "governance", "category": "regression", "baseline_location": "art-0520 Retrieval para 3", "changed_location": "absent", "difference": "'If workspace_id is missing, return no records and report the gap' has no counterpart.", "severity": "high", "impact": "Protected requirement req-017 no longer carried; ws-alpha and ws-beta records could mix." },
    { "id": "R4", "invariant": "none", "level": "structure", "category": "intentional_change", "baseline_location": "art-0520 Tone", "changed_location": "art-0531 Tone", "difference": "Reordered; wording tightened.", "severity": "none", "impact": "Covered by D1." }
  ],
  "root_causes": [
    { "finding": "R3", "mechanism": "lost_constraint", "baseline_quote": "If workspace_id is missing, return no records and report the gap.", "changed_quote": "(no corresponding sentence)" },
    { "finding": "R2", "mechanism": "renamed_but_semantically_altered", "baseline_quote": "filter: workspace_id = agent.workspace_id", "changed_quote": "filter: tenant = agent.tenant" }
  ],
  "repairs": [
    { "finding": "R3", "minimum_fix": "Restore the deny-when-missing sentence verbatim in the Retrieval section.", "or_bless_by": "decision on req-017 (protected; requires the human owner)" },
    { "finding": "R2", "minimum_fix": "Revert the field name to workspace_id, or add tenant to the schema under a recorded decision.", "or_bless_by": "decision on req-017" }
  ],
  "critical_paths": [
    { "path": "draft-only output", "checked": true, "levels": ["output_contract", "behavior"] },
    { "path": "workspace filter", "checked": true, "levels": ["semantics", "governance", "behavior"] }
  ],
  "verdict": "regression",
  "verdict_set_by": "R3"
}
```

Envelope: `findings` = R2, R3 (R1 and R4 appear only in the artifact); `proposed_links` = ["art-0531 contradicts req-017", "art-0531 verifies req-014"]; `uncertainties` = ["Behavior level for I2 compared on text only; no retrieval run observed"]; `observed_checks` = []; `requested_followups` = ["Repair work order for R3 and R2", "Confirm whether tenant was an intended rename"].
