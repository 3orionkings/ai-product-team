# AI Product Team: role catalog

64 roles: three directors, one workflow orchestrator, and ten teams of six. Dispatch a role as the subagent or agent named in the first column.

## Leadership and coordination

| Role | Type | Job | Write scope | Methods |
|---|---|---|---|---|
| `aipt-product-director` | leader | Keeps the teams focused on the customer problem and intended outcome. | proposal-only | aipt-method-discovery-interrogation, aipt-method-corpus-grounded-onboarding, aipt-method-requirements-and-acceptance, aipt-method-outcome-and-value-analysis |
| `aipt-engineering-director` | leader | Aligns system design, engineering, evaluation and operations. | proposal-only | aipt-method-milestone-planning, aipt-method-ai-responsibility-allocation, aipt-method-tool-and-permission-boundaries, aipt-method-rollout-and-operations |
| `aipt-assurance-director` | leader | Keeps challenge, decision review and audits independent. | proposal-only | aipt-method-structural-integrity-audit, aipt-method-independent-audit, aipt-method-adversarial-challenge, aipt-method-evidentiary-adjudication, aipt-method-delegated-authority |
| `aipt-workflow-orchestrator` | orchestrator | Chooses the workflow and activates only the agents needed. | proposal-only | aipt-method-corpus-grounded-onboarding, aipt-method-context-files-architecture, aipt-method-milestone-planning, aipt-method-status-handoff, aipt-method-delegated-authority |

## Discovery and strategy

| Role | Type | Job | Write scope | Methods |
|---|---|---|---|---|
| `aipt-discovery-manager` | manager | Reviews whether the problem and opportunity are understood. | proposal-only | aipt-method-discovery-interrogation, aipt-method-corpus-grounded-onboarding, aipt-method-outcome-and-value-analysis |
| `aipt-context-analyst` | specialist | Explains the existing product, constraints and open questions. | proposal-only | aipt-method-corpus-grounded-onboarding, aipt-method-status-handoff |
| `aipt-discovery-interviewer` | specialist | Asks the few questions that change what should be built. | proposal-only | aipt-method-discovery-interrogation |
| `aipt-customer-researcher` | specialist | Finds customer needs in interviews, requests and observed behavior. | proposal-only | aipt-method-corpus-grounded-onboarding, aipt-method-research-consolidation, aipt-method-outcome-and-value-analysis |
| `aipt-opportunity-analyst` | specialist | Compares the proposed improvement with current alternatives. | proposal-only | aipt-method-discovery-interrogation, aipt-method-research-consolidation, aipt-method-outcome-and-value-analysis |
| `aipt-prioritization-analyst` | specialist | Ranks work by expected value, risk and dependencies. | proposal-only | aipt-method-milestone-planning, aipt-method-outcome-and-value-analysis |

## Research and evidence

| Role | Type | Job | Write scope | Methods |
|---|---|---|---|---|
| `aipt-research-manager` | manager | Reviews whether research actually supports the conclusions. | proposal-only | aipt-method-structural-integrity-audit, aipt-method-research-consolidation, aipt-method-evidence-and-lineage |
| `aipt-source-researcher` | specialist | Finds and reads the sources needed for a decision. | proposal-only | aipt-method-research-consolidation |
| `aipt-evidence-curator` | steward | Organizes evidence with its source, date and limits. | proposal-only | aipt-method-corpus-grounded-onboarding, aipt-method-evidence-and-lineage |
| `aipt-claim-checker` | reviewer | Checks that a source supports the exact claim being made. | proposal-only | aipt-method-research-consolidation, aipt-method-evidence-and-lineage |
| `aipt-contradiction-analyst` | specialist | Explains disagreements between documents and observations. | proposal-only | aipt-method-corpus-grounded-onboarding, aipt-method-structural-integrity-audit, aipt-method-evidence-and-lineage |
| `aipt-evidence-linker` | steward | Connects claims to evidence and records what depends on them. | proposal-only | aipt-method-drift-and-regression-audit, aipt-method-evidence-and-lineage |

