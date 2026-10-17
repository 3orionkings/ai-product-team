---
name: aipt-method-evaluation-execution-and-receipts
description: Run evaluations, execution receipts, exit status, frozen versions, fixture_replay vs live, timeout vs failure, skipped vs passed, command logs. Use to execute checks or evaluations against frozen plan, dataset and candidate versions and to record for each command the arguments, working directory, snapshot, data and configuration versions, exit status, timeout state, skipped counts and log locations. A receipt proves the command's exit status only. Replay is never labeled live. A command mentioned is not a command run.
license: See LICENSE_PENDING.md in the repository root.
metadata:
  aipt_skill_id: "S19"
  aipt_provenance: "newly_authored"
  aipt_version: "0.1.0"
---

# Evaluation execution and receipts

## Purpose

Execute checks and evaluations so that every result is bound to the exact versions it was run against and every claim of execution is backed by a receipt the controller observed. A receipt is the record of one command: what ran, where, against which snapshot, when, with what exit status, and where its logs are. The receipt proves that the command exited with that status. It does not prove the software is correct, that the test was the right test, or that the result applies to a later version. Those judgments belong to the plan from `aipt-method-evaluation-planning` (S17), the audit in `aipt-method-independent-audit` (S10) and the ruling in `aipt-method-evidentiary-adjudication` (S24). This skill supplies them with evidence that cannot be confused with a description of evidence.

## Use when

- A workflow stage asks for `results.json`, `verification-results.json`, `candidate-results.json` or `revalidation.json` and the plan, dataset and candidate versions are frozen.
- A role must report `observed_checks` and needs each entry to carry a `receipt_id`.
- A test suite, scoring script or candidate configuration must be run inside a verification sandbox with a recorded snapshot.
- Results from a deterministic replay fixture and from live execution exist side by side and must be kept apart.
- A previously passed validation must be rerun because a dependency changed and the old result is now historical.

## Do not use when

- The criteria are not yet frozen. Use `aipt-method-evaluation-planning` (S17); results produced before a freeze cannot be scored against one.
- The request is to decide pass or fail from the results. Use the plan's decision rule through `aipt-method-evidentiary-adjudication` (S24) or the reviewing manager.
- The request is to fix a failing test or implementation. Use `aipt-method-scoped-implementation` (S09) under a separate work order; this skill reports the failure and stops.
- The request is to explain why cases failed. Use the failure-analysis stage; this skill supplies the receipts and logs it needs.
- The request is to model cost or latency from the observations. Use `aipt-method-cost-and-latency-analysis` (S20); this skill records raw timings and counts.

## Required inputs

| Input | Record kind and version | If missing |
|---|---|---|
| Frozen evaluation plan | `artifact` version with `analysis` and `decision_rule` | Return `blocked`; record no result. |
| Dataset manifest | `artifact` version with split hashes and case ids | Return `blocked`; a run without a versioned set cannot be reproduced. |
| Candidate configurations | `proposal` or `artifact` version per candidate, with the configuration hash | Return `needs_input` naming the unbound candidate; never substitute "the current configuration". |
| Target snapshot | commit plus dirty-tree diff hash, or a content manifest of the tested files, test files and configuration | Compute it before the first command; if it cannot be computed, return `blocked`. |
| Budget and timeouts | the work order's `timeout_s`, `max_steps`, run cap | Use the policy default and record that the default was applied. |
| Capabilities and execution mode | the task envelope's `capabilities` with `execution_mode` and `unavailable[]` | Treat every tool as unavailable until the envelope lists it; do not simulate a missing tool. |
| Write scope | `verification-sandbox` or the assigned worktree path | Return `blocked`; receipts and logs need a permitted location. |
| Redaction patterns | the case's data-handling policy version | Apply the package default patterns and record that the case policy was absent. |

## Method

