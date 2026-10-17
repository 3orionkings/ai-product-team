# Implementation plan and acceptance gates

Version 0.1 • 16 October 2026 • Local implementation specification

Build useful vertical slices before expanding coverage, then complete the requested 64-agent catalog and twelve workflows. The sequence below is not permission to stop after creating folders, metadata or a small substitute team. No time-to-completion estimate is asserted.

## 1. Source of truth and change discipline

The PRD controls product behavior and scope. The architecture controls responsibility, state and permission contracts. The registries specify the proposed catalog. Full role bodies, schemas and runtime code must remain consistent with them. Workflow specifications control the named user journeys. The source map controls allowed reuse. Safety, privacy and human authority constraints take precedence over convenience.

When sources or specifications conflict, write the conflict and proposed resolution into the private build decision log. Do not silently discard the stricter constraint. A change to the agreed catalog or a protected authority rule requires user review; a minor internal file layout choice may be recorded and implemented without stopping the work.

## 2. Milestones

### M0 — private source and capability audit

Open the package. Inventory the named local source files without modifying them. Read admitted bodies and decide reuse/adaptation/reference/hold/exclusion. Inspect current host versions and current official documentation. Record capability observations rather than relying on historical setup instructions.

**Deliver:** private source manifest with hashes and reasons, public sanitized attribution proposal, installed-host capability report, source/requirement gaps and chosen workspace.

**Exit:** clear sources are selected; held material remains outside the repo; missing sources are specifically labeled; no unrelated folders were scanned. An unavailable host blocks only that host's live-validation claims, not independent development.

### M1 — canonical contracts and local state controller

Implement registry loading, schema checks, immutable versions, SQLite transactional state, event/idempotency handling, task admission, read-only reports and evidence/dependency links. Add version-bound reviews/decisions and authority checks. Keep direct external actions absent.

**Deliver:** working CLI and tests, not just proposed command help; valid seeded registries; migrations/backup recovery tests; protected transition failures.

**Exit:** deterministic negative cases pass; invalid/stale writes are rejected; the controller's enforcement limits are documented accurately.

### M2 — first complete workflow on a synthetic case

Implement W02 `shape-feature` using actual selected skills, native role dispatch where available, requirements, acceptance mapping, manager review and a derived case report. This proves the packet, state and handoff pattern before creating all adapters and role bodies.

**Deliver:** source-grounded feature brief from the synthetic support-copilot material, with one unresolved authority conflict deliberately retained.

**Exit:** no invented fact fills the conflict; actual native execution is distinguishable from fixture replay; output contracts and artifacts resolve.

### M3 — adapters, installation and the full catalog

Author all 64 full role bodies and all 28 shared skills. Generate both native adapter formats from the neutral registry. Implement safe project installation, dry-run, backups, capability probing, namespacing and uninstall. Generate the public directory from the registry.

**Deliver:** complete role/skill library, two generated adapter sets, install/removal tests, per-role readiness matrix and role-specific scenarios.

**Exit:** all definitions exist and resolve; no persona-only stubs; no private paths or unapproved imported content; no inherited host permission is misrepresented as role isolation.

### M4 — decisions, challenge and controlled change

Implement W11 adjudication and W10 change handling end to end. Track authorship/review conflicts, bounded challenge rounds, dissent, exact approval versions, declared dependencies, applicability changes and selective rework.

**Deliver:** a disputed-choice scenario that can defer; a source correction that invalidates a decision's applicability without deleting requirements; a budget-exhaustion path.

**Exit:** no voting-based truth, no self-granted authority, no stale approval reuse, no recursive runaway delegation and no arbitrary invalidation of unrelated work.

### M5 — build, evaluate and complete workflow coverage

Implement W04 local prototype delivery and W05 evaluations with actual execution receipts. Complete W01 and remaining W03/W06/W07/W08/W09/W12 using shared infrastructure and their distinct contracts. Build the synthetic application with positive and negative scenarios.

**Deliver:** runnable demo, version-pinned tests, local implementation/audit loop, twelve executable recipes and per-workflow coverage matrix.

**Exit:** mock outputs are labeled; independent audit is genuine or specifically blocked; failed checks remain visible; all promised functionality has implementation and tests rather than placeholders.

### M6 — native conformance, evaluation and release preparation

Run adapter conformance on each available host. Execute six core workflows per host. Run role-specific behavior cases within the user-authorized model budget; publish precise actual coverage. Compare selected end-to-end workflows with current native baselines. Perform provenance, privacy, docs and installation review.

**Deliver:** actual commands/logs, compatibility matrix, benchmark methodology and results if run, requirement evidence matrix, sanitized public documentation and release-review report.

**Exit:** any untested host or role is labeled. No new release claim outruns the evidence. Do not push, publish or post; report that the local repository is ready for human review, or name the exact blockers.

## 3. Acceptance-test catalog

