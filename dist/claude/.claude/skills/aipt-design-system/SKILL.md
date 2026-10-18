---
name: aipt-design-system
description: "W03 Design how this AI feature should work. Inputs: Accepted requirements; Data and tool constraints; Repository context. Returns: Architecture; Component contracts; Permissions; Failure and evaluation plan. Runs the AI Product Team design-system workflow from this session."
license: MIT
metadata:
  aipt_entry: "W03"
  aipt_version: "0.1.0"
---

# W03 · Design how this AI feature should work.

Request: $ARGUMENTS

Run this workflow from the current session as the root orchestrator, following the `aipt-start` skill for routing, dispatch, gates and the case ledger. Load `aipt-start` first if it is not already loaded. The full procedure, stage by stage, is in `references/recipe.md`; read it before dispatching.

Manager: `aipt-systems-manager` · Minimum risk: R1 (raise it when the inputs or actions require it).

## Inputs

- Accepted requirements
- Data and tool constraints
- Repository context

If an input is missing and would change the result, ask for it before dispatching.

## Outputs

- Architecture
- Component contracts
- Permissions
- Failure and evaluation plan

## Work graph

| # | Stage | Role | Artifact | Runs | Gate |
|---|---|---|---|---|---|
| 1 | Allocate responsibilities | `aipt-workflow-architect` | `architecture.md` | always |  |
| 2 | Specify tools | `aipt-tool-integration-designer` | `tool-contracts.json` | always |  |
| 3 | Constrain authority | `aipt-safety-boundary-designer` | `authority-and-failure-policy.md` | always |  |
| 4 | Extend only when relevant | `aipt-retrieval-designer` | `retrieval-contract.md` | `requires_retrieval` |  |
| 5 | Review | `aipt-systems-manager` | `architecture-review.json` | always | review |

Run stages in order, except where `references/recipe.md` marks two as parallel. Skip a stage only when a current accepted artifact of its type already exists in the case, and say so in the route plan. A stage marked with a condition runs only when that condition holds in the case.

## Gates you may not skip

- Review stages: Review.
- Stages that need an independent reviewer (a fresh subagent that authored nothing it reviews): none.
- A manager's favorable review creates no authority and is not test evidence.

## Conditional specialists

`aipt-retrieval-designer`, `aipt-model-selection-analyst`, `aipt-security-reviewer`, `aipt-privacy-reviewer`, `aipt-engineering-director`. Add one only for an identified missing dependency, review criterion or risk, and say why in the route plan.

## Acceptance

- Deterministic authority stays outside model judgment
- Failure and recovery behavior specified
- Architecture tradeoffs linked to requirements

## Fixture (unrun)

Scenario: Retrieved documents have workspace-specific access, and the proposed prompt tells the model to hide unauthorized text.

Expected behavior: The architecture rejects prompt-only isolation and specifies pre-exposure filtering plus a negative access test.
