---
name: aipt-review-release
description: "W09 Is this feature ready for the proposed release? Inputs: Frozen build; Acceptance map; Real results; Proposed rollout scope. Returns: Pass/fail/blocked release review; Unresolved risks; Human approval request. Runs the AI Product Team review-release workflow from this session."
license: See LICENSE_PENDING.md in the ai-product-team repository.
metadata:
  aipt_entry: "W09"
  aipt_version: "0.1.0"
---

# W09 · Is this feature ready for the proposed release?

Request: $ARGUMENTS

Run this workflow from the current session as the root orchestrator, following the `aipt-start` skill for routing, dispatch, gates and the case ledger. Load `aipt-start` first if it is not already loaded. The full procedure, stage by stage, is in `references/recipe.md`; read it before dispatching.

Manager: `aipt-audit-manager` · Minimum risk: R2 (raise it when the inputs or actions require it).

## Inputs

- Frozen build
- Acceptance map
- Real results
- Proposed rollout scope

If an input is missing and would change the result, ask for it before dispatching.

## Outputs

- Pass/fail/blocked release review
- Unresolved risks
- Human approval request

## Work graph

| # | Stage | Role | Artifact | Runs | Gate |
|---|---|---|---|---|---|
| 1 | Freeze release scope | `aipt-audit-manager` | `release-scope.json` | always |  |
| 2 | Reproduce requirements | `aipt-independent-auditor` | `release-audit.json` | always | review, independent |
| 3 | Review boundaries | `aipt-security-reviewer` | `security-review.json` | always | review |
| 4 | Plan bounded release | `aipt-rollout-planner` | `rollout-plan.md` | always |  |
| 5 | Decide readiness | `aipt-audit-manager` | `release-readiness.md` | always | review |

Run stages in order, except where `references/recipe.md` marks two as parallel. Skip a stage only when a current accepted artifact of its type already exists in the case, and say so in the route plan. A stage marked with a condition runs only when that condition holds in the case.

## Gates you may not skip

- Review stages: Reproduce requirements, Review boundaries, Decide readiness.
- Stages that need an independent reviewer (a fresh subagent that authored nothing it reviews): Reproduce requirements.
- A manager's favorable review creates no authority and is not test evidence.

## Conditional specialists

`aipt-privacy-reviewer`, `aipt-accessibility-reviewer`, `aipt-operations-manager`, `aipt-red-team-tester`, `aipt-evidence-judge`. Add one only for an identified missing dependency, review criterion or risk, and say why in the route plan.

## Acceptance

- Never deploy or publish
- Current-version acceptance evidence
- Blocking findings cannot be waived by voting

## Fixture (unrun)

Scenario: All happy-path tests pass but there is no exercised rollback and isolation remains untested.

Expected behavior: Readiness is blocked or conditional for human review. The workflow neither deploys nor converts missing evidence into a pass.
