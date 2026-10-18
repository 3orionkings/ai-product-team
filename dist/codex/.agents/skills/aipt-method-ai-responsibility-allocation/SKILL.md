---
name: aipt-method-ai-responsibility-allocation
description: Responsibility allocation, step ownership, fixed code versus model inference versus adaptive investigation versus human decision, loop budget, termination rule, permission check placement. Use when designing or reviewing a feature or workflow step by step to decide which mechanism is responsible for each step, to justify any adaptive behavior with a named unknown, to keep deterministic permission checks in code, and to bound every loop with a budget and a termination rule. Produces an allocation table as a proposal artifact.
license: MIT
metadata:
  aipt_skill_id: "S14"
  aipt_provenance: "newly_authored"
  aipt_version: "0.1.0"
---

# AI responsibility allocation

Decide, for every step of a feature or workflow, which of four mechanisms is responsible for it, and write the result as a table other roles can test against.

## Purpose

An AI feature is a sequence of steps, and each step is owned by exactly one mechanism:

- **Fixed code**: a rule you can write down; same input, same output; tested with deterministic checks.
- **Model inference**: one bounded call that reads supplied context and returns a judgment or a draft; its output is not reproducible and needs a check before it has any effect.
- **Adaptive investigation**: a loop in which the model chooses the next read or tool call from earlier results; the least predictable and most expensive mechanism, allowed only for a named unknown and only inside a budget with a termination rule.
- **Human decision**: a person chooses; the system presents options and records the choice; it never substitutes for the person.

The allocation exists to prevent two opposite failures. The first moves a check that code can perform (an authorization rule, a format rule, a threshold) into a model judgment, which turns an enforceable control into a request. The second gives a loop to a step that a single call or a fixed rule would serve, which spends budget and widens the surface for error. The output is a `proposal` record: an allocation table with one row per step, a reason per row, and a budget and termination rule for every loop.

## Use when

- A `proposal` introduces or changes a step where a model reads, judges, drafts or chooses an action.
- A `review` or `challenge` asks whether a permission check lives in code or in a prompt.
- A loop exists in the design without a stated maximum number of iterations or a termination rule.
- An outcome analysis shows cost or latency concentrated in investigation steps and the allocation is being revisited.
- Requirements are being written and each acceptance check needs a mechanism that can satisfy it.

## Do not use when

- You need the input, result and error shape of a specific tool: use `aipt-method-tool-and-permission-boundaries` (S16).
- You need to decide who may approve or execute an effect: use `aipt-method-delegated-authority` (S25).
- You need to specify which sources a step may read and how scope is enforced: use `aipt-method-retrieval-and-context-contracts` (S15).
- You need observed cost or latency numbers for a budget: use `aipt-method-cost-and-latency-analysis` (S20); this skill records the budget, not the measurement.
- You need to design how a person sees and acts on a decision: use `aipt-method-accessible-interaction-design` (S28).

## Required inputs

- **Step list** — `proposal` or `artifact` version id describing the ordered steps of the feature. If missing, derive the steps from the requirement set, label every derived step a hypothesis, and name the derivation in `uncertainties`.
- **Requirements** — `requirement` version ids, with the protected flag visible. A protected requirement is one no agent may remove or weaken; only a human decision changes it. If missing, return `needs_input`: permission steps cannot be allocated without knowing which rules are protected.
- **Permission model** — `source` or `requirement` version stating which principals may see or do what. If missing, allocate every non-permission step and return `needs_input` for the rows that touch permissions; never fill the gap by inference.
- **Tool inventory** — `artifact` version listing callable tools with their effect class (read, write, send, external). If missing, proceed and mark the tool column of adaptive rows `unknown`.
- **Budget policy** — `decision` version or policy reference giving loop ceilings and wall-clock limits. If missing, propose ceilings, label them hypotheses, and add a `requested_followups` item for the policy owner.
- **Prior allocation** — the previous `proposal` version if this is a revision. If missing, state that the table is a first allocation.

## Method

