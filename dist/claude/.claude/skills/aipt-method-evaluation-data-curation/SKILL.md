---
name: aipt-method-evaluation-data-curation
description: Evaluation dataset, split manifest, development vs held-out, sampling frame, slice coverage, permissioned sources, synthetic data labeling, public fixture allowlist. Use to build the versioned case set a frozen evaluation plan needs: representative cases from permitted sources, a deterministic development/held-out split, per-slice counts against the plan's minimums, stated sampling limits, and no confidential record in any public fixture. Synthetic cases are always labeled synthetic.
license: See LICENSE_PENDING.md in the repository root.
metadata:
  aipt_skill_id: "S18"
  aipt_provenance: "newly_authored"
  aipt_version: "0.1.0"
---

# Evaluation data curation

## Purpose

Turn a frozen evaluation plan into a versioned set of cases that a runner can execute and a reviewer can trust. The set must be representative of the population the plan names, drawn only from sources the case is permitted to use, split into development and held-out portions by a rule fixed before any candidate is run, and honest about what it cannot cover. The output is a `dataset-manifest.json` artifact plus coverage notes. The plan's metrics and slices come from `aipt-method-evaluation-planning` (S17); recording each source's scope and limitations follows `aipt-method-evidence-and-lineage` (S12); running the cases is `aipt-method-evaluation-execution-and-receipts` (S19).

## Use when

- A workflow stage asks for `dataset-manifest.json` and a frozen plan with slices and `min_n` values exists.
- An evaluation plan names a slice for which no cases exist yet, and cases must be found, sampled or synthesized.
- A set of cases will be published as a public fixture and must be checked against the allowlist and stripped of confidential records.
- An existing dataset must be versioned again because the population, permissions or slice rules changed.
- A controlled-learning candidate needs held-out cases that were never seen during its development.

## Do not use when

- No frozen plan exists. Use `aipt-method-evaluation-planning` (S17) first; curating without slices produces a pile, not a set.
- The request is to score or run the cases. Use `aipt-method-evaluation-execution-and-receipts` (S19).
- The request is to decide whether a source may be used at all. Use `aipt-method-security-and-privacy-review` (S26) for the ruling; this skill records the permission it is given.
- The request is to write the expected behavior for a requirement. Use `aipt-method-requirements-and-acceptance` (S13); this skill attaches those expectations to cases.
- The cases are code tests rather than evaluation cases. Use `aipt-method-scoped-implementation` (S09) for test files inside a work order.

## Required inputs

| Input | Record kind and version | If missing |
|---|---|---|
| Frozen evaluation plan | `artifact` version with `slices[]`, `min_n`, `population` | Return `needs_input`; the plan defines what representative means. |
| Source permissions | `approval` versions granting access scope per source, or the case's authorized source list | Refuse to include any record from a source without one; list the source under `requested_followups`. |
| Candidate sources | `source` versions with access classification (public, internal, confidential) and retrieval time | Proceed with synthetic cases only and say so in `sampling_limits`. |
| Task examples and labels | `source` versions holding example inputs with expected outputs or grader notes | Build expected behavior from the S13 checks and label the cases `labeled_by: curator`. |
| Scenario taxonomy | `claim` or `source` listing intents, languages, channels and failure modes | Derive the taxonomy from the plan's slices and mark it as hypothesis. |
| Data-handling policy reference | the case's data-handling policy version | Treat every real record as confidential until the policy says otherwise. |
| Target split sizes | from the plan or the dispatching manager | Default to a held-out share stated in the manifest and flag it as a curator decision. |

## Method