1. Verify the freeze. Fetch the plan, dataset and each candidate by version id, recompute their content hashes and compare with the ids. On mismatch, stop and return `blocked` with both hashes in `findings`.
2. Record the snapshot: the commit id and the hash of the dirty diff, or the manifest hash and path list when there is no repository. Include test files, scoring scripts and configuration, not only product code. The snapshot goes on every receipt from this run.
3. Confirm execution mode from the envelope. Write it into `actual_execution_metadata.execution_mode` before any command runs. If the mode is `fixture_replay`, every result record and the results file carry `"execution_mode": "fixture_replay"`; nothing from this run may be aggregated with live results.
4. Confirm capabilities. If a required command, dataset path or sandbox is unavailable, return `blocked` with the checks listed as `not_run` and the missing capability named. Do not produce a result for a command that could not start.
5. Run each command through the receipt facility: fixed argument vector, no shell, the recorded working directory, the envelope's timeout, an environment allowlist, and the case ids or test ids it covers. Capture stdout and stderr to files. The receipt facility fills `started_at`, `ended_at`, `exit_status`, `timed_out`, `cancelled`, `stdout_path`, `stderr_path` and `observation_source`.
6. Classify each outcome from the receipt and the parsed output, never from expectation: exit `0` with all listed tests passing is `passed`; nonzero exit is `failed`; `timed_out: true` with `exit_status: null` is `timed_out`, not failed; `cancelled` is its own class; tests the runner reports as skipped are `skipped` and are never counted among passed; a command that did not start is `not_run`.
7. Redact. Apply the policy patterns to stored logs and record `redactions_applied`. Logs with redactions remain evidence of exit status and of the redacted text's absence, not of its content.
8. Score and aggregate exactly as the plan's `analysis` section prescribes: the same slices, the same handling of refusals, timeouts, `skipped` and `not_run`, no additional slice, no rerun to replace a worse result. If a rerun occurs for an operational reason, keep every attempt's receipt and report all of them.
9. Record what could not be observed. Where the actual model, host, token counts or latency are not observable from this position, write `"unknown"` in that field; do not copy the requested configuration into the observed field.
10. Emit a `validation` record per check: `method`, `target_refs` (candidate, dataset, plan, snapshot), `receipt_id`, `result` (`passed | failed | blocked | not_run`), `rubric`, `coverage` (which cases, which slices), `applicability: current`. A result other than `not_run` without a `receipt_id` is invalid; do not write it.
11. Compose `results.json`. List every command under `receipts[]`. List every command that was proposed, suggested or described but not executed under `commands_not_run[]` with the reason. The two lists do not overlap. Propose links: `validation --verifies--> candidate`, `validation --depends_on--> plan|dataset|snapshot` with `impact_policy: invalidate_applicability`.

## Output contract

Artifact: `results.json`, one immutable version per run.

Required keys: `run_id`, `execution_mode` (`native | sequential | manual_handoff | fixture_replay`), `observed_by` (`controller | native | agent_reported`), `plan_ref`, `dataset_ref`, `candidates[]` (`ref`, `config_sha256`), `snapshot` (`kind`, `commit`, `dirty_diff_sha256` or `manifest_sha256`, `paths[]`), `receipts[]` (`id`, `command`, `cwd`, `started_at`, `ended_at`, `exit_status`, `timed_out`, `cancelled`, `stdout_path`, `stderr_path`, `test_ids[]`, `redactions_applied`, `proves: "command_exit_status_only"`), `case_results[]` (`case_id`, `candidate_ref`, `outcome`, `receipt_id`, `score_fields`), `counts` (`passed`, `failed`, `skipped`, `timed_out`, `cancelled`, `not_run`), `slice_aggregates[]` (`slice_id`, `metric_id`, `value`, `n`, `insufficient_n`), `unobserved_fields[]`, `commands_not_run[]` (`command`, `reason`), `validation_refs[]`.

Envelope fields this skill always fills:

- `observed_checks`: one entry per executed command, each with `command`, `claimed_exit_status` equal to the receipt's `exit_status`, and `receipt_id`. An entry without a `receipt_id` is a claim, and this skill does not emit one.
- `actual_execution_metadata`: `execution_mode`, `host` when observable, `started_at`, `ended_at`; `native_child_id` only when the controller issued one.
- `findings`: hash mismatches, blocked capabilities, every failed or timed-out check, every `skipped` count, every rerun.
- `evidence_refs`: plan, dataset, candidate and snapshot versions; receipt ids.
- `artifact_refs`: the results version; the validation records.
- `proposed_links`: as in step 11.
- `uncertainties`: unobserved fields, flaky-looking outcomes (differing attempts), scoring that depended on a grader.
- `requested_followups`: failure analysis for failed slices; a scoped work order for any fix; adjudication against the decision rule.
- `scope_violations`: any instruction to edit tests, configuration or thresholds during the run, to label replay as live, or to omit an attempt.

## Evidence and uncertainty rules

- A receipt supports exactly one `fact`: this argument vector, in this directory, against this snapshot, exited with this status at this time. Everything else derived from it is `observation` (parsed output) or `hypothesis` (what the outcome means).
- The observing party is recorded. `controller`-observed receipts outrank `agent_reported` metadata; an agent's statement that a command ran, without a receipt, is recorded as `claimed_only` and carries no weight in a validation.
- A command named in a message, a plan, a script comment or a previous run is not a command run in this run. Only a receipt from this run is.
- A passed validation is bound to its snapshot. When any target, test or configuration version changes, the result stays a historical pass and its applicability becomes unestablished until an explicit review, as `aipt-method-evidence-and-lineage` (S12) describes.
- Requested configuration and observed configuration are different fields. When the observed one is unavailable, the value is `"unknown"`.
- Replay results are evidence about the software's state transitions; they are not evidence about agent or model behavior.

## Guardrails

