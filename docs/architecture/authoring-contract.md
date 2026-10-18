# Authoring contract for role bodies and shared skills

Every one of the 64 role bodies (`agents/<id>.md`) and 28 shared skills (`skills/aipt-method-<name>/SKILL.md`) follows this contract. It exists so that the catalog is substantive (FR-003, AT-02), methods are not duplicated across roles (FR-004) and nothing in a body depends on a provider, a model id, a price or a private source (FR-032, FR-029).

## 1. Voice and prohibitions

- Second person, imperative, present tense: "Read the frozen proposal. Name the premise it depends on."
- No persona preamble. Never "You are a world-class…", never a biography, never adjectives about the agent's talent. The first line after the title is the job.
- No provider names, model names, model ids, prices, token rates, context-window sizes or host version facts. Those live in `policies/*.json` and `docs/compatibility/`.
- No private paths, project names, client names, employer names, real people or real companies. Examples use the synthetic Larkspur Support / Reply Assist material under `examples/support-copilot/` or an equally fictional case.
- No restating a shared skill's method inside a role. A role *names* the skill it applies (`aipt-method-<name>`, S-id) and says what it feeds in and what it takes out. If two roles would need the same paragraph, that paragraph belongs in a skill.
- No hedging filler ("it is important to note", "be sure to"), no decorative headings, no emoji.
- Every "must not" has a stated alternative ("Instead, …"). A rule without a replacement behavior is a slogan.
- Claims of capability are limited to what the host supplies. A body never says it has run something, verified something or seen a child agent; it says what evidence it requires before saying so.
- British/American spelling: American. Plain words over jargon; define a term the first time if it is specific to this package (work order, receipt, applicability, protected requirement).

## 2. Role body template (`agents/<id>.md`)

Length 120–240 lines. Sections in this order; headings exactly as written.

```
# <Name>

<One sentence: the job, from registry description, in the imperative or as "What it does".>

## Position
- Role id: `<id>` · Type: <type> · Team: <team name>
- Reports to: `<reports_to>` · Reviewed by: `<reviewed_by>`
- Write scope: <write_scope> · May dispatch: <yes/no> · Acceptance authority: <value>
- Dispatch condition: <dispatch_condition verbatim>
- Shared skills: `aipt-method-…` (S0x), …

## Use when
3–6 bullets of concrete triggers, phrased as conditions in the case state or request.

## Do not use when
3–6 bullets. Each names the role or workflow to use instead.

## Inputs
Typed list. For each: name, the record kind and version reference expected (e.g. "frozen proposal — `proposal` version id"), and what the role does if it is missing (ask, refuse, or proceed with an explicit limitation).

## Method
Numbered steps, 5–12, unique to this role. Reference skills by name at the step where they apply. Steps say what to read, what to produce and what to check. No step is "think carefully".

## Output
The artifact(s) from the registry output_contract: file name and shape (keys for JSON; headings for Markdown). Then the envelope fields this role always fills: `findings`, `evidence_refs`, `uncertainties`, `requested_followups`, and any role-specific ones (`observed_checks` for roles that run commands; `proposed_links` for stewards; `scope_violations` always when relevant).

## Evidence rules
What counts as support for this role's statements; what must be labelled hypothesis, observation or unknown; what the role must never infer. Cite S12 (evidence-and-lineage) rather than restating it.

## Distinctive rule
<registry distinctive_rule verbatim, then one short paragraph on how it changes behavior in practice.>

## Status and escalation
Which `status` values the role may return (`complete`, `needs_input`, `blocked`, `partial`, `out_of_scope`, `failed`), the condition for each, and where it escalates (its reviewer, a named workflow, or `human-owner`). State plainly that a `complete` output is the assigned contract met, not a product decision.

## Worked example
A compact, concrete input → output on the synthetic corpus (or another fictional case): 15–40 lines. Show the actual artifact shape, not a description of it.

## Negative case
<registry negative_test verbatim.> Then: the input that would tempt the failure, the wrong output, and the correct output. This is the fixture `evals/roles/<id>/negative.json` describes.

## Review rubric
4–6 checks the reviewing role applies, each observable (present/absent, matches/does not match), none about tone.
```

## 3. Skill template (`skills/aipt-method-<name>/SKILL.md`)

The directory name equals the `name` field (Agent Skills spec). Length 120–300 lines in `SKILL.md`; longer material goes under `references/`, one level deep.

```
---
name: aipt-method-<name>
description: <What it does and when to use it. Trigger words first. ≤ 600 characters; hard limit 1024.>
license: MIT
metadata:
  aipt_skill_id: "S0x"
  aipt_provenance: "adapt" | "newly_authored"
  aipt_version: "0.1.0"
---

# <Title>

## Purpose
## Use when
## Do not use when
## Required inputs
## Method
## Output contract
## Evidence and uncertainty rules
## Guardrails
## Success criteria
## Example
```

Rules for adapted skills (S01–S11): preserve the source's purpose, use/do-not-use conditions, process order, output contract, guardrails and success criteria in substance; restate inputs as typed versioned references and outputs as artifacts plus envelope fields; add the Example section (the sources had none); drop any sentence that names the author's earlier projects or installation paths. The `metadata.aipt_provenance` is `adapt`.

Rules for new skills (S12–S28): `metadata.aipt_provenance` is `newly_authored`. Where a method rests on a well-known public technique (for example: freezing an evaluation protocol before results; p95 of parallel stages; idempotency keys for non-idempotent actions), state the technique in plain words. Do not copy another skill pack's text. Primary technical references may be named in `references/sources.md` as plain titles and URLs with a one-line note on what was taken; no quotation beyond a phrase.

## 4. Fixtures and readiness labels

For every role, three files under `evals/roles/<id>/`:
- `positive.json`: `{"role_id", "label": "unrun", "scenario": "<text>", "input_refs": [{"kind", "title", "synthetic": true}], "expected": {"status": "complete", "must_include": [...], "must_not_include": [...], "checks": [...]}}`
- `negative.json`: same shape; `scenario` is the registry negative test situation; `expected.status` is whatever the correct behavior yields (often `needs_input`, `blocked` or `complete` with a refusal recorded in findings); `must_not_include` names the tempting wrong output.
- `readiness.json`: `{"role_id", "state": "authored", "contract_validated": false, "adapter_generated": false, "native_discovered": false, "scenario_executed": false, "evaluated": false, "updated": "<date>"}`. Later milestones flip flags; nothing else edits the body to claim a state.

`must_include` / `must_not_include` items are short literal phrases or JSON keys that a checker can search for in the response envelope; `checks` are sentences for a human or model grader.

## 5. Quality gates applied after authoring

1. **Structure**: every heading present in order; length within range; frontmatter valid; `name` equals directory; description ≤ 1024.
2. **Prohibitions**: a scan for provider/model names, prices, private names, persona openers, forbidden filler; any hit fails the body.
3. **Non-duplication**: a near-duplicate detector over Method sections (shingle similarity) flags any pair of roles above threshold; the fix is to move the shared text into a skill and reference it.
4. **Registry agreement**: Position block matches `registry/agents.json`; Distinctive rule and Negative case quote the registry verbatim; skills listed equal `skill_ids`.
5. **Reviewer pass**: an independent reader checks that Method is actually distinct from adjacent roles (the pairs named in `docs/spec/03_AGENT_DIRECTORY.md` "Distinct responsibilities that should not be merged"), that the Worked example is concrete, and that the Negative case is role-specific rather than generic.

The gate results are recorded per role in `readiness.json` (`contract_validated`) and summarized in `docs/directory/readiness.md`.
