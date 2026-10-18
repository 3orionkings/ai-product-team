# Adaptation notes: UX direction synthesis (S03)

Source: the author's March 2026 draft of UX Direction Synthesizer. The notes below describe what the adapted `SKILL.md` keeps, changes and leaves out.

## Preserved

- Purpose: after discovery, turn answers and source context into a coherent product direction, mental model, information architecture and flow strategy.
- Use when: discovery is complete enough to propose direction; answers must become UX principles and product shape; the work concerns a new interface, major redesign, onboarding or workflow shell.
- Do not use when: discovery is too shallow; the request is purely technical and not UX- or workflow-facing; the requester wants questions, not proposals.
- Process steps and their order: translate answers into design posture (primary user, highest-leverage job, what trust and control should feel like, appropriate visibility, reversibility and confirmation); define the mental model (metaphor or operating model, what the product is and is not); define the structural layers (surfaces, navigation, object model, primary states, approval and execution moments, activity, queue, history and settings relationships); prioritize workflows (P0, secondary, deferred, high-risk); state a short set of product principles.
- Output contract: product direction summary; mental model; information architecture or surface map; priority flows; UX principles; open tradeoffs and decisions to validate.
- Guardrails: no screen-by-screen filler unless requested; no vague "modern intuitive experience" language; no features detached from user jobs; no trust claims without interface mechanisms.
- Success criteria: the direction is internally coherent, grounded in source context, differentiated from generic assistant UX, and ready to hand off to wireframes, requirements or prototype work.

## Changed

- Required inputs are restated as typed versioned references (`claim`, `source`, `artifact`, `requirement` and `decision` version ids), each with the behavior to follow when it is missing; a fifth input, the responsibility allocation from aipt-method-ai-responsibility-allocation (S14), was added for features with model-driven steps.
- Outputs are restated as a named artifact, `ux-direction.md` recorded as a `proposal` version, plus the envelope fields `findings`, `evidence_refs`, `artifact_refs`, `proposed_links`, `uncertainties`, `requested_followups` and `scope_violations`.
- A trust-mechanism check was made an explicit numbered step (step 6) rather than only a guardrail, so each trust claim is tied to a surface, state or moment or becomes an open decision.
- Approval and execution moments now name whether each step is proposed, confirmed or executed and by whom; enforcement of that boundary is deferred to aipt-method-tool-and-permission-boundaries (S16).
- The "open tradeoffs" output now carries options, settling evidence and decider for each item, with requirement-shaped items routed to aipt-method-requirements-and-acceptance (S13).
- An Example section was added, using the fictional Reply Assist product at Larkspur Support; the source had none.
- An Evidence and uncertainty rules section was added; it defers record keeping to aipt-method-evidence-and-lineage (S12) and treats priority ranking as a proposal.
- Do-not-use bullets now route to the neighboring skills S01, S08, S14 and S28 so the method stays distinct from discovery, planning, responsibility allocation and control-level interaction design.
- Each guardrail now states the alternative behavior, as the authoring contract requires.
- Voice changed to second person imperative throughout.

## Omitted

- The pack-level introduction that described the origin of the drafts in the author's prompt archive, its suggested installation directories and its recommended usage order.
- The agent-style title framing ("Synthesizer"); the adapted skill is a method, not a persona.