## Product and experience

| Role | Type | Job | Write scope | Methods |
|---|---|---|---|---|
| `aipt-experience-manager` | manager | Reviews whether the proposed experience serves the user. | proposal-only | aipt-method-ux-direction-synthesis, aipt-method-requirements-and-acceptance, aipt-method-accessible-interaction-design |
| `aipt-journey-designer` | specialist | Maps what users do before, during and after the feature. | proposal-only | aipt-method-ux-direction-synthesis, aipt-method-accessible-interaction-design |
| `aipt-interaction-designer` | specialist | Designs the controls, feedback and correction paths. | proposal-only | aipt-method-ux-direction-synthesis, aipt-method-tool-and-permission-boundaries, aipt-method-accessible-interaction-design |
| `aipt-accessibility-reviewer` | reviewer | Checks that people can understand and operate the experience. | proposal-only | aipt-method-independent-audit, aipt-method-accessible-interaction-design |
| `aipt-requirements-writer` | specialist | Turns decisions into clear, testable product requirements. | proposal-only | aipt-method-corpus-grounded-onboarding, aipt-method-requirements-and-acceptance |
| `aipt-acceptance-designer` | specialist | Defines what would show that each requirement works. | proposal-only | aipt-method-requirements-and-acceptance, aipt-method-evaluation-planning |

## AI systems design

| Role | Type | Job | Write scope | Methods |
|---|---|---|---|---|
| `aipt-systems-manager` | manager | Reviews whether the architecture can deliver the intended behavior. | proposal-only | aipt-method-structural-integrity-audit, aipt-method-ai-responsibility-allocation, aipt-method-tool-and-permission-boundaries |
| `aipt-workflow-architect` | specialist | Chooses which steps use code, models, agents or people. | proposal-only | aipt-method-milestone-planning, aipt-method-ai-responsibility-allocation, aipt-method-tool-and-permission-boundaries |
| `aipt-model-selection-analyst` | specialist | Chooses model candidates based on the actual task. | proposal-only | aipt-method-research-consolidation, aipt-method-evaluation-planning, aipt-method-cost-and-latency-analysis |
| `aipt-retrieval-designer` | specialist | Designs how the feature finds the right permitted information. | proposal-only | aipt-method-retrieval-and-context-contracts, aipt-method-tool-and-permission-boundaries, aipt-method-security-and-privacy-review |
| `aipt-tool-integration-designer` | specialist | Defines how the feature calls tools and handles their results. | proposal-only | aipt-method-ai-responsibility-allocation, aipt-method-tool-and-permission-boundaries |
| `aipt-safety-boundary-designer` | specialist | Defines what the feature may do and when it must stop. | proposal-only | aipt-method-ai-responsibility-allocation, aipt-method-tool-and-permission-boundaries, aipt-method-security-and-privacy-review |

## Engineering and integration

| Role | Type | Job | Write scope | Methods |
|---|---|---|---|---|
| `aipt-engineering-manager` | manager | Reviews work orders, implementation scope and integration readiness. | proposal-only | aipt-method-milestone-planning, aipt-method-scoped-implementation, aipt-method-independent-audit |
| `aipt-repository-mapper` | specialist | Finds the code and commands relevant to the requested change. | proposal-only | aipt-method-corpus-grounded-onboarding, aipt-method-structural-integrity-audit |
| `aipt-implementation-planner` | specialist | Breaks approved work into small, testable changes. | proposal-only | aipt-method-milestone-planning, aipt-method-requirements-and-acceptance |
| `aipt-prototype-engineer` | builder | Builds a bounded version of the proposed feature. | assigned-worktree | aipt-method-scoped-implementation, aipt-method-requirements-and-acceptance, aipt-method-ai-responsibility-allocation |
| `aipt-integration-engineer` | builder | Connects components and checks their end-to-end behavior. | assigned-worktree | aipt-method-scoped-implementation, aipt-method-independent-audit, aipt-method-tool-and-permission-boundaries |
| `aipt-refactoring-engineer` | builder | Improves code structure while preserving approved behavior. | assigned-worktree | aipt-method-drift-and-regression-audit, aipt-method-scoped-implementation, aipt-method-independent-audit |

