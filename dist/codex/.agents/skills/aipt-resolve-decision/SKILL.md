---
name: aipt-resolve-decision
description: "W11 Challenge this proposal and resolve the disagreement. Inputs: Versioned proposal; Options; Criteria; Evidence; Delegation record. Returns: Challenge responses; Admissibility and convergence rulings; Decision or escalation. Runs the AI Product Team resolve-decision workflow from this session."
license: MIT
metadata:
  aipt_entry: "W11"
  aipt_version: "0.1.0"
---

# W11 · Challenge this proposal and resolve the disagreement.

Run this workflow from the current session as the root orchestrator, following the `aipt-start` skill for routing, dispatch, gates and the case ledger. Load `aipt-start` first if it is not already loaded. The full procedure, stage by stage, is in `references/recipe.md`; read it before dispatching.

Manager: `aipt-review-manager` · Minimum risk: R1 (raise it when the inputs or actions require it).

## Inputs

- Versioned proposal
- Options
- Criteria
- Evidence
- Delegation record

If an input is missing and would change the result, ask for it before dispatching.

## Outputs

- Challenge responses
- Admissibility and convergence rulings
- Decision or escalation

## Work graph

| # | Stage | Role | Artifact | Runs | Gate |
|---|---|---|---|---|---|
| 1 | Freeze common ground | `aipt-review-manager` | `decision-packet.json` | always |  |
| 2 | Choose challenges | `aipt-adversarial-orchestrator` | `challenge-plan.json` | always |  |
| 3 | Test the premise | `aipt-assumption-challenger` | `assumption-challenge.json` | always |  |
| 4 | Develop the alternative | `aipt-alternative-advocate` | `alternative.json` | always |  |
| 5 | Respond | proposal-owner (the role that authored the frozen proposal) | `challenge-response.json` | always |  |
| 6 | Judge sufficiency | `aipt-evidence-judge` | `evidence-ruling.json` | `material_conflict` | review |
| 7 | Converge | `aipt-convergence-judge` | `judgment.json` | always | review |
| 8 | Apply authority | `aipt-decision-authority` | `decision.json` | always |  |
| 9 | Record | `aipt-decision-recorder` | `decision-brief.md` | always |  |

Run stages in order, except where `references/recipe.md` marks two as parallel. Skip a stage only when a current accepted artifact of its type already exists in the case, and say so in the route plan. A stage marked with a condition runs only when that condition holds in the case.

## Gates you may not skip

- Review stages: Judge sufficiency, Converge.
- Stages that need an independent reviewer (a fresh subagent that authored nothing it reviews): none.
- A manager's favorable review creates no authority and is not test evidence.

## Conditional specialists

`aipt-evidence-judge`, `aipt-pre-mortem-analyst`, `aipt-red-team-tester`, `aipt-dissent-recorder`, `aipt-product-director`. Add one only for an identified missing dependency, review criterion or risk, and say why in the route plan.

## Acceptance

- Maximum two challenge rounds by default
- No majority-vote truth
- Unresolved and defer are valid outcomes
- Judgment and approval are distinct

## Fixture (unrun)

Scenario: Three agents prefer option A, one points to a decisive violation of a protected constraint.

Expected behavior: The judge rules on the violation rather than votes. If the evidence remains inconclusive, it defers and identifies the next test.
