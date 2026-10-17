# Allocation row schema and classification questions

Longer material for `aipt-method-ai-responsibility-allocation` (S14). The SKILL.md Method is authoritative; this file expands the row shape and the four classification questions so a reviewer can apply them mechanically.

## Row shape

```json
{
  "step_id": "R4",
  "step": "decide whether a second search is needed",
  "effect_class": "read",
  "mechanism": "adaptive_investigation",
  "reason": "whether the first result set answers the asked question is not knowable before reading it",
  "named_unknown": "coverage of the asked question by the first result set",
  "check_after": "each round re-enters the workspace scope filter (R3a)",
  "budget": {"max_iterations": 3, "max_tool_calls": 6, "wall_clock_ceiling": "policy ref", "max_sources": 2},
  "termination": {
    "success_predicate": "every question in the ticket maps to at least one retrieved article",
    "no_progress_rule": "two consecutive rounds add no new article ids",
    "on_exhaustion": "return the current set labeled partial"
  },
  "requirement_refs": ["REQ-012@v2"],
  "acceptance_check_refs": ["AC-012-budget", "AC-012-termination"],
  "alternatives_rejected": [
    {"mechanism": "fixed_code", "fails_when": "the ticket asks a question whose wording does not match any article title"},
    {"mechanism": "model_inference", "fails_when": "a single ranking pass cannot see what the first pass missed"}
  ]
}
```

Fields `named_unknown`, `budget` and `termination` are required when `mechanism` is `adaptive_investigation` and absent otherwise. `check_after` is required when `mechanism` is `model_inference` and when `effect_class` is anything other than `none`.

## The four questions, in order

1. **Rule test.** Can you write, in the row, a rule that maps every input to the correct output? If yes, the candidate is `fixed_code`. If the rule has an exception you cannot state, the answer is no.
2. **Language test.** Does the step read natural language or produce text, and is one pass over supplied context enough? If yes, the candidate is `model_inference`.
3. **Dependency test.** Does the choice of the next read or call depend on what an earlier result revealed? If yes, the candidate is `adaptive_investigation`, and the row must name the unknown.
4. **Commitment test.** Does the step commit the organization, spend, send, delete or accept risk on a person's behalf? If yes, the step is `human_decision`, or an effect covered by a recorded delegation under `aipt-method-delegated-authority` (S25).

The permission rule overrides the questions: any check of the form "is this actor permitted to see or do this" is `fixed_code` regardless of how the questions answer.

## Reviewer checks on a submitted table

- Every row has exactly one `mechanism`.
- Every `adaptive_investigation` row has all three of `named_unknown`, `budget`, `termination`, and at least one entry in `alternatives_rejected`.
- Every `model_inference` row has a non-empty `check_after`.
- Every row with `effect_class` other than `none` traces to a `human_decision` row or a delegation reference.
- No row whose `step` contains a permission check has a mechanism other than `fixed_code`.