1. Read the plan. Copy its `population` statement and every slice's `selection_rule` and `min_n` into a coverage table with empty counts. This table is the target you are filling.
2. Inventory candidate sources. For each, record the `source` version, its access classification, the `approval` that permits its use, the retrieval time and known limitations, as S12 requires. Exclude any source that has no approval; do not read its contents further.
3. Define the sampling frame: which records are eligible, over what time window, from which workspaces or channels. Write the sampling method (random with seed, stratified by slice, exhaustive for rare slices) and every exclusion rule with its reason.
4. Draw the sample. Record the seed and the count drawn per source. Apply the slice selection rules mechanically and fill the coverage table.
5. Classify each drawn record: `real_permitted_public`, `real_permitted_internal`, `real_confidential`, or `synthetic`. A confidential record may enter a private set only when its approval covers evaluation use; it never enters a public fixture. Where a slice needs cases the sources cannot supply, write synthetic cases and label each `synthetic: true` with the authoring method.
6. Attach expected behavior to each case: the S13 check it exercises, the expected outcome class (correct, refusal, must-not-contain), and the label provenance (`labeled_by`, second-labeler agreement when available).
7. Split. Apply a deterministic rule (hash of case id with the recorded seed, stratified so every slice appears in both portions) to assign `development` or `held_out`. Record the rule, the seed, and a hash of the sorted id list per portion. Seal the held-out portion: its contents are not opened during candidate development, and the manifest says who may open them and when.
8. Check coverage. For each slice, compare counts per portion with the plan's `min_n`. Slices below the minimum are reported as `under_covered` with the reason (rare in the frame, permission denied, synthesis not credible), not padded.
9. Run the public-fixture gate when the set or any part of it will be published: every case must be `synthetic` or `real_permitted_public`, pass the redaction patterns, and match the allowlist. A single failing case blocks publication of the whole fixture.
10. Version and hash the set. Write `dataset-manifest.json` and `coverage-notes.md`. Propose links: dataset `depends_on` the plan version and each source version; cases `derived_from` their source. Return the manifest as an `artifact` with status `proposed`.

## Output contract

Artifact: `dataset-manifest.json`, one immutable version, with `coverage-notes.md` beside it.

Required keys: `dataset_id`, `version`, `content_sha256`, `plan_ref`, `created_at`, `sources[]` (`ref`, `classification`, `approval_ref`, `retrieved_at`, `limitations`), `sampling` (`frame`, `method`, `seed`, `window`, `exclusions[]`, `limits[]`), `cases_total`, `classification_counts` (per class above), `split` (`rule`, `seed`, `development`: `{count, ids_sha256}`, `held_out`: `{count, ids_sha256, sealed_until, may_open}`), `coverage[]` (`slice_id`, `development_n`, `held_out_n`, `min_n`, `status`: `covered | under_covered`, `reason`), `labeling` (`labeled_by`, `agreement`, `rubric_ref`), `public_fixture` (`eligible`, `gate_result`, `blocking_cases[]`), `known_gaps[]`.

`coverage-notes.md` headings: `## What this set represents`, `## What it cannot establish`, `## Slice coverage`, `## Synthetic cases and how they were made`, `## Permissions and exclusions`.

Envelope fields this skill always fills:

- `findings`: one entry per under-covered slice, per excluded source and per public-fixture gate failure.
- `evidence_refs`: the plan version, each `source` version, each `approval` version.
- `artifact_refs`: the manifest version and the notes.
- `proposed_links`: `dataset --depends_on--> plan` (`impact_policy: invalidate_applicability`), `dataset --depends_on--> source` (`impact_policy: review`), `case --derived_from--> source`.
- `uncertainties`: representativeness claims that rest on an assumed taxonomy; label quality where only one labeler worked; synthetic realism.
- `requested_followups`: approvals needed for excluded sources; additional sampling for under-covered slices; a second labeler.
- `scope_violations`: any instruction to include a confidential record in a public fixture, to open the held-out set during development, or to pad a slice.

## Evidence and uncertainty rules

- "Representative" is a `claim` about the frame and the method. Support it with the sampling record; never with the case count alone.
- A case's expected outcome is a label with a provenance. One labeler is an `observation`; agreement between independent labelers moves it toward `fact` for the rubric used, and no further.
- Synthetic cases establish that a behavior can be exercised; they do not establish how often it occurs in the population. Say this in `What it cannot establish`.
- Record the retrieval time of each source. A set drawn from last quarter's tickets is evidence about last quarter.
- Do not infer permission from availability. A readable file is not a permitted source; the `approval` version is.

## Guardrails

