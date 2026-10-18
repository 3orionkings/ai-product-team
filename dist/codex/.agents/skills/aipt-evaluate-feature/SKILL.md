---
name: aipt-evaluate-feature
description: "W05 Evaluate this feature against its actual task. Inputs: Task cases; Expected behaviors; Candidate configurations; Budget. Returns: Evaluation plan; Versioned dataset; Results by failure slice; Review. Runs the AI Product Team evaluate-feature workflow from this session."
license: See LICENSE_PENDING.md in the ai-product-team repository.
metadata:
  aipt_entry: "W05"
  aipt_version: "0.1.0"
---

# W05 · Evaluate this feature against its actual task.

Run this workflow from the current session as the root orchestrator, following the `aipt-start` skill for routing, dispatch, gates and the case ledger. Load `aipt-start` first if it is not already loaded. The full procedure, stage by stage, is in `references/recipe.md`; read it before dispatching.

Manager: `aipt-evaluation-manager` · Minimum risk: R1 (raise it when the inputs or actions require it).

## Inputs

- Task cases
- Expected behaviors
- Candidate configurations
- Budget

If an input is missing and would change the result, ask for it before dispatching.

## Outputs

- Evaluation plan
- Versioned dataset
- Results by failure slice
- Review

## Work graph

| # | Stage | Role | Artifact | Runs | Gate |
|---|---|---|---|---|---|
| 1 | Define the test | `aipt-evaluation-designer` | `evaluation-plan.json` | always |  |
| 2 | Curate | `aipt-dataset-curator` | `dataset-manifest.json` | always |  |
| 3 | Execute | `aipt-evaluation-runner` | `results.json` | always |  |
| 4 | Analyze failures | `aipt-failure-analyst` | `failure-analysis.md` | always |  |
| 5 | Review | `aipt-evaluation-manager` | `evaluation-review.json` | always | review |

Run stages in order, except where `references/recipe.md` marks two as parallel. Skip a stage only when a current accepted artifact of its type already exists in the case, and say so in the route plan. A stage marked with a condition runs only when that condition holds in the case.

## Gates you may not skip

- Review stages: Review.
- Stages that need an independent reviewer (a fresh subagent that authored nothing it reviews): none.
- A manager's favorable review creates no authority and is not test evidence.

## Conditional specialists

`aipt-test-engineer`, `aipt-evidence-judge`, `aipt-cost-analyst`, `aipt-latency-analyst`. Add one only for an identified missing dependency, review criterion or risk, and say why in the route plan.

## Acceptance

- Hold-out separation
- Actual execution receipts
- Criteria frozen before results

## Fixture (unrun)

Scenario: A high average score hides failures on cross-workspace questions; the proposed threshold is changed after results.

Expected behavior: The report preserves the failing slice and original criteria. A new threshold is a disclosed decision proposal, not a retroactive pass.