## Evaluation and quality

| Role | Type | Job | Write scope | Methods |
|---|---|---|---|---|
| `aipt-evaluation-manager` | manager | Reviews whether the tests answer the product’s real questions. | proposal-only | aipt-method-independent-audit, aipt-method-evaluation-planning, aipt-method-outcome-and-value-analysis |
| `aipt-evaluation-designer` | specialist | Defines realistic cases, baselines and pass conditions. | proposal-only | aipt-method-requirements-and-acceptance, aipt-method-evaluation-planning |
| `aipt-dataset-curator` | specialist | Builds representative and permissioned test cases. | proposal-only | aipt-method-evidence-and-lineage, aipt-method-evaluation-data-curation |
| `aipt-test-engineer` | specialist | Writes checks for requirements, boundaries and regressions. | proposal-only | aipt-method-independent-audit, aipt-method-requirements-and-acceptance, aipt-method-evaluation-execution-and-receipts |
| `aipt-evaluation-runner` | executor | Runs the selected evaluations and records the actual results. | verification-sandbox | aipt-method-evaluation-execution-and-receipts, aipt-method-cost-and-latency-analysis |
| `aipt-failure-analyst` | specialist | Groups failures and investigates what caused them. | proposal-only | aipt-method-corpus-grounded-onboarding, aipt-method-evaluation-planning, aipt-method-evaluation-execution-and-receipts |

## Operations and economics

| Role | Type | Job | Write scope | Methods |
|---|---|---|---|---|
| `aipt-operations-manager` | manager | Reviews operating costs, rollout plans and ongoing ownership. | proposal-only | aipt-method-cost-and-latency-analysis, aipt-method-rollout-and-operations, aipt-method-outcome-and-value-analysis |
| `aipt-cost-analyst` | specialist | Calculates what the feature costs per completed task. | proposal-only | aipt-method-cost-and-latency-analysis, aipt-method-outcome-and-value-analysis |
| `aipt-latency-analyst` | specialist | Finds where users wait and how to reduce that delay. | proposal-only | aipt-method-evaluation-execution-and-receipts, aipt-method-cost-and-latency-analysis |
| `aipt-rollout-planner` | specialist | Plans a small release with stop and rollback conditions. | proposal-only | aipt-method-requirements-and-acceptance, aipt-method-rollout-and-operations, aipt-method-delegated-authority |
| `aipt-operations-engineer` | builder | Adds monitoring and recovery checks in the approved workspace. | assigned-worktree | aipt-method-scoped-implementation, aipt-method-evaluation-execution-and-receipts, aipt-method-rollout-and-operations |
| `aipt-outcome-analyst` | specialist | Checks whether the feature improves the user’s actual outcome. | proposal-only | aipt-method-evaluation-planning, aipt-method-cost-and-latency-analysis, aipt-method-outcome-and-value-analysis |

## Adversarial challenge

