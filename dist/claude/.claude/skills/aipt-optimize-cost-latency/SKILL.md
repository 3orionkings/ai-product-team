---
name: aipt-optimize-cost-latency
description: "W08 Reduce cost or waiting without losing required quality. Inputs: Measured usage and traces; Rates; Outcome floor; Workload slices. Returns: Bottleneck and cost model; Candidate changes; Quality-preserving experiment plan. Runs the AI Product Team optimize-cost-latency workflow from this session."
license: See LICENSE_PENDING.md in the ai-product-team repository.
metadata:
  aipt_entry: "W08"
  aipt_version: "0.1.0"
---

# W08 · Reduce cost or waiting without losing required quality.

Request: $ARGUMENTS

Run this workflow from the current session as the root orchestrator, following the `aipt-start` skill for routing, dispatch, gates and the case ledger. Load `aipt-start` first if it is not already loaded. The full procedure, stage by stage, is in `references/recipe.md`; read it before dispatching.

Manager: `aipt-operations-manager` · Minimum risk: R0 (raise it when the inputs or actions require it).

## Inputs

- Measured usage and traces
- Rates
- Outcome floor
- Workload slices

If an input is missing and would change the result, ask for it before dispatching.

## Outputs

- Bottleneck and cost model
- Candidate changes
- Quality-preserving experiment plan

## Work graph

| # | Stage | Role | Artifact | Runs | Gate |
|---|---|---|---|---|---|
| 1 | Cost the completed job | `aipt-cost-analyst` | `cost-model.json` | always |  |
| 2 | Map delay | `aipt-latency-analyst` | `latency-model.json` | always |  |
| 3 | Design candidate changes | `aipt-workflow-architect` | `optimization-options.md` | `missing_current_artifact` |  |
| 4 | Preserve the floor | `aipt-evaluation-designer` | `optimization-test-plan.json` | `missing_current_artifact` |  |
| 5 | Review | `aipt-operations-manager` | `optimization-review.md` | always | review |

Run stages in order, except where `references/recipe.md` marks two as parallel. Skip a stage only when a current accepted artifact of its type already exists in the case, and say so in the route plan. A stage marked with a condition runs only when that condition holds in the case.

## Gates you may not skip

- Review stages: Review.
- Stages that need an independent reviewer (a fresh subagent that authored nothing it reviews): none.
- A manager's favorable review creates no authority and is not test evidence.

## Conditional specialists

`aipt-workflow-architect`, `aipt-retrieval-designer`, `aipt-outcome-analyst`, `aipt-evaluation-designer`, `aipt-alternative-advocate`. Add one only for an identified missing dependency, review criterion or risk, and say why in the route plan.

## Acceptance

- No fabricated prices or token totals
- Quality constraints remain fixed
- Savings are hypotheses until measured

## Fixture (unrun)

Scenario: Trace spans run in parallel and only per-stage percentile numbers are supplied.

Expected behavior: The analyst does not add p95s and call the result end-to-end p95. It identifies the measurement missing before claiming a latency improvement.