- Do not report a command as executed because it appears in instructions, a script or a plan. Instead, run it through the receipt facility or list it under `commands_not_run` with the reason.
- Do not label a `fixture_replay` run as `live`, `native` or by any name that omits replay. Instead, carry `execution_mode: fixture_replay` on the run, on every result record and in the summary line.
- Do not count a timeout as a failure or a skipped test as a pass. Instead, keep `timed_out`, `skipped`, `cancelled` and `not_run` as separate classes in `counts` and apply the plan's handling rule to each.
- Do not run the suite repeatedly and report the best attempt. Instead, keep every receipt and report all attempts with their outcomes; let the plan's stopping rule decide what counts.
- Do not edit a test, a fixture, a threshold or a candidate configuration to make a check pass. Instead, record the failure and request a scoped work order through `aipt-method-scoped-implementation` (S09) with review under `aipt-method-requirements-and-acceptance` (S13).
- Do not aggregate replay and live results, or results from different dataset versions, in one slice value. Instead, produce separate `results.json` versions and let the reviewer compare them.
- Do not claim a result proves correctness. Instead, write `proves: "command_exit_status_only"` on the receipt and leave correctness to the plan's scoring and the adjudication.
- Do not store unredacted secrets or private prompts in logs. Instead, apply the redaction patterns, record the count, and note that redacted content is unavailable as evidence.

## Success criteria

- Every entry in `observed_checks` has a `receipt_id`, and every receipt has an argument vector, working directory, snapshot, start and end time, exit status, `timed_out` flag and log paths.
- `counts.passed + failed + skipped + timed_out + cancelled + not_run` equals the number of checks the plan required, and no check appears in both `receipts[]` and `commands_not_run[]`.
- `execution_mode` is present on the run and on every result record, and no replay value appears in any live aggregate.
- Every `validation` with a result other than `not_run` cites a receipt, and every validation's `target_refs` include the snapshot.
- Unobservable fields read `"unknown"` rather than echoing the requested configuration.
- A second runner given the same versions, snapshot and commands can reproduce `counts` or explain the difference from the receipts alone.

## Example

Case: Reply Assist at Larkspur Support. Plan `plan-reply-assist-eval@v1`, dataset `ds-reply-assist@v2`, candidate `config-a@v3`. The sandbox has the scoring script but the live model gateway is not in `capabilities.tools`, so this run is a fixture replay of recorded drafts.

```json
{
  "run_id": "run-0419",
  "execution_mode": "fixture_replay",
  "observed_by": "controller",
  "plan_ref": "plan-reply-assist-eval@v1",
  "dataset_ref": "ds-reply-assist@v2",
  "candidates": [{"ref": "config-a@v3", "config_sha256": "9b02...41cd"}],
  "snapshot": {"kind": "git", "commit": "7d1e4f0", "dirty_diff_sha256": "e3b0...b855", "paths": ["eval/score.py", "eval/cases/", "config/reply-assist.json"]},
  "receipts": [
    {"id": "rcpt-0419-01", "command": ["python", "-I", "eval/score.py", "--cases", "eval/cases/held_out.jsonl", "--drafts", "fixtures/config-a-v3-drafts.jsonl", "--slice", "cross_ws_bait"], "cwd": "/sandbox/run-0419", "started_at": "2026-03-04T10:02:11Z", "ended_at": "2026-03-04T10:02:19Z", "exit_status": 1, "timed_out": false, "cancelled": false, "stdout_path": "receipts/rcpt-0419-01.out", "stderr_path": "receipts/rcpt-0419-01.err", "test_ids": ["cross_ws_bait"], "redactions_applied": 0, "proves": "command_exit_status_only"},
    {"id": "rcpt-0419-02", "command": ["python", "-I", "eval/score.py", "--cases", "eval/cases/held_out.jsonl", "--drafts", "fixtures/config-a-v3-drafts.jsonl", "--slice", "all"], "cwd": "/sandbox/run-0419", "started_at": "2026-03-04T10:02:20Z", "ended_at": "2026-03-04T10:07:20Z", "exit_status": null, "timed_out": true, "cancelled": false, "stdout_path": "receipts/rcpt-0419-02.out", "stderr_path": "receipts/rcpt-0419-02.err", "test_ids": ["all"], "redactions_applied": 0, "proves": "command_exit_status_only"}
  ],
  "counts": {"passed": 8, "failed": 2, "skipped": 0, "timed_out": 54, "cancelled": 0, "not_run": 0},
  "slice_aggregates": [
    {"slice_id": "cross_ws_bait", "metric_id": "m_leak", "value": 0.2, "n": 10, "insufficient_n": true},
    {"slice_id": "all", "metric_id": "m_resolve", "value": null, "n": 0, "insufficient_n": true}
  ],
  "unobserved_fields": ["actual_model", "token_counts", "gateway_latency"],
  "commands_not_run": [{"command": ["python", "-I", "eval/run_live.py", "--config", "config/reply-assist.json"], "reason": "live gateway not in capabilities.tools"}],
  "validation_refs": ["val-0419-bait@v1", "val-0419-all@v1"]
}
```

The summary line reads: "fixture_replay of recorded drafts; m_leak 2/10 on cross_ws_bait, held-out n below plan minimum; the `all` slice timed out at 300 s and has no value; live run not executed." The wrong output reports `m_leak` as a live measurement, counts the timed-out slice as failed, or lists `run_live.py` among the executed checks.