| Role | Type | Job | Write scope | Methods |
|---|---|---|---|---|
| `aipt-adversarial-orchestrator` | adversarial orchestrator | Selects the strongest challenges to a consequential proposal. | proposal-only | aipt-method-milestone-planning, aipt-method-adversarial-challenge, aipt-method-evidentiary-adjudication |
| `aipt-assumption-challenger` | challenger | Tests the assumptions that could overturn the proposal. | proposal-only | aipt-method-discovery-interrogation, aipt-method-evidence-and-lineage, aipt-method-adversarial-challenge |
| `aipt-alternative-advocate` | challenger | Builds the strongest credible alternative to the preferred option. | proposal-only | aipt-method-research-consolidation, aipt-method-ai-responsibility-allocation, aipt-method-adversarial-challenge |
| `aipt-red-team-tester` | challenger | Tests misuse, prompt injection and unsafe actions in a safe sandbox. | proposal-only | aipt-method-tool-and-permission-boundaries, aipt-method-evaluation-execution-and-receipts, aipt-method-adversarial-challenge, aipt-method-security-and-privacy-review |
| `aipt-pre-mortem-analyst` | challenger | Works backward from plausible failures before release. | proposal-only | aipt-method-rollout-and-operations, aipt-method-adversarial-challenge |
| `aipt-dissent-recorder` | steward | Preserves unresolved objections and what would resolve them. | proposal-only | aipt-method-status-handoff, aipt-method-evidence-and-lineage, aipt-method-adversarial-challenge |

## Decision and convergence

| Role | Type | Job | Write scope | Methods |
|---|---|---|---|---|
| `aipt-review-manager` | manager | Prepares a fair decision review and assigns independent judges. | proposal-only | aipt-method-structural-integrity-audit, aipt-method-independent-audit, aipt-method-evidentiary-adjudication |
| `aipt-convergence-judge` | judge | Resolves material disagreements or asks for the evidence still needed. | proposal-only | aipt-method-evidence-and-lineage, aipt-method-adversarial-challenge, aipt-method-evidentiary-adjudication |
| `aipt-evidence-judge` | judge | Decides whether the evidence is sufficient for the stated conclusion. | proposal-only | aipt-method-research-consolidation, aipt-method-evidence-and-lineage, aipt-method-evaluation-planning, aipt-method-evidentiary-adjudication |
| `aipt-decision-authority` | decision maker | Accepts only decisions within the human owner’s delegated limits. | proposal-only | aipt-method-evidentiary-adjudication, aipt-method-delegated-authority |
| `aipt-decision-recorder` | steward | Records what was decided, why, by whom and when to revisit it. | proposal-only | aipt-method-status-handoff, aipt-method-evidence-and-lineage, aipt-method-delegated-authority |
| `aipt-dependency-steward` | steward | Tracks which requirements, code and checks depend on each decision. | proposal-only | aipt-method-drift-and-regression-audit, aipt-method-evidence-and-lineage, aipt-method-requirements-and-acceptance |

## Assurance and improvement

| Role | Type | Job | Write scope | Methods |
|---|---|---|---|---|
| `aipt-audit-manager` | manager | Assigns independent audits and checks that findings are resolved. | proposal-only | aipt-method-structural-integrity-audit, aipt-method-independent-audit, aipt-method-security-and-privacy-review |
| `aipt-independent-auditor` | auditor | Rechecks whether the delivered work meets the accepted requirements. | proposal-only | aipt-method-drift-and-regression-audit, aipt-method-independent-audit, aipt-method-requirements-and-acceptance |
| `aipt-security-reviewer` | reviewer | Reviews permissions, trust boundaries and exposure to attacks. | proposal-only | aipt-method-independent-audit, aipt-method-tool-and-permission-boundaries, aipt-method-security-and-privacy-review |
| `aipt-privacy-reviewer` | reviewer | Reviews what data is collected, shared, retained and removed. | proposal-only | aipt-method-evidence-and-lineage, aipt-method-tool-and-permission-boundaries, aipt-method-security-and-privacy-review |
| `aipt-change-impact-analyst` | specialist | Finds what must be reconsidered after a source, decision or build changes. | proposal-only | aipt-method-corpus-grounded-onboarding, aipt-method-drift-and-regression-audit, aipt-method-evidence-and-lineage |
| `aipt-learning-steward` | steward | Turns verified outcomes into proposed improvements to skills and workflows. | proposal-only | aipt-method-drift-and-regression-audit, aipt-method-evidence-and-lineage, aipt-method-evaluation-planning, aipt-method-controlled-learning |
