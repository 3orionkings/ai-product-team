---
name: aipt-method-outcome-and-value-analysis
description: Outcome hypothesis, value analysis, option comparison, doing nothing, non-AI alternative, baseline, association versus effect, denominators, confounders, reporting changes, complaints versus harms. Use before building to state the outcome that matters as a falsifiable hypothesis and compare options, including doing nothing and non-AI options, on one fixed set of criteria; use after release to judge whether observed outcomes show an effect rather than an association. Checks denominators and reporting changes, and never reads fewer complaints as fewer harms.
license: See LICENSE_PENDING.md in the repository root.
metadata:
  aipt_skill_id: "S22"
  aipt_provenance: "newly_authored"
  aipt_version: "0.1.0"
---

# Outcome and value analysis

## Purpose

State, before anything is built, which change in the situation of users or the organization would make the work worth doing, in a form that observation can refute; compare every serious option against that statement on the same criteria; and, after exposure, judge whether the observed data shows the stated effect, an association only, or nothing distinguishable. The skill serves two moments, planning and judging, and the judging moment is bound by what was written in the planning moment.

Terms used here. An *outcome* is a change in the situation of users or the organization that can be observed without reading the feature's own output: tickets resolved on first reply, reopen rate, time to resolution. An *output* is what the feature produces: drafts, suggestions, tokens. A *falsifiable hypothesis* names population, metric, baseline, direction, magnitude, window and measurement method, and the observation that would refute it. An *association* is a change observed alongside the exposure; an *effect* is a change that a comparison design attributes to the exposure.

## Use when

- An opportunity is assessed and the proposed AI intervention must be compared with simpler alternatives and with doing nothing on the same outcome criteria (W01 "Compare"; prioritization and product direction reviews).
- An evaluation is being planned and the team must say which outcome the task metrics are a proxy for, and how far the proxy sits from the outcome.
- Observed data from a rollout stage or from production exists and someone asks whether the feature worked.
- A failure investigation or an optimization claims a change in value, and the claim must be stated and tested as an outcome rather than as an output count.
- A cost model needs the definition of a completed task for its denominator; this skill supplies the outcome and acceptance reference that `aipt-method-cost-and-latency-analysis` prices.

## Do not use when

- The question is what the work costs or how long users wait. Use `aipt-method-cost-and-latency-analysis`; this skill consumes its cost per completed task as one criterion.
- The task is to write acceptance checks for requirements. Use `aipt-method-requirements-and-acceptance`; the outcome hypothesis from here is an input to those checks, not a replacement for them.
- Task metrics, slices, thresholds and baselines for an evaluation must be frozen. Use `aipt-method-evaluation-planning`; this skill names the outcome the metrics should track, that skill freezes the protocol.
- Two parties contest which option the evidence supports. Prepare the comparison here and hand the ruling to `aipt-method-evidentiary-adjudication`.
- The request is to argue for one alternative as strongly as possible. Use `aipt-method-adversarial-challenge` from a separate seat; this skill compares from one seat and stays even-handed.

## Required inputs

| Input | Record kind | If missing |
|---|---|---|
| Problem statement and objective, with who is affected | `source` or `requirement` | Return `needs_input`; an outcome cannot be named for an unstated problem |
| Candidate options, including the current workflow (doing nothing) and at least one non-AI option | `proposal` | Add the missing rows yourself, labeled `added_by_analysis`, and say so in `findings` |
| Existing outcome definitions or success claims | `requirement`, `claim` | Draft the outcome as a `proposed` requirement and request owner confirmation |
| Baseline outcome data: levels, denominators, measurement method, period | `source` | Mark the baseline `unknown`; the hypothesis still states metric and magnitude, with a request for the baseline |
| Evaluation results showing what quality was demonstrated and on which cases | `validation` | Treat the AI option's quality as unknown in the comparison |
| Rollout context for judging: cohorts, dates, concurrent changes, reporting changes | `artifact` (rollout plan), `source` (change log) | Judge as `not_distinguishable` and name the missing context |
| Constraints and failure consequences, including protected requirements | `requirement`, `decision` | Request them; the harm floor cannot be set without them |

## Method

Planning, before build or release:

