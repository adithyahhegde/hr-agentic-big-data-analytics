# Agent and Orchestration Engine

## Purpose

The agent layer now has two bounded responsibilities: **analytical planning** and **evidence synthesis**. Deterministic services calculate metrics, establish schema/capabilities, validate feasibility, and fit models. Agents reason only over those verified contracts and cannot invent measurements, targets, fields, or unsupported analytical objectives.

## Current execution model

`UPLOAD → PROFILE → SCHEMA UNDERSTANDING → CAPABILITIES → PLANNING AGENT → PLAN VALIDATION → ANALYTICS/ML → EVIDENCE → SYNTHESIS AGENT → REPORT`

The planning agent receives feasible `TaskCandidate` objects derived from the confirmed canonical schema and dataset-size gates. It ranks investigations, states the analytical question, and proposes bounded investigation steps. The execution layer remains authoritative over which tools/models are valid and how they are evaluated.

## Planning agent

`app/services/planning_agent.py` implements `bounded_analytical_planner_v1`.

- Offline/default mode uses a deterministic policy over validated capabilities, producing reproducible plans without an external AI service.
- When `HR_ANALYTICS_ALLOW_LOCAL_LLM=true`, the planner may ask the configured local Ollama model to rank the same candidate set. The model is strictly constrained to supplied objective IDs and cannot modify target or feature fields.
- Invalid, incomplete, or unavailable local-model responses fall back to the deterministic plan.
- The planner never receives unrestricted employee rows; it sees only structured capability metadata.

This preserves a meaningful agentic decision point without allowing a language model to bypass analytical correctness constraints.

## Tool policy

Tools are registered, typed operations including profiling, data-quality validation, schema mapping, feasibility detection, descriptive analytics, classification, regression, clustering, anomaly detection, Spark execution, model evaluation, explainability, insight synthesis, and reporting.

Tool outputs are structured and validated before synthesis. The planning agent cannot alter deterministic results, execute arbitrary user-generated code, or directly access unrestricted employee rows.

## ML model-selection policy

The ML layer is **bounded model comparison, not full AutoML**. Candidate pools are deterministic and task-specific. Local classification currently compares Logistic Regression, Random Forest, and HistGradientBoosting; local regression compares Ridge, Random Forest, and HistGradientBoosting. Spark classification compares Logistic Regression, Random Forest, and GBT; Spark regression compares Linear Regression, Random Forest, and GBT. The strongest candidate is selected using held-out evaluation (F1 for classification, RMSE for regression). The planning agent selects the analytical objective; it does not invent arbitrary model classes.

## Planning and safeguards

Before analytical execution, the workflow requires a stored dataset, accepted schema mappings, and a feasible objective. Workload routing selects the local or Spark path from explicit workload characteristics. Model execution uses confirmed targets/features, excludes identifier-like predictors, applies bounded evaluation, and reports task-appropriate metrics.

The synthesis service produces reversible investigation actions rather than employment decisions. Predictive feature importance is described as associative evidence; clustering/anomaly signals are explicitly treated as statistical review signals. Data-quality warnings result in remediation-oriented recommendations rather than employee-level conclusions.

## Provenance

Run records retain dataset ID and fingerprint, operation, execution engine, status, timestamp, and a structured provenance object. Analytical results also carry schema version where applicable. Dataset manifests persist the source metadata, profile, and confirmed mappings. The synthesis result also exposes aggregate provenance containing the current dataset fingerprint, evidence count, accepted/rejected ML-run accounting, and an explicit `structured_analytics_only` source scope. This metadata contains no raw HR records and makes the lineage of a generated report inspectable without exposing employee rows.

## Failure and recovery policy

Failures should be explicit rather than silently converted into fabricated results. Validation failures are surfaced to the caller; transient/runtime failures use safe bounded handling; run history can record failed operations with error type and recoverability metadata. The application should not retry schema or data-quality prerequisite failures indefinitely.

## Privacy boundary

Raw HR records are used by deterministic analytical services only as necessary to compute aggregate results. The planning and synthesis layers receive structured metadata/evidence rather than the raw dataset. Exported reports are aggregate/evidence oriented and explicitly mark raw-record inclusion as false.

## Current implementation boundary

The implemented agentic layer now includes **bounded analytical planning plus bounded evidence synthesis**. The evidence synthesizer rejects unsupported objectives and unprovenanced/cross-dataset ML results, caps evidence volume/text, emits evidence-object citations for recommendations, and exposes aggregate provenance. Remaining research/product layers include systematic planner-quality evaluation against human analyst baselines and independent external-cluster scalability measurement.
