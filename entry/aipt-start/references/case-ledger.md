# Case ledger

`aipt-cases/<case-id>/ledger.jsonl` is the case's memory. Every record a role relies on is one line. Lines are appended and never edited or deleted. A change is a new line that refers to the old one.

## Line format

```json
{"seq": 14, "at": "2026-10-17T14:05:00Z", "kind": "claim", "id": "clm-07", "version": "v2",
 "hash": "sha256:3b1f…", "by_role": "context-analyst", "by_task": "task-03", "execution": "native",
 "refs": [{"rel": "supersedes", "to": "clm-07@v1"}],
 "payload": {"statement": "…", "claim_type": "fact", "status": "contested"}}
```

- `seq`: 1, 2, 3 … in append order.
- `kind`: one of `source`, `claim`, `requirement`, `proposal`, `decision`, `artifact`, `validation`, `challenge`, `review`, `approval`, `link`, `task`, `receipt`, `user_input`.
- `id` and `version`: a record is cited as `id@version`. A new version is a new line with a `supersedes` ref to the previous one.
- `hash`: SHA-256 of the payload or of the artifact file. Approvals and reviews are bound to the hashes they saw.
- `execution`: `native`, `sequential`, `manual_handoff` or `controller` (for lines this session writes itself).

The recipes and role files call records "nodes". In this release a node is a ledger record.

## Vocabularies

| Field | Values |
|---|---|
| `claim_type` | `fact`, `hypothesis`, `observation` |
| claim `status` | `proposed`, `supported`, `contested`, `unsupported`, `superseded` |
| requirement `status` | `proposed`, `approved`, `retired`, `superseded`; plus `protected: true` or `false` |
| decision `status` | `proposed`, `under_review`, `accepted`, `rejected`, `deferred`, `human_required`, `review_required`, `superseded` |
| artifact `status` | `proposed`, `implemented_not_verified`, `verified_for_scope`, `changes_required`, `revalidation_required`, `archived` |
| validation `result` | `passed`, `failed`, `blocked`, `not_run` |
| validation `applicability` | `current`, `historical`, `invalidated`, `unestablished` |
| link `rel` | `supports`, `contradicts`, `implements`, `verifies`, `derived_from`, `supersedes`, `depends_on` |
| `depends_on` `impact_policy` | `review`, `invalidate_applicability`, `none` |
| review `result` | `ready`, `revise`, `blocked`, `escalate`, `pass`, `fail` |
| review `independence` | `verified`, `unverified`, `conflict` |

## Rules

1. **Receipts are the only execution evidence.** A `receipt` line records the command, the working directory, the commit or content hash, start and end times, the exit status, and paths to `receipts/<id>.out` and `.err`. A timeout is recorded as `timed_out: true` with no exit status. A validation with result `passed` or `failed` must cite a receipt. Without one, its result is `not_run`.
2. **Results are history; applicability is the present.** When the tested artifact, the test, the data or the configuration changes, add a line that sets the old validation's applicability to `historical` or `invalidated`. Never change its result.
3. **A contradiction is a contest.** New contrary evidence adds a `contradicts` link and moves the old claim to `contested`, with a review task. Only a recorded review moves it on to `supported`, `unsupported` or `superseded`.
4. **Dependencies carry a policy.** Only `depends_on` links have an `impact_policy`. To find what a change affects, walk the `depends_on` links backwards from the changed version. List separately any record that plausibly depends on the change but has no link, so the traversal is not mistaken for complete.
5. **Protected requirements survive failed implementations.** A failing implementation queues the requirement for review. It never retires it. Only an approval from the user, bound to the new version, can supersede it.
6. **Approvals bind to versions.** An `approval` line records who granted it (`human-owner` from the user's own message, or a `delegation` the user set up), its scope, the exact version hash, and its expiry. An approval for version 1 does not cover version 2.
7. **Scope only narrows.** A summary, report or example inherits the most restrictive access scope among its inputs.
8. **The report is derived.** Regenerate `report.md` from the ledger whenever it is shown. Editing it changes nothing.