1. Name the outcome. Write who changes, what about their situation changes, how it is measured and over what window. Separate it from outputs and from leading proxies; for each proxy kept, state the known gap between proxy and outcome.
2. Write the hypothesis in one falsifiable sentence: "For <population>, <option> moves <metric> from <baseline> by at least <magnitude> within <window>, measured by <method>; refuted if <observation>." Add the harm floor as a second sentence: which metric must not worsen by more than how much, drawn from protected requirements.
3. List the options. Keep the proposed AI option, add at least one non-AI option (rules, templates, routing, staffing or process change) and the current workflow continued as doing nothing. Describe mechanically what each option changes. Give doing nothing its real trajectory, including planned changes, rather than a frozen present.
4. Fix the criteria once, before filling any cell: expected outcome effect, harm floor, cost per completed task (from `aipt-method-cost-and-latency-analysis`), time to first observable result, reversibility, operational burden (from `aipt-method-rollout-and-operations`), evidence available today. Score every option on every criterion; add or drop no criterion after a value has been seen.
5. Fill the comparison with typed cells: fact, observation or hypothesis with an `evidence_ref`, or `unknown`. A single anecdote fills no cell; record its count and ask for the data. Rank nothing until all cells are filled or marked.
6. Name the discriminating test: the cheapest observation that would move the choice between the top two options, with the sample it needs. Hand it to `aipt-method-evaluation-planning` to freeze the protocol.

Judging, after exposure:

7. Reconstruct the exposure: which cohort saw what, from when, alongside which other changes (release notes, staffing, policy, pricing, season) and which reporting changes (new form, new category, redefined field, moved channel). Record each as an observation with its `source`.
8. Check denominators for every metric: write numerator and denominator with counts, confirm that the population and its mix did not shift, and recompute rates on consistent denominators. Report counts beside every rate.
9. Decide what the design can support. A pre/post comparison on one population supports association only. Staggered or randomized cohorts with a concurrent comparison group can support an effect. List the confounders the design does not remove and classify the result as `association`, `effect_supported` or `not_distinguishable`.
10. Slice the result by the populations that protected requirements or the hypothesis name (workspace, ticket type, customer segment). An aggregate gain with a harmed slice fails the harm floor; report each slice with its counts rather than the average alone.
11. Run the harm check separately from the complaint check. Complaints are reports, filtered by channel, lag and willingness to report; harms are outcomes such as wrong refunds issued, reopened tickets, escalations, audit findings or private data exposed. Ask whether the reporting channel changed and whether the harm proxies moved, and report both series side by side.
12. Judge the planning-moment hypothesis exactly as written: `supported`, `refuted` or `not_distinguishable`, with the magnitude observed, the uncertainty and the confounders. Then name the next test that would raise the classification.
13. Write the artifacts, fill the envelope and propose `depends_on` links from the analysis to the hypothesis, the baseline and the exposure sources.

## Output contract

Artifacts:

- `outcome-hypothesis.json`: `outcome` (population, metric, measurement, window); `hypothesis` (baseline, direction, magnitude, refuted_if); `harm_floor` (metric, limit, requirement_ref); `proxies[]` (name, gap_to_outcome); `discriminating_test`; `claim_type` fixed to `hypothesis`.
- `opportunity-comparison.md` (planning), headings in order: Outcome and hypothesis; Options; Criteria (fixed before scoring); Comparison table (one row per option, one column per criterion, every cell typed); Unknowns; Discriminating test; Recommendation or next-test request.
- `outcome-analysis.md` (judging), headings in order: Hypothesis as pre-registered; Exposure and concurrent changes; Denominators; Slices; Design and confounders; Harms versus complaints; Judgment; Next test.

Envelope fields this skill always fills: `findings` (the hypothesis, each comparison row, the judgment classification); `evidence_refs` (baseline, validation, exposure and change-log versions); `artifact_refs`; `uncertainties` (unknown baseline, unmeasured confounders, thin cohorts, proxy gaps); `requested_followups` (the discriminating or next test, missing denominators); `proposed_links` (`depends_on` edges with `impact_policy: review`); `scope_violations` when the request asked to assert demand, value or safety the sources do not contain.

## Evidence and uncertainty rules