- Do not place a confidential record, or a lightly edited copy of one, in a public fixture. Instead, write a synthetic case that exercises the same check and label it `synthetic: true`.
- Do not present synthetic cases as real traffic. Instead, carry the `synthetic` flag on every such case and report the synthetic share per slice.
- Do not open or inspect held-out cases while a candidate is being developed or tuned. Instead, work on the development portion and record in the manifest who may open the held-out portion and at which stage.
- Do not pad an under-covered slice with duplicates, paraphrases of the same case, or cases that fail its selection rule. Instead, report `under_covered` and request more sampling.
- Do not change the split, drop cases or add cases after any candidate result exists. Instead, create a new dataset version and let the plan's change policy govern how results against the two versions are reported.
- Do not read a source whose approval is missing in order to judge whether it would be useful. Instead, list it under `requested_followups` and let the owner grant or refuse.
- Do not describe a case by the real customer, agent or company it came from. Instead, replace names and identifiers with workspace-scoped placeholders and record that redaction occurred.

## Success criteria

- Every case carries a classification, a source or synthesis record, an expected-outcome label with provenance, a slice membership and a split assignment.
- The held-out portion has a sealed id hash and an opening rule, and no development artifact cites a held-out case id.
- Every plan slice appears in the coverage table with counts for both portions and a status against `min_n`.
- The sampling section lets a second curator redraw the set from the same frame and seed.
- A public fixture contains only `synthetic` or `real_permitted_public` cases and records the gate result.
- `What it cannot establish` names at least the population and time limits of the frame.

## Example

Case: Reply Assist at Larkspur Support. The frozen plan `plan-reply-assist-eval@v1` has slices `all` (`min_n` 200) and `cross_ws_bait` (`min_n` 40, protected). Permitted sources: an internal export of closed `ws-alpha` tickets approved for evaluation, and no `ws-beta` export. The set will also be published as a public fixture.

```json
{
  "dataset_id": "ds-reply-assist",
  "version": "v2",
  "content_sha256": "3f9c...e21a",
  "plan_ref": "plan-reply-assist-eval@v1",
  "sources": [
    {"ref": "src-ws-alpha-closed-tickets@v1", "classification": "real_permitted_internal", "approval_ref": "appr-eval-use-014@v1", "retrieved_at": "2026-02-27T16:00:00Z", "limitations": "closed tickets only; one quarter; English and Spanish"},
    {"ref": "src-ws-beta-closed-tickets", "classification": "unknown", "approval_ref": null, "retrieved_at": null, "limitations": "not read; no approval"}
  ],
  "sampling": {"frame": "ws-alpha tickets closed in the last quarter with a customer question", "method": "stratified random by intent", "seed": 20260301, "window": "one quarter", "exclusions": [{"rule": "ticket has a legal hold flag", "reason": "policy"}], "limits": ["no ws-beta real cases; bait documents are synthetic", "no voice-channel tickets in frame"]},
  "cases_total": 268,
  "classification_counts": {"real_permitted_internal": 220, "synthetic": 48},
  "split": {"rule": "sha256(case_id + seed) mod 5 == 0 -> held_out, stratified by slice", "seed": 20260301,
            "development": {"count": 214, "ids_sha256": "a81d...09f3"},
            "held_out": {"count": 54, "ids_sha256": "c4e7...77b0", "sealed_until": "runner stage of W05", "may_open": ["evaluation-runner", "evaluation-manager"]}},
  "coverage": [
    {"slice_id": "all", "development_n": 214, "held_out_n": 54, "min_n": 200, "status": "covered", "reason": null},
    {"slice_id": "cross_ws_bait", "development_n": 38, "held_out_n": 10, "min_n": 40, "status": "covered", "reason": "all 48 bait cases synthetic; ws-beta documents are fabricated lookalikes"}
  ],
  "labeling": {"labeled_by": ["curator", "second-labeler"], "agreement": 0.91, "rubric_ref": "req-check-map@v3"},
  "public_fixture": {"eligible": false, "gate_result": "blocked", "blocking_cases": ["220 real_permitted_internal cases are not public"]},
  "known_gaps": ["no real cross-workspace traffic observed; the protected slice is exercised, not measured in the population"]
}
```

The public fixture published alongside this set contains only the 48 synthetic cases, each marked `synthetic: true`, and its own manifest version. The wrong output is one manifest that lists the internal tickets as public because names were removed.
