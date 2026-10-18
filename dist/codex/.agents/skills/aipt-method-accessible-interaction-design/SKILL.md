---
name: aipt-method-accessible-interaction-design
description: Accessible interaction design, draft versus preview versus confirmation versus executed action, keyboard operation, non-color status, perceivable feedback, correction path, undo, handoff back to people, observed check versus untested claim. Use when specifying or reviewing how people see, operate and correct an AI feature, including the task before and after the AI exchange. Produces an interaction specification with a control inventory, four-state actions, feedback and correction paths, handoffs, and reproducible checks each labeled observed or untested.
license: MIT
metadata:
  aipt_skill_id: "S28"
  aipt_provenance: "newly_authored"
  aipt_version: "0.1.0"
---

# Accessible interaction design

Specify the controls, feedback and correction paths through which people see, operate and correct an AI feature, so that every action is distinct in its draft, preview, confirmation and executed states and every claim about operability is marked observed or untested.

## Purpose

An interaction specification says what a person can perceive at each moment, what they can do, what happens when they do it, and how they get back when it was wrong. It covers the whole task, not only the exchange with the model: the state the person arrives in, the handoff to the AI, the handoff back, and the exits that do not pass through the AI at all.

Three terms carry the skill. An action has four **states**: `draft` (output exists, is editable, and has had no effect anywhere), `preview` (the exact effect is shown and still none has happened), `confirmation` (the person consents to one exact version) and `executed` (the effect happened and a receipt exists). A **correction path** is a way to change course from any state: edit, reject, undo, escalate to a person. An **observed check** is a reproducible procedure someone ran on a named build with a named setup and recorded; anything else, including a screenshot, is an **untested claim**.

Four public accessibility principles frame the work, in plain words. Perceivable: status and content reach the person through more than one sense and are available to assistive technology. Operable: every control works from the keyboard and without timing or motion the person cannot adjust. Understandable: labels say what will happen, in the person's terms. Robust: state is exposed programmatically, not only drawn. The confirmation state binds to the action record that `aipt-method-tool-and-permission-boundaries` (S16) defines, so what the person confirms is what executes.

## Use when

- A surface shows AI output a person can act on, and at least one control could lead to an effect outside that surface.
- Status, uncertainty, staleness or failure must be communicated to a person.
- A journey includes a handoff from a person to the AI and back, or an exit that bypasses the AI.
- A review needs reproducible accessibility checks rather than a rendered screenshot.
- A `requirement` names supported input modes, assistive technology or operability.

## Do not use when

- You need tool contracts, idempotency or the split between proposed and executed actions: use S16; this skill designs what the person sees around that split.
- You need to decide who may confirm an effect: use `aipt-method-delegated-authority` (S25).
- You need to decide whether a step belongs to code, inference or a person: use `aipt-method-ai-responsibility-allocation` (S14).
- You need the mental model, surface map and priority flows: use `aipt-method-ux-direction-synthesis` (S03); this skill specifies the controls on the surfaces S03 names.
- You need the fresh-context mechanics of an audit: use `aipt-method-independent-audit` (S10) and apply this skill for the checks inside it.
- You need acceptance checks written as requirements: use `aipt-method-requirements-and-acceptance` (S13); this skill supplies their content.

## Required inputs

- **Journey** — `artifact` or `proposal` version naming actors, entry state, context, exits and handoffs. If missing, write a minimal task map from the request, label it a hypothesis, and return `partial`.
- **Action inventory** — the S16 `artifact` version listing actions, effect classes and model access. If missing, treat every control that could leave the surface as an external effect until the inventory shows otherwise.
- **User authority** — `requirement` or `approval` version stating who may confirm each effect. If missing, design the confirmation, write `who: unassigned`, and add a followup.
- **System state signals** — `artifact` or `requirement` version listing what the system knows about its own uncertainty, source coverage, freshness and timeouts. If missing, design feedback for the standard states and mark each signal's availability a hypothesis.
- **Supported input modes and assistive setups** — `requirement` version or compatibility record, by reference. If missing, specify for keyboard, screen reader and non-color display at minimum and mark other setups unspecified.
- **Prototype or build** — `artifact` version when reviewing. If missing, every check is `untested`.

## Method

