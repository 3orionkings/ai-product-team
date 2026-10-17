# Test report RA-ISO-NEG-02 — cross-workspace retrieval negative test

Document id: LS-TEST-07
Date: 2026-10-14
Status: observed failure; open
Build under test: 0.9.0-rc1 (`06-changelog.md`)
Requirement under test: WS-ISO-1 (`04-workspace-isolation-requirement.md`), acceptance criteria AC-3 and AC-4
Executed by role: test engineer
Observation source: the synthetic demonstration's own test runner

Synthetic material. This report describes a labeled design fixture for the package's W10 (`process-change`) workflow. It is not a report of an actual product incident, and the product, workspaces and documents in it are fictional. The commands below are written against a demonstration application that is built in a later milestone; their exact form is provisional and is marked as such.

## Summary

Under one query shape, a document belonging to `ws-beta` was returned for a query made from `ws-alpha`. The shape is a short single-term query whose term is a tag shared by documents in both workspaces. Three other query shapes behaved correctly. The failure is reproducible on build 0.9.0-rc1 and was not observed on build 0.8.1.

This report establishes that AC-3 fails for at least one shape on the release candidate. It does not establish the cause; see the hypothesis section, which is labeled as such.

## What this report shows and does not show

Shows

- A cross-workspace document in a result set, on a named build, under a stated query, with the result listing recorded.
- That the exact-title shape covered by RA-ISO-POS-01 still passes on this build.

Does not show

- The root cause. One hypothesis is recorded below. It has not been confirmed by inspecting or changing code.
- Whether other unstated query shapes also leak.
- Anything about the correctness of RA-ISO-POS-01 on 2026-08-19. That test's recorded result is a genuine pass for the shapes it covered on the build it ran against.
- Anything about who may send a reply. Sending authority is governed by `02-support-policy.md` and is untouched by this finding.

## Setup

1. Load the ws-alpha index (A-KB-01 through A-KB-04) and the ws-beta index (B-KB-01 through B-KB-04) from `05-sample-tickets.md`.
2. Confirm the build identifier reports 0.9.0-rc1.
3. For each query below, record the full ordered result list including document ids, then check every id's prefix against the requesting workspace.

## Reproduction steps (provisional command shapes)

The demonstration application is expected to expose a retrieval command of roughly this form. Argument names may change when it is built; the steps, inputs and expected observations are the contract.

```text
support-copilot retrieve --workspace ws-alpha --query "Station pickup schedule" --shape exact-title
support-copilot retrieve --workspace ws-alpha --query "schedule" --shape keyword
support-copilot retrieve --workspace ws-alpha --query "pickup schedule change" --shape phrase
support-copilot retrieve --workspace ws-alpha --query "" --shape keyword
```

Run each command once; the application is deterministic for a fixed index.

## Observations

| # | Requesting workspace | Query | Shape | Result ids in order | Outcome |
|---|---|---|---|---|---|
| 1 | ws-alpha | "Station pickup schedule" | exact-title | A-KB-01 | Pass |
| 2 | ws-alpha | "schedule" | keyword (single term) | A-KB-01, **B-KB-01** | **Fail** — B-KB-01 belongs to ws-beta |
| 3 | ws-alpha | "pickup schedule change" | phrase | A-KB-01 | Pass |
| 4 | ws-alpha | "" (empty) | keyword | (no results) | Pass |

Observation 2 is the failure. B-KB-01, "Watering schedule FAQ", carries the tag `schedule`; so does A-KB-01. The ws-beta document appeared at rank 2 of 2.

### Control run on the previous build

The same four queries were run against build 0.8.1 after switching the build identifier. Observation 2 returned A-KB-01 only. The leak is specific to 0.9.0-rc1 among the two builds tested.

### Additional probe

From ws-beta, the single-term query "pause" returned B-KB-04 only. The single-term query "schedule" from ws-beta returned B-KB-01 only. The leak was observed from ws-alpha and not from ws-beta in this session. This asymmetry is recorded as an observation; it is not explained.

## Hypothesis (not established)

Build 0.9.0-rc1 added tag-based matching and merged title, keyword and tag matches into one ranked list before the result limit. The title and keyword lookup paths filter on workspace id (introduced in 0.7.0). It is possible that the tag lookup path does not apply the workspace filter, so a tag shared across workspaces returns documents from both, and the merge step does not re-filter. This would be consistent with observations 1 through 4 and with the control run on 0.8.1.

It would not by itself explain the asymmetry in the additional probe. The hypothesis is therefore incomplete and has not been confirmed. Confirming or refuting it requires reading the retrieval code or adding a check at the merge step, neither of which this report did.

## Relationship to existing records

- Requirement WS-ISO-1 is not satisfied by build 0.9.0-rc1. The requirement itself is unchanged and remains protected.
- Validation RA-ISO-POS-01 remains a pass for exact-title queries on build 0.7.1. Its applicability to 0.9.0-rc1 is limited: observation 1 reproduces its result on the new build, but the component it tested has changed and the new build fails a shape it did not cover.
- The claim "retrieval is isolated per workspace in build 0.9.0-rc1" is contradicted by observation 2.
- The proposed release readiness decision for 0.9.0 lists WS-ISO-1 as a criterion. This report is new evidence against that criterion.

## What this report asks for

These are requests for review, not decisions.

1. Review of the 0.9.0 release readiness decision in light of observation 2.
2. A targeted correction to the retrieval component, scoped to the path that produced observation 2, with the cause confirmed rather than assumed.
3. A permanent negative test for AC-3 covering single-term, phrase, tag and empty shapes from both workspaces, so that a pass on exact-title queries can no longer stand in for isolation.
4. Revalidation of both the positive and the negative checks against the corrected build before readiness is reconsidered, by a reviewer who did not make the correction.

Nothing in this report asks for the requirement to change, for drafting behavior to change, or for any artifact unrelated to retrieval to be reopened.
