---
name: aipt-method-tool-and-permission-boundaries
description: Tool contract, permission boundary, idempotency key, timeout, retry policy, proposed action versus executed action, enforceable boundary versus requested compliance. Use when defining or reviewing the tools an AI feature may call: typed inputs, results and errors; idempotency keys for non-idempotent effects; timeouts and retry rules; separating actions the model proposes from actions the system executes; binding each effect to target identifiers and versions; and labeling each boundary as enforced by code or merely requested of the model. Produces tool contract and action record artifacts.
license: See LICENSE_PENDING.md in the repository root.
metadata:
  aipt_skill_id: "S16"
  aipt_provenance: "newly_authored"
  aipt_version: "0.1.0"
---

# Tool and permission boundaries

Define what each tool accepts, returns and may change, and keep the decision to execute an effect outside the model.

## Purpose

A tool is any function a model can ask the system to run. This skill produces four things for every tool: a typed contract (inputs, results, errors), a failure policy (timeouts, retries, idempotency), a separation between the action the model proposes and the action the system executes, and a label for each boundary that says whether code enforces it or a prompt merely requests it.

Two terms carry the skill. An **enforceable boundary** is a restriction that holds regardless of what the model outputs: the tool is absent from the model's tool list, a schema rejects the input, a permission check in code refuses the call, an allowlist limits the target. An **instruction requesting compliance** is text in a prompt that asks the model not to do something; it is useful guidance and worthless as a control, because nothing checks it and injected text can override it. The package's assurance levels apply: a boundary earns `enforced_by_host` only when a specific refusal has been demonstrated; until then it is `recorded`.

Three public techniques are used in plain words. An idempotency key is a caller-supplied identifier sent with a non-idempotent request so that a repeat of the same key performs the effect once and returns the same result. A version precondition is an expected prior version sent with a write so the write is refused if the target has changed. A timeout is an unknown outcome, not a failure, until the state is read back.

## Use when

- A feature exposes any tool to a model, whether it reads or changes state.
- A tool has an effect: write, send, delete, pay, or call an external system.
- A `review` or `challenge` finds a prompt instruction standing where a control should be.
- Retries, timeouts or duplicate-call behavior are undefined for a tool that changes state.
- An approval must bind to exactly what will be executed, not to a description of it.

## Do not use when

- You need to decide whether a step belongs to code, inference, a loop or a person: use `aipt-method-ai-responsibility-allocation` (S14).
- You need to specify which sources may be read and how scope survives transformation: use `aipt-method-retrieval-and-context-contracts` (S15).
- You need to decide who may approve an action and under what delegation: use `aipt-method-delegated-authority` (S25).
- You need to design the confirmation a person sees before an effect: use `aipt-method-accessible-interaction-design` (S28).
- You need to review a whole feature's trust boundaries, injection exposure and egress: use `aipt-method-security-and-privacy-review` (S26); this skill writes the contracts that review reads.

## Required inputs

- **Tool inventory** — `artifact` or `proposal` version listing every tool the model may call. If missing, enumerate tools from the proposal text, label the list a hypothesis, and return `needs_input` if no proposal names any.
- **Effect classification** — per tool: `read`, `write`, `send`, `delete`, `external`. If missing, classify from the tool's description, label each classification a hypothesis, and treat any uncertain tool as an effect tool.
- **Allocation table** — the S14 `proposal` version, if one exists, so the executing component for each effect is known. If missing, proceed and write `executor: unassigned` for every effect.
- **Permission model** — `requirement` or `source` version stating which principals may cause which effects. If missing, no boundary may be labeled `enforceable`; write every boundary as `requested` and return `needs_input`.
- **Host capability facts** — the compatibility record stating which restrictions the host can apply, by reference. If missing, label every boundary `requested` until a demonstration exists; never fill the gap from memory.
- **Approval model** — the S25 `approval` or `decision` version, where effects need approval. If missing, every effect's action record stays in state `proposed`.

## Method