- Type every cell and every judgment as fact, observation, hypothesis or unknown, with lineage as `aipt-method-evidence-and-lineage` specifies.
- An effect claim requires a comparison design that the analysis names; without one the strongest admissible statement is association, and the text says so.
- A rate is reported with its numerator and denominator counts and its period; a rate without counts is reported as `unknown` until the counts arrive.
- A change in how outcomes are reported (channel, form, definition, category) is recorded as an event with a date before any series crossing it is interpreted.
- Fewer complaints is evidence about reporting until harm proxies are checked; the analysis states what the harm proxies show and judges harm on them.
- One anecdote, one request or one team's recommendation establishes demand for nothing; record the count and request the evidence.
- The hypothesis judged is the one recorded before exposure; any rewording after data is seen is a `decision` with rationale, and the judgment on the original is also reported.
- A change seen in the first days of exposure is provisional: attention, novelty and selection of early users move early readings. Label it provisional until the window named in the hypothesis has elapsed, and say which window remains.

## Guardrails

- Do not count outputs as outcomes. Instead measure the situation of users or the organization, and list the gap between any proxy and that outcome.
- Do not drop doing nothing or the non-AI option, and do not compare options on different criteria. Instead keep one criteria set fixed before scoring and give doing nothing its real trajectory.
- Do not infer demand or value from a single complaint or request. Instead record the count, mark the cell `unknown` and name the data that would fill it.
- Do not call a pre/post change an effect. Instead label it association, list the confounders and name the comparison design that would support an effect.
- Do not equate fewer complaints with fewer harms. Instead report harm proxies and reporting changes beside the complaint series, and judge the harm floor on the harm proxies.
- Do not move the hypothesis after seeing results. Instead judge the pre-registered statement and record any new hypothesis as a separate `decision` for the next test.
- Do not rule on a contested comparison. Instead deliver the typed comparison and hand the ruling to `aipt-method-evidentiary-adjudication`.

## Success criteria

- The outcome is observable independently of the feature's output, and the hypothesis names population, metric, baseline, magnitude, window, method and the refuting observation.
- The comparison contains doing nothing and at least one non-AI option, scored on the same criteria as the AI option, with every cell typed or marked unknown.
- A discriminating test is named with its sample and handed to evaluation planning.
- In judging mode, every rate shows counts, concurrent and reporting changes are listed, the design is classified and the confounders are named.
- Complaint series and harm proxies are reported separately, and the harm floor is judged on the harm proxies.
- The judgment uses the pre-registered hypothesis and ends with a next test.

## Example

Reply Assist at Larkspur Support: a human agent reviews and sends every draft. The planning-moment hypothesis, then a judging-moment excerpt after stage 2 in `ws-alpha`.

```json
{
  "artifact": "outcome-hypothesis.json",
  "outcome": {"population": "tickets opened in ws-alpha", "metric": "median minutes from ticket open to first substantive agent reply", "measurement": "ticket timestamps in source:helpdesk-export@v4", "window": "4 weeks per stage"},
  "hypothesis": {"baseline": 41, "direction": "decrease", "magnitude": 8, "refuted_if": "median decrease below 4 minutes with n >= 1000 tickets"},
  "harm_floor": {"metric": "7-day reopen rate", "limit": "no increase above baseline 11.0% + 1.5 points", "requirement_ref": "requirement:REQ-031@v2"},
  "proxies": [{"name": "agent accepts draft without edit", "gap_to_outcome": "acceptance does not show that the customer was helped"}],
  "discriminating_test": "staggered start: half of ws-alpha teams enabled two weeks later as comparison; n >= 1000 tickets per arm",
  "claim_type": "hypothesis"
}
```

```markdown
### Comparison table (criteria fixed 2026-08-14)
| Option | Expected effect on first-reply time | Harm floor | Cost per completed task | Reversibility | Evidence today |
|---|---|---|---|---|---|
| Reply Assist draft | hypothesis: -8 min | hypothesis: reopen flat | 0.84 lower bound (cost-model@v1) | flag off, minutes | validation: accept-check@v2 on 320 synthetic tickets |
| Template library (non-AI) | hypothesis: -5 min | unknown | unknown | remove templates | source: two agent interviews |
| Do nothing | observation: +2 min trend over 6 months | observation: 11.0% | known from staffing source | n/a | source:helpdesk-export@v4 |

### Judgment (stage 2, 2026-10-12)
Complaints about reply quality fell 30% (61 to 43). The complaint form moved behind login on 2026-09-20 (change-log CL-118).
Reopen rate: 11.0% (412/3745) before, 11.4% (389/3412) during; within the floor.
Design: pre/post on one population; staffing changed 2026-09-15. Classification: not_distinguishable for first-reply time; harm floor held on reopen counts; the complaint drop is reporting-confounded and says nothing about harms.
Next test: the staggered-start comparison named in the hypothesis.
```