| ID | Test group | Required assertions |
|---|---|---|
| AT-01 | Catalog consistency | Exactly 64 unique agents; 10 teams of 6 plus 4 leadership roles; valid manager/director edges; 28 skills; 12 workflows; JSON/Markdown/HTML agree; no dangling IDs. |
| AT-02 | Role substance | Every role has full use/skip conditions, unique method/output, evidence rules, escalation and positive/negative fixtures; readiness labels match actual work. Similarity review detects near-duplicate filler. |
| AT-03 | Provenance | Every reused body was actually read; public/private manifests separated; attribution and holds correct; no excluded source in public tree or Git index. |
| AT-04 | Adapter conformance | Both formats parse; actual discovery and child execution are measured separately; native IDs captured; unsupported settings fail loudly; no unsupported per-agent sandbox claim. |
| AT-05 | Workflow contracts | All twelve recipes have reachable success, needs-input, blocked and failure paths; output schemas and role references resolve; no arbitrary code in predicates. |
| AT-06 | Selective routing | Narrow tasks activate only justified roles; no compulsory director/manager ladder; flat native dispatch baseline; required review gates cannot be pruned. |
| AT-07 | Budget enforcement | Task/retry/concurrency counters are atomic; exhaustion stops dispatch; a blocked child releases reconciled capacity; unavailable dollars/tokens remain unknown. |
| AT-08 | Execution identity | A parent's role-played answer cannot count as a spawned child; sequential/manual fallback is labeled; actual host receipts are retained. |
| AT-09 | Authority and versions | Judge cannot execute; agent cannot grant itself delegation; version-changed approval rejected; revoked/expired/wrong-target grants rejected; no initial external-write command. |
| AT-10 | Review independence | An artifact author cannot independently approve it; unknown context origin does not satisfy a required fresh review; manager summary is not test evidence. |
| AT-11 | Adversarial convergence | Challenges are material and testable; max rounds enforced; judge may defer; decisive constraint beats majority preference; dissent persists. |
| AT-12 | Evidence integrity | Missing citations, real-but-irrelevant citations, conflicting source scope and unsupported promotion are detected; exact source versions resolve. |
| AT-13 | Dependency/impact | Reverse propagation reaches declared dependents only; incomplete links are exposed; changed target/test/data/config affects applicability; failed implementation does not retire a requirement. |
| AT-14 | Verification receipts | Actual command and exit observed; timeout differs from failure; skipped tests differ from passed; scope coverage explicit; replay/live modes cannot be confused. |
| AT-15 | Persistence/recovery | Stale writes rejected; retries idempotent; accepted events survive interruption; consistent backup restores; reports regenerate; portable import/export preserves links. |
| AT-16 | Data and security boundary | Source injection cannot authorize excluded reads; path traversal/symlink escapes rejected by controlled paths; secrets/private traces absent in export; no claim of hostile same-user isolation. |
| AT-17 | Installer safety | Dry-run changes nothing; preexisting files preserved; existing user edits cause conflict; only owned unchanged files removed; no global install/hooks/schedule by default. |
| AT-18 | Model/economics configuration | No permanently best model; dates/rates recorded; missing costs unknown; completed-task cost includes disclosed retries; p95s not summed as end-to-end percentile. |
| AT-19 | Synthetic demo | Draft-only copilot works within its declared scope; unsafe authority change blocked; negative isolation fixture causes targeted review; corrected version revalidated. |
| AT-20 | Evaluation claims | Rubrics/datasets frozen; held-out cases separate; baseline comparable; failures/overhead shown; live coverage per role/workflow/host explicit. |
| AT-21 | Controlled learning | Candidate change isolated; held-out regressions prevent promotion; policy cannot self-weaken; previous version and rollback remain available. |
| AT-22 | Human directory | Offline operation, keyboard search/filter, readable grouping, no color-only status; count/labels generated from registry; no external fonts/assets required. |

## 4. Requirement evidence ledger

Create `docs/requirement-evidence.csv` with one row per PRD requirement and separate child rows for materially different acceptance clauses. Columns:

`requirement_id`, `clause`, `implementation_paths`, `test_ids`, `last_target_version`, `actual_command_or_scenario`, `receipt_paths`, `result`, `reviewer`, `review_context`, `host`, `host_version`, `remaining_gap`.

Allowed results: `not_started`, `implemented_not_verified`, `passed_for_scope`, `failed`, `blocked`, `not_applicable_with_reason`. Do not make every row PASS because a test suite exits zero. A single command can support multiple requirements only when the test actually exercises each one.

## 5. Fixture and live-test distinction

The supplied schema examples and registries are design seeds. Validate their syntax and internal consistency, then extend them into actual production contracts. A fixture replay uses predetermined outputs to check software flow. It is not a demonstration of live agent judgment or a native host's execution.

Minimum fixture definitions: 128 role scenarios (one positive and one negative per role), twelve workflow scenarios and all AT groups. Their presence is separate from model execution. Record which scenarios were run with actual models, which used replay and which remain unrun.

All catalog entries need complete role bodies. Six core workflows need end-to-end execution on both hosts for the cross-host release claim. When a live run is unavailable or would exceed the authorized budget, mark it blocked and leave runnable instructions. Do not simulate an unavailable host and call it compatible.

## 6. Build-agent organization

The local Codex implementation can itself use a small builder/reviewer arrangement: source/provenance reviewer, controller engineer, adapter engineer, role/skill author, workflow/demo engineer and independent integration reviewer. Only assign disjoint files or use isolated worktrees. The builder remains responsible for reconciling all outputs.

The product's 64-agent organization does not require 64 implementation workers. Do not create a recursive agent team to build another recursive agent team. The implementation objective is working contracts and useful workflows, not a large process diagram.

## 7. Publication review

Inspect the actual public tree, generated exports, Git status and staged files. Exclude private source paths, original audits, hidden caches, real prompts/transcripts, auth files, run databases, private examples and source snapshots. Check license/attribution and third-party notices. Verify the README's commands and claimed support against recorded evidence. Scan for confidential markers, then perform semantic review; absence of marker hits alone is not clearance.

## 8. Final local build report

Report repository path; source reuse/adaptation/new-work table; role/skill/workflow counts; implemented CLI functions; actual commands/results; per-host compatibility; live versus replay scenario coverage; remaining blocked requirements; private/source exclusions; and the first runnable user workflow. State plainly whether nothing has been pushed or published.

A polished directory or a large number of Markdown files is not sufficient completion. A repository with precise blocked status can be a useful interim result, but it must not be represented as a fully verified release.
