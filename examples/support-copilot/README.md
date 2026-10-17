# Larkspur Support / Reply Assist — synthetic example corpus

This directory is the document corpus and case brief for the package's support-copilot demonstration. It is the material that workflow W02 (`shape-feature`) and workflow W10 (`process-change`) run against in their contract fixtures, and it is the case that `docs/spec/02_ARCHITECTURE.md` §12.3 describes as a labeled design fixture.

The demonstration application itself (a small retrieval-and-drafting program) is built in a later milestone. Nothing in this directory is code. Everything here is a document that an agent reads as an authorized source.

## Everything here is synthetic

Every company, product, workspace, ticket, document, test, date, version number and role in this directory is invented for the demonstration.

- "Larkspur Support" is a fictional help-desk product. "Reply Assist" is a fictional feature of it.
- "ws-alpha" and "ws-beta" are fictional customer workspaces with fictional knowledge documents.
- The tickets contain no personal data by construction: no names, no addresses, no account identifiers, no message bodies copied from anywhere.
- No real people, companies, email addresses, web addresses or prices appear. Internal references use invented document ids such as `LS-POL-02`.
- The test report in `corpus/07-...` describes a fixture, not an actual product incident.

If a reader recognizes any resemblance to a real organization, that resemblance is accidental and the content should be treated as fiction regardless.

## What the example is for

The package's controller checks structure, references, versions, authority, independence and state transitions. It never decides whether evidence is persuasive. A demonstration therefore needs material in which the *structural* behaviors are observable: a conflict that must be preserved rather than resolved, a protected requirement that must survive a failed implementation, an old test result that must stay historical rather than be rewritten, and a release decision that must be queued for review rather than flipped.

This corpus supplies exactly those situations and nothing else. It is deliberately small so that a reader can hold the whole case in mind and recognize when an agent has invented a fact to fill a gap.

## File map

| File | Role in the case | Date inside the document |
|---|---|---|
| `brief.md` | Case brief: objective, protected constraints, source scope, owner. Input to `case init`. | — |
| `corpus/01-product-overview.md` | The help-desk product and the proposed Reply Assist feature. | 2026-09-08 |
| `corpus/02-support-policy.md` | Current reply policy: agents send; AI may draft only. The controlling source on authority. | 2026-09-20 |
| `corpus/03-roadmap-slides-2026-05.md` | Older slide notes saying Reply Assist will send routine replies automatically. The deliberate conflict. | 2026-05-12 |
| `corpus/04-workspace-isolation-requirement.md` | Protected requirement WS-ISO-1 and the positive test that passed. | 2026-07-02 (test 2026-08-19) |
| `corpus/05-sample-tickets.md` | Eight synthetic tickets across ws-alpha and ws-beta, plus each workspace's knowledge-document index. | 2026-09 |
| `corpus/06-changelog.md` | Release notes 0.6.0 through 0.9.0-rc1. No entry introduces sending. | 2026-06 to 2026-10 |
| `corpus/07-cross-workspace-negative-test-2026-10.md` | New evidence for W10: a negative test found a ws-beta document returned for a ws-alpha query under one query shape. | 2026-10-14 |
| `scenario.md` | How W02 and W10 are expected to behave on this corpus, with failure signatures. | — |

Files 01 through 06 form the source scope for the W02 run. File 07 is admitted as a new source version only when the W10 run begins; see `brief.md` and `scenario.md`.

## The deliberate conflict (W02)

`corpus/02-support-policy.md`, dated 2026-09-20, states that only a human agent sends a reply and that AI assistance may draft only. `corpus/03-roadmap-slides-2026-05.md`, dated 2026-05-12, states that Reply Assist "will send routine replies automatically". The newer document is a policy; the older one is a roadmap ambition whose own speaker notes say policy sign-off had not been obtained.

No document in the corpus records a decision that withdraws or defers the May ambition. That absence is intentional. The correct W02 output keeps both sources visible, writes requirements that cannot be read as authorizing sending, includes a no-send negative case in the acceptance map, and leaves the authority question open for `human-owner`. Resolving the conflict by picking the newer document and dropping the older one is a fixture failure, because it hides a decision that nobody has made.

## The protected requirement and the new evidence (W10)

`corpus/04-workspace-isolation-requirement.md` defines WS-ISO-1: retrieval exposes only documents authorized for the requesting workspace. It is marked protected, owned by `human-owner`, and it records a positive test (RA-ISO-POS-01) that passed on 2026-08-19 with an explicitly stated coverage limit: exact-title queries only.

`corpus/07-cross-workspace-negative-test-2026-10.md` reports that on 2026-10-14, against build 0.9.0-rc1, a short single-term query from ws-alpha returned a ws-beta document. The report labels its root-cause hypothesis as a hypothesis.

The correct W10 behavior: the requirement stays approved and protected; the isolation claim becomes contested; the old positive test is marked historical (its result is not rewritten); the 0.9.0 release decision is queued for review; targeted work orders cover the retrieval fix and a new negative check; artifacts unrelated to retrieval are not touched. Retiring the requirement because its implementation failed is the failure this fixture exists to catch (PRD FR-025, acceptance test AT-13).

## How the fixtures use the corpus

`registry/workflows.json` carries a `fixture` field for each workflow. For W02 the scenario is "One document says drafts only; an older slide says send messages automatically." For W10 it is "A negative test disproves an isolation assumption after a positive test passed." The expected behaviors in those fields are the pass conditions; `scenario.md` expands them stage by stage and names the wrong outputs that would mean a failure.

Fixture runs are labeled `fixture_replay` by the controller and are never presented as live model performance.

## What this directory does not contain

- No code, no database, no run state. Those belong under a target project's `.aipt/cases/`.
- No private material of any kind; this directory is intended to be exportable in full.
- No decision that resolves the authority conflict, and no fix for the isolation defect. Both are left for the workflows and the human owner.
