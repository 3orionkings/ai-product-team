---
name: aipt-shape-feature
description: "W02 Turn these documents into a feature proposal. Inputs: Authorized corpus; Problem; Answers to material questions. Returns: Source-linked requirements; Journey; Acceptance map; Unresolved decisions. Runs the AI Product Team shape-feature workflow from this session."
license: MIT
metadata:
  aipt_entry: "W02"
  aipt_version: "0.1.0"
---

# W02 · Turn these documents into a feature proposal.

Request: $ARGUMENTS

Run this workflow from the current session as the root orchestrator, following the `aipt-start` skill for routing, dispatch, gates and the case ledger. Load `aipt-start` first if it is not already loaded. The full procedure, stage by stage, is in `references/recipe.md`; read it before dispatching.

Manager: `aipt-experience-manager` · Minimum risk: R0 (raise it when the inputs or actions require it).

## Inputs

- Authorized corpus
- Problem
- Answers to material questions

If an input is missing and would change the result, ask for it before dispatching.

## Outputs

- Source-linked requirements
- Journey
- Acceptance map
- Unresolved decisions

## Work graph

| # | Stage | Role | Artifact | Runs | Gate |
|---|---|---|---|---|---|
| 1 | Reconstruct | `aipt-context-analyst` | `context-brief.md` | always |  |
| 2 | Clarify | `aipt-discovery-interviewer` | `answers.json` | always |  |
| 3 | Design the job | `aipt-journey-designer` | `journey.md` | always |  |
| 4 | Specify | `aipt-requirements-writer` | `requirements.json` | always |  |
| 5 | Define evidence | `aipt-acceptance-designer` | `acceptance-map.json` | always |  |
| 6 | Review | `aipt-experience-manager` | `experience-review.json` | always | review |

Run stages in order, except where `references/recipe.md` marks two as parallel. Skip a stage only when a current accepted artifact of its type already exists in the case, and say so in the route plan. A stage marked with a condition runs only when that condition holds in the case.

## Gates you may not skip

- Review stages: Review.
- Stages that need an independent reviewer (a fresh subagent that authored nothing it reviews): none.
- A manager's favorable review creates no authority and is not test evidence.

## Conditional specialists

`aipt-interaction-designer`, `aipt-accessibility-reviewer`, `aipt-contradiction-analyst`, `aipt-evidence-linker`. Add one only for an identified missing dependency, review criterion or risk, and say why in the route plan.

## Acceptance

- Conflicts preserved
- Requirements remain linked to source decisions
- Missing authority remains open

## Fixture (unrun)

Scenario: One document says drafts only; an older slide says send messages automatically.

Expected behavior: The source conflict remains visible. Requirements cannot silently authorize sending. The acceptance map includes no-send behavior until a human resolves the authority change.