1. **Enumerate steps.** One row per step with: step id, trigger, inputs, output, and effect class (`none`, `read`, `write`, `send`, `external`). Where a single step both forms a judgment and causes an effect, split it into two rows: the judgment row and the effect row.
2. **Classify the nature of each step** with four questions, asked in order. Is the correct output fully determined by the inputs under a rule you can write in the row? Then the candidate is fixed code. Does the step need to read natural language or produce text? Then the candidate is model inference. Does the next action depend on what an earlier result revealed? Then the candidate is adaptive investigation. Does the step commit the organization, spend, send, delete or accept risk on a person's behalf? Then the step is a human decision, or an effect that a recorded delegation (S25) covers.
3. **Apply the permission rule.** Any check of the form "is this actor permitted to see or do this" is fixed code, without exception. If the current design asks the model to make that check, record a finding naming the step, the current mechanism and the rule, and move the check into code. Reference S15 for retrieval scope and S16 for tool boundaries; do not restate them in the table.
4. **Apply the minimum-mechanism rule.** Choose the lowest mechanism in the order fixed code, model inference, adaptive investigation that meets the requirement, and write in the row why the lower mechanism fails. An adaptive row must name the unknown: the specific piece of information that cannot be known before the first result arrives. "The model will work it out" is not a reason; replace it with the unknown or demote the step.
5. **Bound every adaptive row.** Write the budget (maximum iterations, maximum tool calls, wall-clock ceiling, maximum distinct sources) and the termination conditions: a success predicate, budget exhausted, and a no-progress rule such as two consecutive iterations that add no new identifiers. For each exit, write what the step returns and whether the result is labeled `partial`.
6. **Attach a check to every inference row.** Name what validates the output before any effect uses it: a code check (schema, policy, scope markers), a human review, or a second independent check. An inference row whose output feeds an effect row with no check between them is a finding.
7. **Specify every human decision row.** Write what is presented (the proposal version), the actions available to the person (accept, edit, reject, defer), who may act, and the behavior on no response. The default on no response is no effect and an escalation, never silent proceed. Reference S25 for delegation and S28 for the interaction.
8. **Record alternatives for adaptive rows.** For each adaptive row, write the fixed-code and single-inference alternatives considered and the specific case each fails. This is what a reviewer tests.
9. **Map each row to acceptance checks** using `aipt-method-requirements-and-acceptance` (S13): a deterministic test for fixed-code rows; a labeled evaluation slice for inference rows (planned under S17); a budget test (the loop halts at the ceiling) and a termination test for adaptive rows; a test that no effect occurs without a recorded approval for human decision rows.
10. **Assemble the proposal and the envelope.** Emit the table as a `proposal` artifact with `depends_on` links to the requirement and permission-model versions, then fill the envelope fields in the output contract.

## Output contract

Artifact: `allocation-table.json` (or the same rows as a Markdown table), kind `proposal`. One row per step with keys:

`step_id`, `step`, `effect_class`, `mechanism` (`fixed_code` | `model_inference` | `adaptive_investigation` | `human_decision`), `reason`, `named_unknown` (adaptive only), `check_after`, `budget` (adaptive only: `max_iterations`, `max_tool_calls`, `wall_clock_ceiling`, `max_sources`), `termination` (adaptive only: `success_predicate`, `no_progress_rule`, `on_exhaustion`), `requirement_refs`, `acceptance_check_refs`, `alternatives_rejected`.

Envelope fields this skill always fills:

- `findings`: one per misallocation, each with step id, current mechanism, required mechanism and the rule violated (permission rule, minimum-mechanism rule, unchecked inference, unbounded loop, silent default).
- `evidence_refs`: the requirement, permission-model and tool-inventory versions read.
- `artifact_refs`: the allocation table version.
- `proposed_links`: each row `depends_on` the requirement version it serves, `impact_policy: review`; the table `depends_on` the permission model, `impact_policy: invalidate_applicability`.
- `uncertainties`: every hypothesis row, every proposed ceiling without a policy source, every unknown tool column.
- `requested_followups`: missing permission model, missing budget policy, measurement requests for S20.
- `scope_violations`: any request to implement a step or to change a protected requirement; allocation proposes and never implements.

## Evidence and uncertainty rules

