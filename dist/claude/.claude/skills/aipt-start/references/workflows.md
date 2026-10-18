# AI Product Team: workflows

## W01 · Should we add AI to this workflow?

Entry skill `aipt-assess-opportunity` · manager `discovery-manager` · minimum risk R0

Inputs: Problem; Current workflow; Users; Constraints; Existing alternatives.

Outputs: Opportunity brief; Option comparison; Decision or next-test recommendation.

Stages: context-analyst → discovery-interviewer → opportunity-analyst → discovery-manager → decision-authority (if consequential_or_disputed).

## W02 · Turn these documents into a feature proposal.

Entry skill `aipt-shape-feature` · manager `experience-manager` · minimum risk R0

Inputs: Authorized corpus; Problem; Answers to material questions.

Outputs: Source-linked requirements; Journey; Acceptance map; Unresolved decisions.

Stages: context-analyst → discovery-interviewer → journey-designer → requirements-writer → acceptance-designer → experience-manager.

## W03 · Design how this AI feature should work.

Entry skill `aipt-design-system` · manager `systems-manager` · minimum risk R1

Inputs: Accepted requirements; Data and tool constraints; Repository context.

Outputs: Architecture; Component contracts; Permissions; Failure and evaluation plan.

Stages: workflow-architect → tool-integration-designer → safety-boundary-designer → retrieval-designer (if requires_retrieval) → systems-manager.

## W04 · Build a bounded version we can test.

Entry skill `aipt-build-prototype` · manager `engineering-manager` · minimum risk R1

Inputs: Accepted scope; Architecture; Target repository; Write authorization.

Outputs: Implemented prototype; Observed test receipts; Independent audit; Handoff.

Stages: repository-mapper → implementation-planner → prototype-engineer → test-engineer → engineering-manager → independent-auditor → workflow-orchestrator.

## W05 · Evaluate this feature against its actual task.

Entry skill `aipt-evaluate-feature` · manager `evaluation-manager` · minimum risk R1

Inputs: Task cases; Expected behaviors; Candidate configurations; Budget.

Outputs: Evaluation plan; Versioned dataset; Results by failure slice; Review.

Stages: evaluation-designer → dataset-curator → evaluation-runner → failure-analyst → evaluation-manager.

## W06 · Find out why this feature is failing.

Entry skill `aipt-investigate-failure` · manager `evaluation-manager` · minimum risk R0

Inputs: Failure reports; Authorized traces; Recent changes; Outcome definitions.

Outputs: Validated symptom; Hypotheses; Discriminating tests; Repair recommendation.

Stages: context-analyst → failure-analyst → contradiction-analyst → repository-mapper (if evidence_points_to_code) → evaluation-manager.

## W07 · Would another model improve this feature?

Entry skill `aipt-compare-models` · manager `systems-manager` · minimum risk R1

Inputs: Current and candidate models; Frozen cases; Quality, latency and cost limits.

Outputs: Like-for-like comparison; Uncertainty; Migration or retention recommendation.

Stages: model-selection-analyst → evaluation-designer → evaluation-runner → cost-analyst → latency-analyst → systems-manager.

## W08 · Reduce cost or waiting without losing required quality.

Entry skill `aipt-optimize-cost-latency` · manager `operations-manager` · minimum risk R0

Inputs: Measured usage and traces; Rates; Outcome floor; Workload slices.

Outputs: Bottleneck and cost model; Candidate changes; Quality-preserving experiment plan.

Stages: cost-analyst → latency-analyst → workflow-architect (if missing_current_artifact) → evaluation-designer (if missing_current_artifact) → operations-manager.

## W09 · Is this feature ready for the proposed release?

Entry skill `aipt-review-release` · manager `audit-manager` · minimum risk R2

Inputs: Frozen build; Acceptance map; Real results; Proposed rollout scope.

Outputs: Pass/fail/blocked release review; Unresolved risks; Human approval request.

Stages: audit-manager → independent-auditor → security-reviewer → rollout-planner → audit-manager.

## W10 · Something changed. What must we revisit?

Entry skill `aipt-process-change` · manager `audit-manager` · minimum risk R1

Inputs: Old and new source or artifact; Intended changes; Dependency graph.

Outputs: Impact queue; Revised proposal; Targeted work orders; Revalidation results.

Stages: change-impact-analyst → dependency-steward → contradiction-analyst → audit-manager → implementation-planner (if rework_required) → independent-auditor (if revalidation_required).

## W11 · Challenge this proposal and resolve the disagreement.

Entry skill `aipt-resolve-decision` · manager `review-manager` · minimum risk R1

Inputs: Versioned proposal; Options; Criteria; Evidence; Delegation record.

Outputs: Challenge responses; Admissibility and convergence rulings; Decision or escalation.

Stages: review-manager → adversarial-orchestrator → assumption-challenger → alternative-advocate → proposal-owner → evidence-judge (if material_conflict) → convergence-judge → decision-authority → decision-recorder.

## W12 · Use verified outcomes to improve the product or team.

Entry skill `aipt-learn-from-outcomes` · manager `audit-manager` · minimum risk R0

Inputs: Audited runs; Outcomes; Failed approaches; Current versions.

Outputs: Improvement proposal; Test and evaluation plan; Versioned change and rollback path.

Stages: outcome-analyst → learning-steward → change-impact-analyst → evaluation-designer (if improvement_needs_evaluation) → audit-manager.
