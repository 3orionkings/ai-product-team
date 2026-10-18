# Tool contract and action record schema

Longer material for `aipt-method-tool-and-permission-boundaries` (S16). The SKILL.md Method is authoritative; this file gives the full field list and the action record state machine.

## Tool contract fields

```json
{
  "tool_id": "save_draft",
  "effect_class": "write",
  "model_access": "propose_only",
  "target_kinds": ["ticket", "draft"],
  "inputs_schema": {"required": ["ticket_id", "workspace_id", "expected_ticket_version", "body", "idempotency_key"]},
  "result_schema": {"draft_id": "string", "draft_version": "string", "ticket_version_seen": "string"},
  "errors": [
    {"code": "invalid_input", "retry_safe": false},
    {"code": "not_permitted", "retry_safe": false},
    {"code": "not_found", "retry_safe": false},
    {"code": "version_conflict", "retry_safe": false},
    {"code": "timeout", "retry_safe": false, "outcome": "unknown"},
    {"code": "transient", "retry_safe": true},
    {"code": "permanent", "retry_safe": false}
  ],
  "idempotency": {"required": true, "key_source": "proposal_version + action_id", "replay_returns": "stored result"},
  "timeout_ref": "policies/tool-timeouts@current",
  "retry": {"max_attempts": 3, "backoff": "exponential", "only_codes": ["transient"]},
  "executor": "draft-writer (code, permission check before write)",
  "boundaries": [
    {"rule": "workspace_id equals requester workspace", "kind": "enforceable", "mechanism": "code check", "demonstrated_by": "NT-save-01"},
    {"rule": "body must not claim the reply was sent", "kind": "requested", "mechanism": "prompt instruction", "demonstrated_by": null}
  ],
  "negative_tests": ["NT-save-01 forbidden workspace", "NT-save-02 repeated key", "NT-save-03 stale version", "NT-save-04 timeout reconciliation"]
}
```

`model_access` values: `direct` (the model's call runs the tool; allowed only for `read` with no side effects), `propose_only` (the model emits an action record; a separate executor runs it), `none` (the tool is absent from the model's list).

## Action record state machine

```
proposed  --approval recorded-->  approved  --executor runs tool-->  executed
proposed  --permission check fails or approval refused-->  refused
approved  --tool call times out-->  unknown  --reconciliation read-->  executed | refused
```

- `proposed`: written by the model; carries `record_hash` over all fields except `state`, `approval_ref`, `receipt_ref`.
- `approved`: an `approval` record (S25) names the same `record_hash`; a hash mismatch leaves the record `proposed` and raises a finding.
- `executed`: a receipt (S19) exists with the tool call, exit status and the target versions observed; the record stores `receipt_ref`.
- `refused`: a code check or approval refused the action; the reason code is recorded.
- `unknown`: the tool call did not return within its timeout; nothing further runs until a read of the target shows whether the effect happened.

## Boundary classification worked list

| Rule | Kind | Why |
|---|---|---|
| Tool absent from the model's list | enforceable | the model has no way to call it |
| Input schema rejects unknown fields | enforceable | validation runs in code before the tool |
| Permission check before write | enforceable | code refuses with `not_permitted` |
| Target allowlist | enforceable | code compares the target id against the list |
| "Never send on the customer's behalf" in the prompt | requested | nothing checks it; keep as guidance only |
| "Only cite articles from this workspace" in the prompt | requested | replace with the S15 scope filter and keep the text as guidance |
