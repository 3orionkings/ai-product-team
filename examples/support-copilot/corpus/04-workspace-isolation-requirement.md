# Requirement WS-ISO-1 — workspace isolation of retrieved documents

Document id: LS-REQ-04
Date: 2026-07-02
Status: approved
Protected: yes
Owner: human-owner
Originating sources: `01-product-overview.md` §1 and §5; `02-support-policy.md` rule R5

Synthetic material. This requirement and its tests belong to a fictional product and are written for a demonstration. The positive test described below did not run anywhere real.

## Statement

Retrieval exposes only documents authorized for the requesting workspace. For every retrieval call made on behalf of workspace W, every document in the result set belongs to W. This holds for every query shape, every ranking path and every index the retrieval component uses, now or later.

## Why this requirement is protected

Workspaces belong to different customer organizations. A document from one workspace appearing in another workspace's results is a disclosure between organizations. It cannot be made acceptable by a product tradeoff, a recall improvement or a schedule. For that reason:

- No agent may retire, weaken, scope down or reinterpret this requirement.
- A failed implementation does not retire the requirement. It queues remediation and revalidation.
- A change to this requirement is a protected authority change. It goes through W11 and requires attested acceptance by `human-owner`.
- A test that passes is evidence about the build and query shapes it covered. It is not evidence that the requirement is satisfied in general.

## Acceptance criteria

| Id | Criterion | Kind |
|---|---|---|
| AC-1 | For a query from ws-alpha whose best match is a ws-alpha document, every returned document belongs to ws-alpha. | Positive |
| AC-2 | For a query from ws-beta whose best match is a ws-beta document, every returned document belongs to ws-beta. | Positive |
| AC-3 | For a query from ws-alpha that would match a ws-beta document if the filter were absent, no ws-beta document is returned. | Negative |
| AC-4 | AC-1 through AC-3 hold for exact-title, keyword, phrase and tag-based query shapes, and for an empty query. | Coverage |
| AC-5 | The workspace filter is applied by the retrieval component itself, not by the caller after results are returned. | Structural |

A release is not ready with respect to this requirement until a positive check and a negative check have both passed against the release candidate, with receipts.

## Positive test RA-ISO-POS-01 — run 2026-08-19

Build under test: 0.7.1 (see `06-changelog.md`). Executed by role: test engineer. Observed by: the synthetic demonstration's own test runner; in the package's terms this is a fixture result, not a live receipt.

### Steps

1. Load the ws-alpha knowledge index (A-KB-01 through A-KB-04) and the ws-beta knowledge index (B-KB-01 through B-KB-04) as listed in `05-sample-tickets.md`.
2. From ws-alpha, issue an exact-title query for "Station pickup schedule". Record the result set.
3. From ws-alpha, issue an exact-title query for "Membership pause and resume". Record the result set.
4. From ws-beta, issue an exact-title query for "Watering schedule FAQ". Record the result set.
5. From ws-beta, issue an exact-title query for "Pause subscription". Record the result set.
6. For each result set, check that every returned document id has the requesting workspace's prefix (`A-` for ws-alpha, `B-` for ws-beta).

### Result

Passed. Each of the four queries returned exactly one document, and that document belonged to the requesting workspace. No cross-workspace document appeared.

### Coverage statement

This test covers AC-1 and AC-2 for the exact-title query shape only. It does not exercise AC-3, because every query was chosen so that its best match was in the requesting workspace. It does not exercise keyword, phrase, tag-based or empty queries (AC-4). It says nothing about retrieval paths added after build 0.7.1.

This coverage statement is part of the test record. If a later test shows a leak under a shape this test did not cover, this test's result remains a genuine pass for what it covered; its applicability to later builds is what changes.

## Negative test — specified, not yet run as of this document

A negative test for AC-3 is specified as follows and had not been run when this document was approved: from ws-alpha, issue queries whose strongest lexical match is a ws-beta document (for example a single term that appears in a ws-beta title and only incidentally in ws-alpha material), and confirm that no ws-beta document is returned under any supported query shape. The first run of such a test is reported in `07-cross-workspace-negative-test-2026-10.md`.

## Dependents declared for this requirement

The following records are expected to carry `depends_on` edges to this requirement in the case, with the stated impact policy, so that a change to the requirement's evidence reaches them and nothing else:

| Dependent | Impact policy |
|---|---|
| Claim: "Retrieval is isolated per workspace in build 0.9.0-rc1." | review |
| Validation: RA-ISO-POS-01 | invalidate_applicability |
| Artifact: retrieval component of the demonstration application | review |
| Decision: release 0.9.0 readiness | review |

Records with no declared edge to this requirement (for example the draft-label requirement, the ticket-summary artifact or the changelog) are not reached by impact traversal. If they should have been linked, that is a missing-lineage finding, not a reason to invalidate them automatically.