1. **Map the whole task.** Before: how the person arrives and with what data, assumed partial. During: the AI exchange. After: what the person does with the output outside the AI, such as sending, filing or escalating. Exits: complete, abandon, escalate to a person, discard. Name each handoff and what crosses it.
2. **Inventory the controls.** Per control: id, visible label, the state it moves an action to, effect class (`none` | `local` | `external`), keyboard operation, who may use it, and its place in focus order. A control that belongs to the surrounding system, such as the send control in a support tool, is listed as outside this surface so that nothing in the surface duplicates it.
3. **Give every action its four states and keep them apart.** Each state has distinct status text, a distinct shape or position, and a programmatic state. Every transition is an explicit action by the person; no timer, scroll or model output moves an action forward. Draft and preview have no effect, and a control in those states cannot be wired to an executor.
4. **Bind confirmation to the exact version.** The confirmation shows the content and target that will execute (the S16 action record and its hash) and names the version. An edit after preview returns the action to draft and discards the pending confirmation. The executed state shows the receipt reference.
5. **Design feedback per system state.** Working, waiting on the person, uncertain (sources missing or confidence low), stale, failed, and unknown outcome (an S16 timeout). Each has text, a non-color visual, a programmatic announcement, and the actions available next. Uncertainty and sources appear in the main flow beside the output.
6. **Design correction paths.** From each state: edit, reject, undo where reversible, report wrong, escalate to a person. For every external effect, state whether undo exists; where it does not, the confirmation is the last stop and says so in its text.
7. **Specify keyboard and non-color operation.** Focus order, visible focus, keyboard activation of every control, dialogs that trap and then return focus, a cancel key, status never carried by color alone, text alternatives for icons, adjustable time limits, optional motion.
8. **Specify the handoff back to people.** The state in which a person takes over, what they receive (output version, sources, record version), what the AI does after handoff (nothing on that record until reassigned), and how a person who was not in the exchange gets its context.
9. **Write checks as reproducible procedures.** Setup (build version, assistive technology or display mode), steps, expected observation. Status `observed` with a receipt, or `untested`. A screenshot supports a layout claim only; operability and announcement need an observed run.
10. **Assemble the specification and the envelope.** Emit `interaction-spec.json`, link each action's states to its S16 action record, and fill the envelope fields below.

## Output contract

Artifact: `interaction-spec.json`, kind `artifact`, with keys:

- `task_map`: `before`, `ai_interaction`, `after`, `exits[]`
- `controls[]`: `control_id`, `label`, `moves_to`, `effect_class`, `keyboard`, `who`, `focus_order`
- `actions[]`: `action_id`, `action_record_ref`, `states` with `draft`, `preview`, `confirmation`, `executed`, each holding `status_text`, `shape`, `programmatic_state`, `transition_in`, `effect` (`none` | `local` | `external`), `receipt_ref`
- `feedback[]`: `state`, `text`, `visual`, `announcement`, `next_actions[]`, `color_only: false`
- `corrections[]`: `from_state`, `action`, `returns_to`, `reversible`
- `handoffs[]`: `to`, `carries[]`, `ai_after_handoff`
- `checks[]`: `check_id`, `setup`, `steps`, `expected`, `status` (`observed` | `untested`), `receipt_ref`

Envelope fields this skill always fills:

- `findings`: any control in draft or preview wired to an effect; any state distinguished by color alone; any control without keyboard operation; any external effect without an undo statement; any check claimed from a screenshot.
- `evidence_refs`: the journey, action inventory, authority, signal and build versions read.
- `artifact_refs`: the specification version.
- `proposed_links`: each action `depends_on` its S16 action record version, `impact_policy: review`; each observed check `verifies` the control it covers.
- `observed_checks`: only runs with receipts; otherwise empty.
- `uncertainties`: hypothesized task map, unavailable signals, assistive setups not covered.
- `requested_followups`: the untested checks to run, the `who` for any unassigned confirmation, the setups not covered.
- `scope_violations`: any request to wire a draft control to execution, to certify from a screenshot, or to place inside the surface a control that belongs to the surrounding system.

## Evidence and uncertainty rules

- An observed check names the build version, the setup and who ran it, in the receipt shape of `aipt-method-evaluation-execution-and-receipts` (S19).
- A screenshot shows layout at one moment. It says nothing about focus order, announcement or what a control does; a claim resting on it is `untested`.
- "The framework handles accessibility" is a hypothesis until a check on this build observes the behavior.
- A happy-path check does not cover failure or recovery; each correction path has its own check.
- Follow `aipt-method-evidence-and-lineage` (S12) for citing versions and typing claims; this skill adds only the rules above.

## Guardrails

- Do not let a draft or preview control execute an external action. Instead, wire effects only from the confirmation state, bound to the action record hash.
- Do not mark a state by color alone. Instead, pair color with text and shape, and expose the state programmatically.
- Do not advance an action on a timer, a scroll or a model output. Instead, require an explicit action by the person for every transition.
- Do not certify operability from a screenshot or a rendering. Instead, run the check on the build with the stated setup and record it, or mark it `untested`.
- Do not design for a person who starts with a clean prompt and complete data. Instead, specify the entry state with partial data and the path for supplying what is missing.
- Do not end the specification at the model's reply. Instead, specify what the person does next, the handoff and the exits outside the AI.
- Do not hide uncertainty or sources behind hover or a secondary view. Instead, show them in the main flow beside the output.
- Do not duplicate a control that belongs to the surrounding system. Instead, list it as outside this surface and design the handoff to it.
- Do not treat a passing happy-path check as covering correction. Instead, write one check per correction path.

