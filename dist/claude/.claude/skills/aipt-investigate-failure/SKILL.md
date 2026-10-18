---
name: aipt-investigate-failure
description: "W06 Find out why this feature is failing. Inputs: Failure reports; Authorized traces; Recent changes; Outcome definitions. Returns: Validated symptom; Hypotheses; Discriminating tests; Repair recommendation. Runs the AI Product Team investigate-failure workflow from this session."
license: See LICENSE_PENDING.md in the ai-product-team repository.
metadata:
  aipt_entry: "W06"
  aipt_version: "0.1.0"
---

# W06 · Find out why this feature is failing.

Request: $ARGUMENTS

Run this workflow from the current session as the root orchestrator, following the `aipt-start` skill for routing, dispatch, gates and the case ledger. Load `aipt-start` first if it is not already loaded. The full procedure, stage by stage, is in `references/recipe.md`; read it before dispatching.

Manager: `aipt-evaluation-manager` · Minimum risk: R0 (raise it when the inputs or actions require it).

## Inputs

- Failure reports
- Authorized traces
- Recent changes
- Outcome definitions

If an input is missing and would change the result, ask for it before dispatching.

## Outputs

- Validated symptom
- Hypotheses
- Discriminating tests
- Repair recommendation

## Work graph

| # | Stage | Role | Artifact | Runs | Gate |
|---|---|---|---|---|---|
| 1 | Validate the report | `aipt-context-analyst` | `incident-brief.md` | always |  |
| 2 | Find discriminating cuts | `aipt-failure-analyst` | `hypotheses.json` | always |  |
| 3 | Reconcile evidence | `aipt-contradiction-analyst` | `conflicts.json` | always |  |
| 4 | Investigate targeted causes | `aipt-repository-mapper` | `diagnostic-evidence.json` | `evidence_points_to_code` |  |
| 5 | Review and contain | `aipt-evaluation-manager` | `remediation-recommendation.md` | always | review |

Run stages in order, except where `references/recipe.md` marks two as parallel. Skip a stage only when a current accepted artifact of its type already exists in the case, and say so in the route plan. A stage marked with a condition runs only when that condition holds in the case.

## Gates you may not skip

- Review stages: Review and contain.
- Stages that need an independent reviewer (a fresh subagent that authored nothing it reviews): none.
- A manager's favorable review creates no authority and is not test evidence.

## Conditional specialists

`aipt-repository-mapper`, `aipt-retrieval-designer`, `aipt-tool-integration-designer`, `aipt-outcome-analyst`, `aipt-test-engineer`. Add one only for an identified missing dependency, review criterion or risk, and say why in the route plan.

## Acceptance

- Validate the failure definition first
- Differentiate model, retrieval, tool, UI and data failures
- Repair requires a separate scoped work order

## Fixture (unrun)

Scenario: Support complaints fall after the reporting interface becomes harder to find.

Expected behavior: The analysis distinguishes reporting volume from actual task quality and asks for a discriminating measure before crediting the AI feature.
