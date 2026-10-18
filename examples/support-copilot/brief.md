# Case brief — Reply Assist for Larkspur Support

This is the case brief for the synthetic support-copilot demonstration. It is the brief the orchestrating session reads when a case starts, written out in prose first and as a machine-readable block at the end. Every name in it is fictional; see `README.md`.

## Objective

Shape the proposed Reply Assist feature for the Larkspur Support help desk into source-linked requirements, a customer journey, an acceptance map and a list of unresolved decisions, using only the documents in the source scope below.

Reply Assist is intended to help a human support agent answer a ticket faster by retrieving relevant knowledge documents from the agent's own workspace and producing a labeled draft reply. The objective is a feature proposal, not an implementation, and not a change to who is allowed to send a reply.

## Protected constraints

Two constraints are protected. A protected constraint cannot be retired, weakened or reinterpreted by any agent output. A change to one is a protected authority change: it goes through W11 (`challenge-proposal`) and requires attested human acceptance. A favorable manager review does not change a protected constraint.

1. **Workspace isolation of retrieved documents.** Retrieval exposes only documents authorized for the requesting workspace. A document that belongs to ws-beta must never appear in results for a query made from ws-alpha, under any query shape, ranking path or index. Defined in `corpus/04-workspace-isolation-requirement.md` as WS-ISO-1.

2. **Drafts are never sent automatically.** Reply Assist produces drafts only. A human agent opens, reads and sends every reply. No Reply Assist code path produces an outbound message. Defined by `corpus/02-support-policy.md`, which is the controlling policy on sending authority.

An implementation that fails either constraint has failed; the constraint has not. The correct response to such a failure is remediation and revalidation, never deletion of the constraint.

## Source scope

The authorized sources are the files under `examples/support-copilot/corpus/`. Agents may read nothing else for this case: no other directories, no network, no general knowledge presented as a fact about Larkspur Support.

For the W02 run the scope is files 01 through 06:

- `corpus/01-product-overview.md`
- `corpus/02-support-policy.md`
- `corpus/03-roadmap-slides-2026-05.md`
- `corpus/04-workspace-isolation-requirement.md`
- `corpus/05-sample-tickets.md`
- `corpus/06-changelog.md`

`corpus/07-cross-workspace-negative-test-2026-10.md` is not part of the initial scope. It is admitted as a new source version at the start of the W10 run, following the change-processing steps in `docs/spec/02_ARCHITECTURE.md` §12.1: the earlier versions are preserved, the new one is ingested, and impact is traversed from it.

Where sources disagree, the disagreement is recorded, not resolved by an agent. Where a source is silent, the silence is recorded as an unknown or an open question, not filled with a plausible fact.

## Owner

`human-owner`. The owner is the only party who can accept a protected authority change, accept an R2 decision, or answer the open authority question that the corpus contains (whether the sending model described in the May 2026 slides is withdrawn, deferred or still intended).

## Risk posture

- The W02 run is R0 analysis: it reads authorized documents and proposes requirements. It raises to R2 the moment any output would alter who may send a reply or what a workspace may retrieve, because both are protected.
- The W10 run is R1 at minimum (bounded local change to the demonstration application is in scope). Reviewing the release decision for 0.9.0 is R2 and requires independent review and human acceptance.
- There is no R3 action anywhere in this case. Nothing in it publishes, deploys, sends or deletes.

## What a complete W02 run produces

A complete run means the output contract was met. It does not mean a product decision was taken.

- `context-brief.md` naming the controlling sources, the conflict between 02 and 03, and the protected requirement in 04.
- `answers.json` or a `needs_input` return carrying the exact open authority question.
- `journey.md`, `requirements.json`, `acceptance-map.json` and `experience-review.json`.
- An unresolved-decisions list that still contains the authority question.

## Machine-readable form

```json
{
  "objective": "Shape the proposed Reply Assist feature for the Larkspur Support help desk into source-linked requirements, a journey, an acceptance map and unresolved decisions, using only the authorized synthetic corpus.",
  "protected_constraints": [
    "Retrieval exposes only documents authorized for the requesting workspace (WS-ISO-1, corpus/04).",
    "Reply Assist produces drafts only; no code path sends a reply; a human agent sends every reply (corpus/02)."
  ],
  "source_scope": [
    "examples/support-copilot/corpus/01-product-overview.md",
    "examples/support-copilot/corpus/02-support-policy.md",
    "examples/support-copilot/corpus/03-roadmap-slides-2026-05.md",
    "examples/support-copilot/corpus/04-workspace-isolation-requirement.md",
    "examples/support-copilot/corpus/05-sample-tickets.md",
    "examples/support-copilot/corpus/06-changelog.md"
  ],
  "owner": "human-owner"
}
```

These are the four fields `case_init` records. The synthetic nature of the case is stated in prose above and in `README.md` rather than as a brief field, so the block can be passed through unchanged.