## Success criteria

- The task map names the before, during, after and exits, and every handoff with what it carries.
- Every control has a label, a target state, an effect class, a keyboard operation and a place in focus order.
- Every action has four states with distinct text, shape and programmatic state, and only the confirmation state leads to an effect.
- Every system state has feedback with text, a non-color visual and an announcement, and `color_only` is false throughout.
- Every external effect states whether undo exists.
- Every check has a setup, steps, an expected observation and a status, and no `observed` check lacks a receipt.

## Example

Reply Assist at Larkspur Support shows a draft panel beside the agent's reply editor; sending belongs to the support system. Specification excerpt:

```json
{
  "task_map": {"before": "agent opens ticket t-7731 in the support system with partial customer context",
               "ai_interaction": "agent requests a draft, reads it with its sources, edits or rejects it",
               "after": "agent sends from the support system; the AI has no part in sending",
               "exits": ["insert draft", "discard draft", "escalate to a senior agent", "abandon"]},
  "controls": [
    {"control_id": "K1", "label": "Draft a reply", "moves_to": "draft", "effect_class": "none", "keyboard": "button; Enter or Space", "who": "any agent in the ticket's workspace", "focus_order": 1},
    {"control_id": "K2", "label": "Preview in reply editor", "moves_to": "preview", "effect_class": "none", "keyboard": "button; Enter or Space", "who": "same", "focus_order": 2},
    {"control_id": "K3", "label": "Insert into reply editor", "moves_to": "confirmation", "effect_class": "local", "keyboard": "button; dialog traps focus; Escape cancels", "who": "same", "focus_order": 3},
    {"control_id": "K4", "label": "Send", "moves_to": null, "effect_class": "external", "keyboard": "not in this surface", "who": "support system control, outside this surface", "focus_order": null}],
  "actions": [
    {"action_id": "insert-draft", "action_record_ref": "act-0419", "states": {
       "draft": {"status_text": "Draft. Not inserted, not sent.", "shape": "dashed border", "programmatic_state": "draft", "transition_in": "K1", "effect": "none"},
       "preview": {"status_text": "Preview: this text would be placed in your reply editor.", "shape": "eye icon, editor region outlined", "programmatic_state": "preview", "transition_in": "K2", "effect": "none"},
       "confirmation": {"status_text": "Insert draft d-0419@v2 into the reply editor? Nothing is sent.", "shape": "modal with Insert and Cancel", "programmatic_state": "confirmation", "transition_in": "K3", "effect": "none"},
       "executed": {"status_text": "Inserted. Not sent. Sending stays in the support system.", "shape": "check icon", "programmatic_state": "executed", "transition_in": "Insert in dialog", "effect": "local", "receipt_ref": "rcpt-2210"}}}],
  "feedback": [
    {"state": "uncertain", "text": "Draft cites 1 article; 2 statements have no source.", "visual": "warning triangle beside each unsourced statement", "announcement": "polite live region", "next_actions": ["edit", "reject"], "color_only": false},
    {"state": "unknown_outcome", "text": "Insert did not confirm. Check the editor before acting.", "visual": "stopped spinner icon", "announcement": "assertive live region", "next_actions": ["retry insert", "discard"], "color_only": false}],
  "corrections": [{"from_state": "preview", "action": "Edit", "returns_to": "draft", "reversible": true},
                  {"from_state": "executed", "action": "Remove inserted text", "returns_to": "draft", "reversible": true}],
  "handoffs": [{"to": "senior agent", "carries": ["draft version d-0419@v2", "source list", "ticket version t7731@v5"], "ai_after_handoff": "no further drafts on this ticket until reassigned"}],
  "checks": [
    {"check_id": "A1", "setup": "build reply-assist-ui@7c2e, keyboard only", "steps": "Tab from the ticket header through K1 to K3; activate K3 with Enter; press Escape", "expected": "focus order K1, K2, K3; dialog opens; Escape closes it and returns focus to K3", "status": "observed", "receipt_ref": "rcpt-2318"},
    {"check_id": "A2", "setup": "build reply-assist-ui@7c2e, screen reader on", "steps": "Reach the executed state", "expected": "announces 'Inserted. Not sent.'", "status": "untested", "receipt_ref": null},
    {"check_id": "A3", "setup": "build reply-assist-ui@7c2e, grayscale display", "steps": "View draft, preview and executed states", "expected": "states distinguishable by text and shape", "status": "untested", "receipt_ref": null}]
}
```

Envelope excerpt: `findings` records that an earlier prototype wired K2 to the editor directly, so preview had a local effect; `requested_followups` asks for runs of A2 and A3 on the same build.