- A mechanism choice is a proposal until a `decision` record accepts it. Write the table in the voice of a proposal, not of a settled design.
- "This step is deterministic" is a claim that needs the rule written in the row. If you cannot write the rule, the step is not fixed code; label the row inference or adaptive and say why.
- A budget number without observed data is a hypothesis. Label it, and point the measurement request to S20; replace it with an observed distribution when one exists.
- Read the permission model from the cited `requirement` or `source` version. A permission inferred from a user interface, a code comment or a folder name is a hypothesis and is marked as such.
- A budget bounds a loop; it does not prove termination. Termination is established by a check that ran against the current version and has a receipt, meaning the recorded command, exit status and target versions (S19). Until then the termination column is `planned`.
- Follow `aipt-method-evidence-and-lineage` (S12) for citing versions and typing claims; this skill adds only the rules above.

## Guardrails

- Do not place an authorization or permission check in a prompt or a model judgment. Instead, allocate it to fixed code and keep any prompt text about it as guidance labeled "requested, not enforced".
- Do not allocate adaptive investigation on the ground that the model is capable. Instead, write the named unknown; if none exists, demote the step to a single inference or a fixed rule.
- Do not give a loop a budget of "until done" or "until confident". Instead, write numeric ceilings and a no-progress rule, and label them hypotheses if no policy sets them.
- Do not let one row carry both a judgment and an effect. Instead, split the row so the effect has its own mechanism and check.
- Do not let an inference output reach an effect without a check between them. Instead, insert a code check, a human review or an independent second check, and name it in `check_after`.
- Do not set a human decision's no-response behavior to proceed. Instead, set it to no effect plus escalation to the named owner.
- Do not write cost or latency figures into the table from memory. Instead, cite an observed distribution from S20 or write `unknown`.
- Do not implement any step while allocating. Instead, hand the accepted table to `aipt-method-milestone-planning` (S08) for work orders.

## Success criteria

- Every step has exactly one mechanism and a reason a reviewer can test.
- No row allocates a permission check to model inference or adaptive investigation.
- Every adaptive row has a named unknown, a numeric budget, a termination rule with a no-progress clause, and rejected alternatives.
- Every inference row names the check that follows it.
- Every effect row traces to a human decision row or to a recorded delegation reference.
- Every row maps to at least one acceptance check, and the check type matches the mechanism.
- The envelope lists every hypothesis row in `uncertainties` and every missing input in `requested_followups`.

## Example

Reply Assist at Larkspur Support drafts support replies for agents and never sends them. Retrieval must stay inside the agent's workspace (`ws-alpha` or `ws-beta`). Allocation table, abbreviated:

| step_id | step | mechanism | reason | check_after | budget / termination |
|---|---|---|---|---|---|
| R1 | fetch ticket by id | fixed_code | lookup is a rule | schema check | n/a |
| R2 | confirm agent may view the ticket's workspace | fixed_code | permission rule; never a model judgment | denial test per boundary (S15) | n/a |
| R3a | filter articles to the ticket's workspace | fixed_code | scope filter is a rule | every candidate carries the ticket's workspace id | n/a |
| R3b | rank filtered articles by relevance | model_inference | relevance is a judgment over text | top items re-checked for workspace id in code | n/a |
| R4 | decide whether a second search is needed | adaptive_investigation | unknown: whether the first result set answers the asked question cannot be known before reading it | each round re-enters R3a | max 3 rounds, 6 calls, ceiling from policy (hypothesis); stop when no new article ids appear |
| R5 | draft the reply | model_inference | text generation | policy check: no claim of having sent, no citation outside the workspace | n/a |
| R6 | show the draft to the agent | fixed_code | rendering is a rule | n/a | n/a |
| R7 | send the reply | human_decision | commits the company to a customer | approval record bound to the draft version | no response: nothing is sent |

Envelope excerpt:

```json
{
  "findings": [
    {"step_id": "R2", "current": "model_inference", "required": "fixed_code",
     "rule": "permission rule", "note": "prior proposal asked the model to judge workspace access"}
  ],
  "uncertainties": ["R4 ceilings are hypotheses; no budget policy version supplied"],
  "requested_followups": ["budget policy owner to set R4 ceilings", "S20 to measure R4 rounds per ticket"],
  "proposed_links": [{"from": "allocation-table@v1", "rel": "depends_on", "to": "permission-model@v3", "impact_policy": "invalidate_applicability"}]
}
```
