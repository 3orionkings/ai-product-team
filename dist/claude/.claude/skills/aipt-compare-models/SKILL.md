---
name: aipt-compare-models
description: "W07 Would another model improve this feature? Inputs: Current and candidate models; Frozen cases; Quality, latency and cost limits. Returns: Like-for-like comparison; Uncertainty; Migration or retention recommendation. Runs the AI Product Team compare-models workflow from this session."
license: See LICENSE_PENDING.md in the ai-product-team repository.
metadata:
  aipt_entry: "W07"
  aipt_version: "0.1.0"
---

# W07 · Would another model improve this feature?

Request: $ARGUMENTS

Run this workflow from the current session as the root orchestrator, following the `aipt-start` skill for routing, dispatch, gates and the case ledger. Load `aipt-start` first if it is not already loaded. The full procedure, stage by stage, is in `references/recipe.md`; read it before dispatching.

Manager: `aipt-systems-manager` · Minimum risk: R1 (raise it when the inputs or actions require it).

## Inputs

- Current and candidate models
- Frozen cases
- Quality, latency and cost limits

If an input is missing and would change the result, ask for it before dispatching.

## Outputs

- Like-for-like comparison
- Uncertainty
- Migration or retention recommendation

## Work graph

| # | Stage | Role | Artifact | Runs | Gate |
|---|---|---|---|---|---|
| 1 | Select candidates | `aipt-model-selection-analyst` | `candidates.json` | always |  |
| 2 | Freeze comparison | `aipt-evaluation-designer` | `comparison-plan.json` | always |  |
| 3 | Run | `aipt-evaluation-runner` | `candidate-results.json` | always |  |
| 4 | Measure economics | `aipt-cost-analyst` | `cost-comparison.json` | always |  |
| 5 | Measure waiting | `aipt-latency-analyst` | `latency-comparison.json` | always |  |
| 6 | Review | `aipt-systems-manager` | `model-decision-proposal.md` | always | review |

Run stages in order, except where `references/recipe.md` marks two as parallel. Skip a stage only when a current accepted artifact of its type already exists in the case, and say so in the route plan. A stage marked with a condition runs only when that condition holds in the case.

## Gates you may not skip

- Review stages: Review.
- Stages that need an independent reviewer (a fresh subagent that authored nothing it reviews): none.
- A manager's favorable review creates no authority and is not test evidence.

## Conditional specialists

`aipt-dataset-curator`, `aipt-evidence-judge`, `aipt-alternative-advocate`. Add one only for an identified missing dependency, review criterion or risk, and say why in the route plan.

## Acceptance

- Same cases and disclosed settings
- Rates are dated or cost is unknown
- No recommendation based solely on model reputation

## Fixture (unrun)

Scenario: Candidate B looks cheaper per input token but retries more and fails the protected slice.

Expected behavior: The recommendation uses task-level results and stated constraints, not a superficial rate comparison. Unknown charges remain unknown.
