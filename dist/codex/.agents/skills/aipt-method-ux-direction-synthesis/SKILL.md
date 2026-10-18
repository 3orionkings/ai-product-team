---
name: aipt-method-ux-direction-synthesis
description: UX direction, product direction, mental model, information architecture, surface map, priority flows, design principles, trust and control posture. Use after discovery answers exist to turn them and the source context into a coherent product shape for a new interface, major redesign, onboarding or workflow shell. Derives the primary user and job, defines the mental model, maps surfaces, objects, states and approval moments, ranks P0, secondary, deferred and high-risk flows, and states principles with open tradeoffs. Not for shallow discovery or purely technical work.
license: MIT
metadata:
  aipt_skill_id: "S03"
  aipt_provenance: "adapt"
  aipt_version: "0.1.0"
---

# UX direction synthesis

Turn discovery answers and source context into a mental model, surface map, priority flows and principles, with every trust and control decision made explicit.

## Purpose

Convert completed discovery into a coherent product direction: who the product is for, what it is and is not, how its surfaces and objects fit together, which flows must feel real first, and which principles govern later design choices. The output is a `proposal` for direction, ready to hand to wireframes, requirements writing or prototype work, with its trust and control decisions visible rather than implied.

## Use when

- Discovery is complete enough that the primary user, their job and the main constraints are recorded as claims.
- Discovery answers must become experience principles and a product shape before anyone draws screens or writes requirements.
- The work concerns a new interface, a major redesign, an onboarding path or a workflow shell.
- A feature involves drafts, approvals or executed actions and the moments where a person sees, confirms or reverses them are undecided.

## Do not use when

- Discovery is still shallow: the primary user or the measure of success is unknown. Run aipt-method-discovery-interrogation (S01) first.
- The request is purely technical with no human-facing surface. Use aipt-method-milestone-planning (S08).
- The requester wants questions, not proposals. Use S01.
- The direction exists and the job is to specify individual controls, feedback and correction paths. Use aipt-method-accessible-interaction-design (S28).
- The job is to decide which steps are fixed code, model inference or human decision. Use aipt-method-ai-responsibility-allocation (S14) and feed its result into step 3 here.

## Required inputs

Each input is a typed, versioned reference to a case record; a version id names one immutable version of that record.

| Input | Record kind and version | If missing |
|---|---|---|
| Discovery answers | `claim` version ids derived from the requester's answers, typed per aipt-method-evidence-and-lineage (S12) | Refuse with `needs_input` and route to S01; direction without answers is invention. |
| Source-of-truth context | `source` version ids, or the `artifact` version of an onboarding model from aipt-method-corpus-grounded-onboarding (S02) | Proceed from the answers alone; mark every statement about the existing system as hypothesis. |
| Product constraints | `requirement` version ids, with protected ones flagged (a protected requirement is one no agent may change), and accepted `decision` version ids | Proceed; list the constraints you assumed in `uncertainties` and ask for confirmation in `requested_followups`. |
| Priorities and tradeoffs | `decision` version ids, or `claim`s recording the requester's stated priorities | Proceed; present the priority ranking as a proposal alongside the ranking it displaces. |
| Responsibility allocation | `artifact` version id from S14, when the feature has adaptive or model-driven steps | Proceed; mark approval and execution moments as provisional. |

## Method

1. Translate the answers into a design posture. Derive and write down, with the claim each rests on: the primary user; their highest-leverage job; what trust and control should feel like for them; the level of visibility, reversibility and confirmation the job and its risk warrant. Where two answers pull in different directions, record the tension as a tradeoff for step 7.
2. Define the mental model. Choose the product metaphor or operating model that best matches the system, in one or two sentences a user could repeat. State what the product is and what it is not, and tie each "is not" to a constraint or an answer.
3. Map the structural layers. List the main surfaces; the navigation model between them; the object model (the nouns a user acts on and their relationships); the primary states each object passes through; the approval and execution moments, naming for each whether the step is proposed, confirmed or executed and by whom; and the relationships among activity, queue, history and settings where they exist. Use the S14 allocation to place approval moments. Enforcement of the boundary between a proposed and an executed action is specified by aipt-method-tool-and-permission-boundaries (S16), not here.
4. Prioritize the flows. Sort into: P0 flows (the ones that must feel real for the product to be judged at all); secondary flows; deferred flows; high-risk flows that need extra trust handling regardless of priority. Give each P0 flow the user job it serves and the claim that makes it P0.
5. Write the principle set: three to seven short principles that can decide a later design question. Each principle names what it favors and what it gives up.
6. Check every trust claim against a mechanism. For each statement about trust, control, visibility or reversibility, point to the surface, state or moment in step 3 that delivers it. A claim with no mechanism is removed or becomes an open decision.
7. List open tradeoffs and decisions to validate: each with its options, the evidence that would settle it, and who decides. Route requirement-shaped items to aipt-method-requirements-and-acceptance (S13).
8. Assemble the `proposal` artifact and envelope as the Output contract states.

