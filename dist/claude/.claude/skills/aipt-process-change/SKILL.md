---
name: aipt-process-change
description: "W10 Something changed. What must we revisit? Inputs: Old and new source or artifact; Intended changes; Dependency graph. Returns: Impact queue; Revised proposal; Targeted work orders; Revalidation results. Runs the AI Product Team process-change workflow from this session."
license: MIT
metadata:
  aipt_entry: "W10"
  aipt_version: "0.1.0"
---

# W10 · Something changed. What must we revisit?

Request: $ARGUMENTS

Run this workflow from the current session as the root orchestrator, following the `aipt-start` skill for routing, dispatch, gates and the case ledger. Load `aipt-start` first if it is not already loaded. The full procedure, stage by stage, is in `references/recipe.md`; read it before dispatching.

Manager: `aipt-audit-manager` · Minimum risk: R1 (raise it when the inputs or actions require it).

## Inputs

- Old and new source or artifact
- Intended changes
- Dependency graph

If an input is missing and would change the result, ask for it before dispatching.

## Outputs

- Impact queue
- Revised proposal
- Targeted work orders
- Revalidation results

## Work graph

| # | Stage | Role | Artifact | Runs | Gate |
|---|---|---|---|---|---|
| 1 | Preserve versions | `aipt-change-impact-analyst` | `change-assessment.json` | always |  |
| 2 | Map affected work | `aipt-dependency-steward` | `impact-queue.json` | always |  |
| 3 | Assess contradictions | `aipt-contradiction-analyst` | `correction-proposal.json` | always |  |
| 4 | Authorize the correction | `aipt-audit-manager` | `change-review.json` | always | review |
| 5 | Rework selectively | `aipt-implementation-planner` | `targeted-work-orders.json` | `rework_required` |  |
| 6 | Revalidate | `aipt-independent-auditor` | `revalidation.json` | `revalidation_required` | review, independent |

Run stages in order, except where `references/recipe.md` marks two as parallel. Skip a stage only when a current accepted artifact of its type already exists in the case, and say so in the route plan. A stage marked with a condition runs only when that condition holds in the case.

## Gates you may not skip

- Review stages: Authorize the correction, Revalidate.
- Stages that need an independent reviewer (a fresh subagent that authored nothing it reviews): Revalidate.
- A manager's favorable review creates no authority and is not test evidence.

## Conditional specialists

`aipt-evidence-curator`, `aipt-claim-checker`, `aipt-requirements-writer`, `aipt-refactoring-engineer`, `aipt-test-engineer`, `aipt-decision-recorder`. Add one only for an identified missing dependency, review criterion or risk, and say why in the route plan.

## Acceptance

- Only declared affected dependencies are automatically queued
- Constraints survive failed implementations
- Historical test outcomes are preserved

## Fixture (unrun)

Scenario: A negative test disproves an isolation assumption after a positive test passed.

Expected behavior: The requirement remains mandatory; the release decision is reviewed; the old result remains historical; only relevant implementation/checks are requeued.
