# AI Product Team — agent directory

Generated from `registry/agents.json`. Open `index.html` in this folder for a searchable version that works offline.

## Leadership and coordination

Accountable to the human owner.

| # | Agent | Type | What it does | Installed as |
|---|---|---|---|---|
| 01 | **Product Director** | leader | Keeps the teams focused on the customer problem and intended outcome. | `aipt-product-director` |
| 02 | **Engineering Director** | leader | Aligns system design, engineering, evaluation and operations. | `aipt-engineering-director` |
| 03 | **Assurance Director** | leader | Keeps challenge, decision review and audits independent. | `aipt-assurance-director` |
| 04 | **Workflow Orchestrator** | orchestrator | Chooses the workflow and activates only the agents needed. | `aipt-workflow-orchestrator` |

## Discovery and strategy

Director: Product Director.

| # | Agent | Type | What it does | Installed as |
|---|---|---|---|---|
| 05 | **Discovery Manager** | manager | Reviews whether the problem and opportunity are understood. | `aipt-discovery-manager` |
| 06 | **Context Analyst** | specialist | Explains the existing product, constraints and open questions. | `aipt-context-analyst` |
| 07 | **Discovery Interviewer** | specialist | Asks the few questions that change what should be built. | `aipt-discovery-interviewer` |
| 08 | **Customer Researcher** | specialist | Finds customer needs in interviews, requests and observed behavior. | `aipt-customer-researcher` |
| 09 | **Opportunity Analyst** | specialist | Compares the proposed improvement with current alternatives. | `aipt-opportunity-analyst` |
| 10 | **Prioritization Analyst** | specialist | Ranks work by expected value, risk and dependencies. | `aipt-prioritization-analyst` |

## Research and evidence

Director: Product Director.

| # | Agent | Type | What it does | Installed as |
|---|---|---|---|---|
| 11 | **Research Manager** | manager | Reviews whether research actually supports the conclusions. | `aipt-research-manager` |
| 12 | **Source Researcher** | specialist | Finds and reads the sources needed for a decision. | `aipt-source-researcher` |
| 13 | **Evidence Curator** | steward | Organizes evidence with its source, date and limits. | `aipt-evidence-curator` |
| 14 | **Claim Checker** | reviewer | Checks that a source supports the exact claim being made. | `aipt-claim-checker` |
| 15 | **Contradiction Analyst** | specialist | Explains disagreements between documents and observations. | `aipt-contradiction-analyst` |
| 16 | **Evidence Linker** | steward | Connects claims to evidence and records what depends on them. | `aipt-evidence-linker` |

## Product and experience

Director: Product Director.

| # | Agent | Type | What it does | Installed as |
|---|---|---|---|---|
| 17 | **Experience Manager** | manager | Reviews whether the proposed experience serves the user. | `aipt-experience-manager` |
| 18 | **Journey Designer** | specialist | Maps what users do before, during and after the feature. | `aipt-journey-designer` |
| 19 | **Interaction Designer** | specialist | Designs the controls, feedback and correction paths. | `aipt-interaction-designer` |
| 20 | **Accessibility Reviewer** | reviewer | Checks that people can understand and operate the experience. | `aipt-accessibility-reviewer` |
| 21 | **Requirements Writer** | specialist | Turns decisions into clear, testable product requirements. | `aipt-requirements-writer` |
| 22 | **Acceptance Designer** | specialist | Defines what would show that each requirement works. | `aipt-acceptance-designer` |

## AI systems design

Director: Engineering Director.

| # | Agent | Type | What it does | Installed as |
|---|---|---|---|---|
| 23 | **Systems Manager** | manager | Reviews whether the architecture can deliver the intended behavior. | `aipt-systems-manager` |
| 24 | **Workflow Architect** | specialist | Chooses which steps use code, models, agents or people. | `aipt-workflow-architect` |
| 25 | **Model Selection Analyst** | specialist | Chooses model candidates based on the actual task. | `aipt-model-selection-analyst` |
| 26 | **Retrieval Designer** | specialist | Designs how the feature finds the right permitted information. | `aipt-retrieval-designer` |
| 27 | **Tool Integration Designer** | specialist | Defines how the feature calls tools and handles their results. | `aipt-tool-integration-designer` |
| 28 | **Safety Boundary Designer** | specialist | Defines what the feature may do and when it must stop. | `aipt-safety-boundary-designer` |

## Engineering and integration

Director: Engineering Director.

| # | Agent | Type | What it does | Installed as |
|---|---|---|---|---|
| 29 | **Engineering Manager** | manager | Reviews work orders, implementation scope and integration readiness. | `aipt-engineering-manager` |
| 30 | **Repository Mapper** | specialist | Finds the code and commands relevant to the requested change. | `aipt-repository-mapper` |
| 31 | **Implementation Planner** | specialist | Breaks approved work into small, testable changes. | `aipt-implementation-planner` |
| 32 | **Prototype Engineer** | builder | Builds a bounded version of the proposed feature. | `aipt-prototype-engineer` |
| 33 | **Integration Engineer** | builder | Connects components and checks their end-to-end behavior. | `aipt-integration-engineer` |
| 34 | **Refactoring Engineer** | builder | Improves code structure while preserving approved behavior. | `aipt-refactoring-engineer` |

