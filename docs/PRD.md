# Product Requirements Document

## Working title
Agentic AI for Autonomous Big Data Analytics & Decision Support in Human Resource Management

## Status
Draft — pre-implementation

## Problem
HR data is often fragmented across employee, attendance, performance, compensation, recruitment, training, and other sources. Conventional analytics workflows require an analyst to understand schemas, select an analytical method, prepare data, train/evaluate models, interpret results, and translate findings into HR actions.

## Product vision
Build a web-based HR analytics platform that can ingest heterogeneous HR data, understand and standardize its schema, identify analytical objectives supported by the available data, orchestrate appropriate Big Data and ML/analytics tools, explain findings, and produce evidence-backed decision-support recommendations.

## Primary users
- HR analysts
- HR managers
- Students/researchers demonstrating autonomous analytics

## Core workflow
1. User uploads or connects HR data.
2. System profiles the data.
3. Semantic schema layer maps source fields to canonical HR concepts with confidence.
4. System determines which analytical objectives are feasible.
5. User selects an objective (initial MVP) or provides a supported objective through a future natural-language interface.
6. Agent creates an execution plan.
7. Data engine processes the workload using the appropriate processing path.
8. ML/statistical tools execute the plan.
9. Evaluation and validation are performed.
10. Explainability tools identify important factors where applicable.
11. Agent converts structured evidence into findings and decision-support recommendations.
12. Results and provenance are persisted.

## MVP objectives
- Ingest CSV HR datasets.
- Profile and validate data.
- Standardize heterogeneous HR column names into a canonical schema.
- Present feasible analytical objectives and allow user selection.
- Support classification, regression, clustering, and anomaly detection.
- Use Spark for scalable data processing and Spark ML where appropriate.
- Evaluate models with task-appropriate metrics.
- Provide SHAP-based explanations for supported predictive models.
- Produce evidence-linked HR decision-support recommendations.
- Persist analysis metadata and results.
- Provide a usable web dashboard.

## Non-goals for MVP
- Fully autonomous employment decisions.
- Automated hiring/firing/promotion decisions.
- Production-scale multi-node cloud infrastructure.
- Guaranteed correctness of semantic mappings.
- Real-time streaming as a mandatory feature.
- Arbitrary natural-language HR questions without a validated analytical plan.

## Safety and governance
The system provides decision support, not final employment decisions. It must surface uncertainty, data limitations, potential bias/leakage, and low-confidence schema mappings. Sensitive HR data must not be sent to external services by default.

## Success criteria
- A new HR dataset can be ingested without manually editing application code.
- Supported analytical objectives are correctly detected as feasible/infeasible with reasons.
- Schema mappings expose confidence and allow correction.
- Large-data paths can execute through Spark without unnecessarily collecting the full dataset into local Python memory.
- ML results include appropriate validation metrics and limitations.
- Recommendations are traceable to computed evidence.
- Documentation remains synchronized with implementation.

## Research positioning
This document does not claim that the overall concept is novel. Existing agentic data-science and agentic HR systems must be systematically reviewed before the research contribution is finalized. See `RESEARCH_GAP.md`.
