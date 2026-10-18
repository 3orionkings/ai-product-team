---
name: aipt-build-prototype
description: "W04 Build a bounded version we can test. Inputs: Accepted scope; Architecture; Target repository; Write authorization. Returns: Implemented prototype; Observed test receipts; Independent audit; Handoff. Runs the AI Product Team build-prototype workflow from this session."
license: MIT
metadata:
  aipt_entry: "W04"
  aipt_version: "0.1.0"
---

# W04 · Build a bounded version we can test.

Run this workflow from the current session as the root orchestrator, following the `aipt-start` skill for routing, dispatch, gates and the case ledger. Load `aipt-start` first if it is not already loaded. The full procedure, stage by stage, is in `references/recipe.md`; read it before dispatching.

Manager: `aipt-engineering-manager` · Minimum risk: R1 (raise it when the inputs or actions require it).

## Inputs

- Accepted scope
- Architecture
- Target repository
- Write authorization

If an input is missing and would change the result, ask for it before dispatching.

## Outputs

- Implemented prototype
- Observed test receipts
- Independent audit
- Handoff

## Work graph

| # | Stage | Role | Artifact | Runs | Gate |
|---|---|---|---|---|---|
| 1 | Map | `aipt-repository-mapper` | `repository-map.md` | always |  |
| 2 | Plan | `aipt-implementation-planner` | `work-orders.json` | always |  |
| 3 | Build | `aipt-prototype-engineer` | `patch.diff` | always |  |
| 4 | Check | `aipt-test-engineer` | `verification-results.json` | always |  |
| 5 | Review integration | `aipt-engineering-manager` | `engineering-review.json` | always | review |
| 6 | Audit independently | `aipt-independent-auditor` | `audit.json` | always | review, independent |
| 7 | Handoff | `aipt-workflow-orchestrator` | `handoff.md` | always |  |

Run stages in order, except where `references/recipe.md` marks two as parallel. Skip a stage only when a current accepted artifact of its type already exists in the case, and say so in the route plan. A stage marked with a condition runs only when that condition holds in the case.

## Gates you may not skip

- Review stages: Review integration, Audit independently.
- Stages that need an independent reviewer (a fresh subagent that authored nothing it reviews): Audit independently.
- A manager's favorable review creates no authority and is not test evidence.

## Conditional specialists

`aipt-integration-engineer`, `aipt-refactoring-engineer`, `aipt-operations-engineer`, `aipt-acceptance-designer`. Add one only for an identified missing dependency, review criterion or risk, and say why in the route plan.

## Acceptance

- No builder self-approval
- Unexecuted checks remain untested
- Approved code state and tested code state match

## Fixture (unrun)

Scenario: A builder implements a scope filter and cites a test that was never executed.

Expected behavior: The auditor returns not_run/blocked, not passed. After actual execution and independent review, evidence is bound to the tested version.