## Evaluation and quality

Director: Engineering Director.

| # | Agent | Type | What it does | Installed as |
|---|---|---|---|---|
| 35 | **Evaluation Manager** | manager | Reviews whether the tests answer the product’s real questions. | `aipt-evaluation-manager` |
| 36 | **Evaluation Designer** | specialist | Defines realistic cases, baselines and pass conditions. | `aipt-evaluation-designer` |
| 37 | **Dataset Curator** | specialist | Builds representative and permissioned test cases. | `aipt-dataset-curator` |
| 38 | **Test Engineer** | specialist | Writes checks for requirements, boundaries and regressions. | `aipt-test-engineer` |
| 39 | **Evaluation Runner** | executor | Runs the selected evaluations and records the actual results. | `aipt-evaluation-runner` |
| 40 | **Failure Analyst** | specialist | Groups failures and investigates what caused them. | `aipt-failure-analyst` |

## Operations and economics

Director: Engineering Director.

| # | Agent | Type | What it does | Installed as |
|---|---|---|---|---|
| 41 | **Operations Manager** | manager | Reviews operating costs, rollout plans and ongoing ownership. | `aipt-operations-manager` |
| 42 | **Cost Analyst** | specialist | Calculates what the feature costs per completed task. | `aipt-cost-analyst` |
| 43 | **Latency Analyst** | specialist | Finds where users wait and how to reduce that delay. | `aipt-latency-analyst` |
| 44 | **Rollout Planner** | specialist | Plans a small release with stop and rollback conditions. | `aipt-rollout-planner` |
| 45 | **Operations Engineer** | builder | Adds monitoring and recovery checks in the approved workspace. | `aipt-operations-engineer` |
| 46 | **Outcome Analyst** | specialist | Checks whether the feature improves the user’s actual outcome. | `aipt-outcome-analyst` |

## Adversarial challenge

Director: Assurance Director.

| # | Agent | Type | What it does | Installed as |
|---|---|---|---|---|
| 47 | **Adversarial Orchestrator** | adversarial orchestrator | Selects the strongest challenges to a consequential proposal. | `aipt-adversarial-orchestrator` |
| 48 | **Assumption Challenger** | challenger | Tests the assumptions that could overturn the proposal. | `aipt-assumption-challenger` |
| 49 | **Alternative Advocate** | challenger | Builds the strongest credible alternative to the preferred option. | `aipt-alternative-advocate` |
| 50 | **Red-Team Tester** | challenger | Tests misuse, prompt injection and unsafe actions in a safe sandbox. | `aipt-red-team-tester` |
| 51 | **Pre-mortem Analyst** | challenger | Works backward from plausible failures before release. | `aipt-pre-mortem-analyst` |
| 52 | **Dissent Recorder** | steward | Preserves unresolved objections and what would resolve them. | `aipt-dissent-recorder` |

## Decision and convergence

Director: Assurance Director.

| # | Agent | Type | What it does | Installed as |
|---|---|---|---|---|
| 53 | **Review Manager** | manager | Prepares a fair decision review and assigns independent judges. | `aipt-review-manager` |
| 54 | **Convergence Judge** | judge | Resolves material disagreements or asks for the evidence still needed. | `aipt-convergence-judge` |
| 55 | **Evidence Judge** | judge | Decides whether the evidence is sufficient for the stated conclusion. | `aipt-evidence-judge` |
| 56 | **Decision Authority** | decision maker | Accepts only decisions within the human owner’s delegated limits. | `aipt-decision-authority` |
| 57 | **Decision Recorder** | steward | Records what was decided, why, by whom and when to revisit it. | `aipt-decision-recorder` |
| 58 | **Dependency Steward** | steward | Tracks which requirements, code and checks depend on each decision. | `aipt-dependency-steward` |

## Assurance and improvement

Director: Assurance Director.

| # | Agent | Type | What it does | Installed as |
|---|---|---|---|---|
| 59 | **Audit Manager** | manager | Assigns independent audits and checks that findings are resolved. | `aipt-audit-manager` |
| 60 | **Independent Auditor** | auditor | Rechecks whether the delivered work meets the accepted requirements. | `aipt-independent-auditor` |
| 61 | **Security Reviewer** | reviewer | Reviews permissions, trust boundaries and exposure to attacks. | `aipt-security-reviewer` |
| 62 | **Privacy Reviewer** | reviewer | Reviews what data is collected, shared, retained and removed. | `aipt-privacy-reviewer` |
| 63 | **Change Impact Analyst** | specialist | Finds what must be reconsidered after a source, decision or build changes. | `aipt-change-impact-analyst` |
| 64 | **Learning Steward** | steward | Turns verified outcomes into proposed improvements to skills and workflows. | `aipt-learning-steward` |
