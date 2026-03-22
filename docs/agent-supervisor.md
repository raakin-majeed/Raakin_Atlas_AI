# Technical Documentation: ATLAS AI Academic Supervisor

## 1. Agent Definition
The ATLAS AI Academic Supervisor is an autonomous cognitive agent designed for institutional oversight. Unlike standard rule-based systems, this agent utilizes Large Language Model (LLM) reasoning to evaluate student success trajectories and execute precision academic interventions.

## 2. Core Intelligence
The agent intelligence is powered by the Gemini 3 Flash model. This allows the Supervisor to move beyond simple threshold triggers and perform Contextual Pattern Recognition.

* Longitudinal Analysis: The agent compares current data against historical trends in the atlas_final_test_mix dataset to detect velocity changes in student performance.
* Linguistic Synthesis: It transforms raw data points into professional, empathetic, and authoritative recovery plans, maintaining the formal tone required by a university supervisor.

## 3. Operational Logic and Decision Matrix
The agent operates on a tripartite decision-making framework to classify student risk:

| Risk Tier | Input Indicators | Agent Action |
| :--- | :--- | :--- |
| Stable | Consistent attendance and stable grades | No action; continues silent monitoring |
| Monitoring | Minor fluctuations in activity or isolated grade drops | Generates a Standard Observation log and drafts a check-in |
| Critical | Significant downward trend and high absenteeism | Triggers a Supervisor Directive and mandates a recovery plan |

## 4. Primary Capabilities

### Data Reasoning
The agent functions as an Intelligent Knowledge Studio. It ingests structured datasets and builds a temporary cognitive map of the student body. It identifies correlations between disparate variables, such as a drop in LMS activity predicting a future drop in exam scores.

### Autonomous Communication
Once a risk is identified, the agent assumes the role of a communicator.
* Identity Assumption: It drafts correspondence from the perspective of an Academic Supervisor.
* Security Compliance: It strictly enforces domain-locking, ensuring communications are only sent to authorized university domains.

### Persistent Audit Logging
Every decision made by the agent is committed to a PostgreSQL-backed audit trail. This ensures the agent reasoning can be reviewed by human faculty at any time, providing full transparency.

## 5. Agent Workflow
1. Observation: The agent receives a batch of performance data from the atlas_final_test_mix source.
2. Inference: It runs a comparative analysis to find students deviating from established performance baselines.
3. Action: For students flagged as Monitoring or Critical, the agent generates a context-specific recovery strategy.
4. Reporting: The agent updates the system status to LIVE and logs the completion of the intervention cycle.