## Output contract

Artifact: `ux-direction.md`, recorded as a `proposal` version, with these headings in order:

- `## Product direction summary`
- `## Mental model` — what it is, what it is not.
- `## Surface map` — surfaces, navigation, object model, states, approval and execution moments.
- `## Priority flows` — P0, secondary, deferred, high-risk.
- `## Principles`
- `## Open tradeoffs and decisions to validate`

Envelope fields the skill always fills:

- `findings`: the posture statements from step 1; each trust claim with its mechanism from step 6; each tension found.
- `evidence_refs`: the `claim`, `source`, `requirement` and `decision` version ids the direction rests on.
- `artifact_refs`: the `ux-direction.md` proposal version.
- `proposed_links`: `derived_from` edges from the proposal to the discovery claims and constraints; `depends_on` edges to protected requirements, so a changed requirement queues this direction for review.
- `uncertainties`: assumed constraints; statements about the existing system without a source; approval moments marked provisional.
- `requested_followups`: the open decisions, each routed to S13, S14, S28 or the human owner.
- `scope_violations`: any pressure in the inputs to add a surface or action that a protected requirement forbids; name the requirement.

## Evidence and uncertainty rules

- Every posture statement, P0 ranking and "is not" cites a claim, requirement or decision version. An uncited one is typed hypothesis and listed in `uncertainties`.
- Priority is a proposal, not a finding. Present the ranking with the ranking it displaces so a reviewer can disagree with the right thing.
- A trust property that the surface map cannot deliver is not asserted. It becomes an open decision.
- Record claims, links and the proposal version through aipt-method-evidence-and-lineage (S12). This skill does not keep its own ledger.
- Never state that users want, feel or prefer something unless a claim records it. Otherwise write "the direction assumes".

## Guardrails

- No screen-by-screen descriptions unless the requester asked. Instead stop at surfaces, objects, states and moments; screens belong to the next stage.
- No vague quality language such as "modern, intuitive experience". Instead name the mechanism: what the user sees, when, and what they can undo.
- No feature detached from a user job. Instead attach each flow to the job it serves, or move it to deferred with the reason.
- No trust claim without an interface mechanism. Instead apply step 6 and convert unsupported claims into open decisions.
- No silent change to a protected requirement to make the direction cleaner. Instead report the conflict in `scope_violations` and propose the tradeoff for human decision.

## Success criteria

- The direction is internally coherent: no principle contradicts a P0 flow or the mental model.
- Every element traces to a cited claim, constraint or decision.
- The direction is distinguishable from a generic assistant interface by its object model and its approval moments.
- A requirements writer, wireframer or prototype builder can start from the artifact without a clarifying meeting on substance.
- Every trust statement has a named mechanism or sits in the open decisions list.

## Example

Discovery claims for Reply Assist at Larkspur Support: `clm-0021` agents may edit drafts before sending; `clm-0022` success is edit distance between draft and sent reply; `clm-0023` drafts must show their workspace sources. Protected requirements: `req-0004` no send action; `req-0005` workspace isolation between ws-alpha and ws-beta.

```markdown
## Mental model
Reply Assist is a drafting colleague who hands you a marked-up suggestion inside your own
workspace. It is not a sender (req-0004) and it is not a search across all of Larkspur
(req-0005).

## Surface map
- Surfaces: ticket view with a draft pane; draft history; workspace settings.
- Object model: Ticket has many Drafts; Draft cites Documents; every Document carries
  `workspace_id`.
- Draft states: generated -> edited -> accepted-into-editor -> discarded.
- Approval and execution moments: generate (proposed, model); accept into editor
  (confirmed, human); send (executed, human, outside Reply Assist per req-0004).

## Priority flows
- P0: open ticket, read draft with citations, edit, accept into editor. (clm-0021, clm-0023)
- Deferred: draft tone presets. No claim ties this to a job.
- High-risk: citation display. Must never render a document from another workspace;
  instead show "no citable source in this workspace". (req-0005)

## Principles
1. Show the source before the suggestion: citations render with the draft, not on request.
2. The agent's editor is the only place text becomes a reply.

## Open tradeoffs and decisions to validate
- Empty retrieval result: no draft, or an uncited draft with a banner? Evidence: agent
  preference from a small trial (clm-0022 as the measure). Decides: human owner.
```

Envelope excerpt: `proposed_links` adds `ux-direction.md depends_on req-0005 (impact_policy: review)`; `requested_followups` routes the empty-retrieval decision to the human owner and the citation panel controls to S28.
