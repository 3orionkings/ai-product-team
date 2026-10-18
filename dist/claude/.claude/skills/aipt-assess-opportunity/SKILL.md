---
name: aipt-assess-opportunity
description: "W01 Should we add AI to this workflow? Inputs: Problem; Current workflow; Users; Constraints; Existing alternatives. Returns: Opportunity brief; Option comparison; Decision or next-test recommendation. Runs the AI Product Team assess-opportunity workflow from this session."
license: MIT
metadata:
  aipt_entry: "W01"
  aipt_version: "0.1.0"
---

# W01 · Should we add AI to this workflow?

Request: $ARGUMENTS

Run this workflow from the current session as the root orchestrator, following the `aipt-start` skill for routing, dispatch, gates and the case ledger. Load `aipt-start` first if it is not already loaded. The full procedure, stage by stage, is in `references/recipe.md`; read it before dispatching.

Manager: `aipt-discovery-manager` · Minimum risk: R0 (raise it when the inputs or actions require it).

## Inputs

- Problem
- Current workflow
- Users
- Constraints
- Existing alternatives

If an input is missing and would change the result, ask for it before dispatching.

## Outputs

- Opportunity brief
- Option comparison
- Decision or next-test recommendation

## Work graph

| # | Stage | Role | Artifact | Runs | Gate |
|---|---|---|---|---|---|
| 1 | Frame | `aipt-context-analyst` | `context-brief.md` | always |  |
| 2 | Resolve material unknowns | `aipt-discovery-interviewer` | `questions-and-decisions.md` | always |  |
| 3 | Compare | `aipt-opportunity-analyst` | `opportunity-comparison.md` | always |  |
| 4 | Review | `aipt-discovery-manager` | `problem-review.json` | always | review |
| 5 | Decide or test | `aipt-decision-authority` | `recommendation.md` | `consequential_or_disputed` |  |

Run stages in order, except where `references/recipe.md` marks two as parallel. Skip a stage only when a current accepted artifact of its type already exists in the case, and say so in the route plan. A stage marked with a condition runs only when that condition holds in the case.

## Gates you may not skip

- Review stages: Review.
- Stages that need an independent reviewer (a fresh subagent that authored nothing it reviews): none.
- A manager's favorable review creates no authority and is not test evidence.

## Conditional specialists

`aipt-customer-researcher`, `aipt-source-researcher`, `aipt-prioritization-analyst`, `aipt-alternative-advocate`, `aipt-product-director`. Add one only for an identified missing dependency, review criterion or risk, and say why in the route plan.

## Acceptance

- No invented demand or outcomes
- A viable non-AI option receives a fair comparison
- Consequential recommendation records uncertainty and authority

## Fixture (unrun)

Scenario: A team asks for an AI assistant to approve every support credit automatically, but supplies only one complaint.

Expected behavior: The result must not infer demand or automatic financial authority. It should compare draft assistance and ordinary rules, identify necessary evidence and preserve the approval question.