1. **Inventory the tools.** One row per tool: `tool_id`, purpose, effect class, target entity kinds, and whether the model can call it directly or only propose it.
2. **Type the contract.** Write the input schema (required fields, identifiers, expected versions), the result schema (what changed, by identifier, and the resulting version), and the error taxonomy: `invalid_input`, `not_permitted`, `not_found`, `version_conflict`, `timeout`, `transient`, `permanent`. Every error carries `retry_safe: true | false`.
3. **Require idempotency keys** for every tool whose effect is not idempotent (create, send, charge, append). The key is derived from the action record identity (`proposal_version` plus `action_id`), is required in the input schema, and the contract states that a repeated key performs the effect once and returns the stored result.
4. **Set timeouts and retries** per tool: a timeout value by reference to policy; a retry rule that retries only errors marked `retry_safe`, with a maximum attempt count and a backoff; no retry of a non-idempotent effect without its key. When the ceiling is reached, the caller records outcome `unknown` and performs a reconciliation read before any further action.
5. **Separate proposed from executed.** The model produces an action record in state `proposed`: `tool_id`, inputs, target identifiers with expected versions, rationale, expected effect. A separate component executes: fixed code behind a permission check, or a person. The model never holds the credential that executes an effect, and the executing component accepts only action records, not free text.
6. **Bind effects to identifiers and versions.** Every effect names the exact entity id and the version it expects; the tool refuses with `version_conflict` on mismatch. Approvals (S25) bind to the hash of the action record so that what was approved is byte-for-byte what executes.
7. **Classify every boundary.** For each rule that limits what a tool can do, write `kind: enforceable` with the mechanism and how it was or will be demonstrated, or `kind: requested` with the instruction text. For each `requested` boundary that guards an effect, record a finding and propose the enforceable replacement: remove the tool from the model's list, add a schema constraint, add a code permission check, or add an allowlist.
8. **Write negative tests** per effect tool: a call against a forbidden target returns `not_permitted`; a repeated idempotency key produces one effect; a stale expected version returns `version_conflict`; a timeout leaves an `unknown` record and a reconciliation read. Shape them with `aipt-method-requirements-and-acceptance` (S13).
9. **Assemble the artifacts and the envelope.** Emit `tool-contracts.json` and the action record shape, link each contract to the permission model and requirement versions, and fill the envelope fields below.

## Output contract

Artifact: `tool-contracts.json`, kind `artifact`, with `tools[]`, each:

`tool_id`, `effect_class`, `model_access` (`direct` | `propose_only` | `none`), `inputs_schema`, `result_schema`, `errors[]` (`code`, `retry_safe`), `idempotency` (`required`, `key_source`), `timeout_ref`, `retry` (`max_attempts`, `backoff`, `only_codes[]`), `boundaries[]` (`rule`, `kind`: `enforceable` | `requested`, `mechanism`, `demonstrated_by`), `negative_tests[]`.

Artifact: action record shape, kind `proposal` while `proposed` and `artifact` once executed:

`action_id`, `proposal_version`, `tool_id`, `inputs`, `targets[]` (`entity_id`, `expected_version`), `idempotency_key`, `state` (`proposed` | `approved` | `executed` | `refused` | `unknown`), `approval_ref`, `receipt_ref`, `record_hash`.

Envelope fields this skill always fills:

- `findings`: each `requested` boundary guarding an effect; each non-idempotent tool without a key; each effect tool with `model_access: direct`; each write without a version precondition; each undefined timeout or retry.
- `evidence_refs`: the tool inventory, permission model, host capability and approval versions read.
- `artifact_refs`: the contracts version and the action record shape version.
- `proposed_links`: each tool contract `depends_on` the permission model version, `impact_policy: invalidate_applicability`; each negative test `verifies` the boundary it covers.
- `uncertainties`: hypothesized effect classes, boundaries awaiting demonstration, timeouts without a policy reference.
- `requested_followups`: host capability facts, receipts for negative tests, the executor for any `unassigned` effect.
- `scope_violations`: any request to execute an action, to hold a credential, or to simulate a tool the host does not provide.

## Evidence and uncertainty rules

