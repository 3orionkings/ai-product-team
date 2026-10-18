---
name: aipt-learn-from-outcomes
description: "W12 Use verified outcomes to improve the product or team. Inputs: Audited runs; Outcomes; Failed approaches; Current versions. Returns: Improvement proposal; Test and evaluation plan; Versioned change and rollback path. Runs the AI Product Team learn-from-outcomes workflow from this session."
license: See LICENSE_PENDING.md in the ai-product-team repository.
metadata:
  aipt_entry: "W12"
  aipt_version: "0.1.0"
---

# W12 · Use verified outcomes to improve the product or team.

Request: $ARGUMENTS

Run this workflow from the current session as the root orchestrator, following the `aipt-start` skill for routing, dispatch, gates and the case ledger. Load `aipt-start` first if it is not already loaded. The full procedure, stage by stage, is in `references/recipe.md`; read it before dispatching.

Manager: `aipt-audit-manager` · Minimum risk: R0 (raise it when the inputs or actions require it).

## Inputs

- Audited runs
- Outcomes
- Failed approaches
- Current versions

If an input is missing and would change the result, ask for it before dispatching.

## Outputs

- Improvement proposal
- Test and evaluation plan
- Versioned change and rollback path

## Work graph

| # | Stage | Role | Artifact | Runs | Gate |
|---|---|---|---|---|---|
| 1 | Measure outcome | `aipt-outcome-analyst` | `outcome-review.md` | always |  |
| 2 | Propose learning | `aipt-learning-steward` | `improvement-proposal.json` | always |  |
| 3 | Check scope and drift | `aipt-change-impact-analyst` | `improvement-impact.json` | always |  |
| 4 | Test | `aipt-evaluation-designer` | `improvement-evaluation-plan.json` | `improvement_needs_evaluation` |  |
| 5 | Review promotion | `aipt-audit-manager` | `promotion-review.json` | always | review |

Run stages in order, except where `references/recipe.md` marks two as parallel. Skip a stage only when a current accepted artifact of its type already exists in the case, and say so in the route plan. A stage marked with a condition runs only when that condition holds in the case.

## Gates you may not skip

- Review stages: Review promotion.
- Stages that need an independent reviewer (a fresh subagent that authored nothing it reviews): none.
- A manager's favorable review creates no authority and is not test evidence.

## Conditional specialists

`aipt-evidence-curator`, `aipt-evaluation-designer`, `aipt-dataset-curator`, `aipt-independent-auditor`, `aipt-dissent-recorder`. Add one only for an identified missing dependency, review criterion or risk, and say why in the route plan.

## Acceptance

- No automatic policy self-modification
- No private traces in public fixtures
- Compare on held-out examples before promoting

## Fixture (unrun)

Scenario: A new prompt fixes the one example from which it was written but fails held-out negative cases.

Expected behavior: The candidate is not promoted. The old version and evaluation results remain available, and no authority rule is weakened.