- "Enforced" needs a demonstration: a receipt of a refused call against the current version, meaning the recorded command, exit status and target versions (S19), or a host configuration version that applies the restriction. Without one, write `kind: requested` or `demonstrated_by: pending`.
- Read `retry_safe` from the contract, never from the tool's name or a general sense that reads are harmless; a read with side effects (audit logging, quota consumption) is still an effect for retry purposes.
- A timeout is an outcome `unknown`. Writing it as `failed` is a false claim; writing it as `succeeded` is a worse one.
- A tool the host does not provide is `blocked`, and its output is never written by hand; the envelope states the missing tool.
- Follow `aipt-method-evidence-and-lineage` (S12) for citing versions and typing claims; this skill adds only the rules above.

## Guardrails

- Do not let the model call an effect tool directly. Instead, give the model `propose_only` access and let code behind a permission check, or a person, execute the action record.
- Do not express a permission as a prompt instruction alone. Instead, enforce it in code or by tool absence, and keep the instruction as guidance labeled `requested`.
- Do not retry a non-idempotent effect without an idempotency key. Instead, require the key in the schema, or perform a reconciliation read and stop.
- Do not record a timeout as a failure. Instead, record `unknown`, read the state back, and decide from what is observed.
- Do not act on an entity by name, by "latest" or by position in a list. Instead, bind the action to the entity id and its expected version.
- Do not give the executing component the model's broad scope. Instead, give it the narrowest credential that performs the one effect.
- Do not simulate a tool the host does not supply. Instead, return `blocked` and name the missing tool in `requested_followups`.
- Do not approve an action record and then execute something assembled from it. Instead, bind the approval to the record hash and execute that record unchanged.

## Success criteria

- Every tool has input, result and error schemas, and every error carries `retry_safe`.
- Every non-idempotent tool requires an idempotency key derived from the action record identity.
- Every tool has a timeout reference and a retry rule limited to `retry_safe` errors.
- Every effect tool has `model_access: propose_only` or `none`, and a named executor.
- Every effect binds to entity ids and expected versions, and approvals bind to the record hash.
- Every boundary is labeled `enforceable` or `requested`, and every `requested` boundary guarding an effect has a finding and a proposed replacement.
- Every effect tool has the four negative tests, each with a status.

## Example

Reply Assist at Larkspur Support drafts replies and never sends them. The model can read the ticket, search articles, and save a draft; sending stays with the human agent in the support system. Contract excerpt for the one effect tool the model may propose:

```json
{
  "tools": [
    {"tool_id": "send_reply", "effect_class": "send", "model_access": "none",
     "boundaries": [{"rule": "the model cannot send", "kind": "enforceable",
                     "mechanism": "tool absent from the model's tool list",
                     "demonstrated_by": "receipt: model call to send_reply returns not_permitted (planned)"}]},
    {"tool_id": "save_draft", "effect_class": "write", "model_access": "propose_only",
     "inputs_schema": {"ticket_id": "string", "workspace_id": "string", "expected_ticket_version": "string",
                       "body": "string", "idempotency_key": "string"},
     "result_schema": {"draft_id": "string", "draft_version": "string"},
     "errors": [{"code": "not_permitted", "retry_safe": false}, {"code": "version_conflict", "retry_safe": false},
                {"code": "timeout", "retry_safe": false}, {"code": "transient", "retry_safe": true}],
     "idempotency": {"required": true, "key_source": "proposal_version + action_id"},
     "timeout_ref": "policies/tool-timeouts@current",
     "retry": {"max_attempts": 3, "backoff": "exponential", "only_codes": ["transient"]},
     "boundaries": [{"rule": "workspace_id must equal the requester's workspace", "kind": "enforceable",
                     "mechanism": "code permission check before write", "demonstrated_by": "NT-save-01 (planned)"},
                    {"rule": "draft must not claim the reply was sent", "kind": "requested",
                     "mechanism": "prompt instruction", "demonstrated_by": null}]}
  ]
}
```

Action record proposed by the model and executed by code:

```json
{"action_id": "act-0419", "proposal_version": "draft-plan@v2", "tool_id": "save_draft",
 "targets": [{"entity_id": "ticket-7731", "expected_version": "t7731@v5"}],
 "idempotency_key": "draft-plan@v2/act-0419", "state": "executed",
 "approval_ref": null, "receipt_ref": "rcpt-2210", "record_hash": "sha256:9f3c..."}
```

The `requested` boundary on `save_draft` produces a finding with the proposed replacement: a code check that rejects a draft body containing a sent-confirmation phrase before the write.
