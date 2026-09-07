# Agent and Orchestration Engine

## Purpose

The agent layer coordinates and synthesizes validated analytical tools; deterministic services calculate metrics and fit models. The synthesis layer does not invent measurements. Its inputs are structured analytical outputs and capability information, not unrestricted HR records.

## Current execution model

`UPLOAD → PROFILE → SCHEMA REVIEW → FEASIBILITY → ANALYTICS/ML → EVIDENCE VALIDATION → BOUNDED SYNTHESIS → REPORT`

The current implementation is a bounded decision-support workflow rather than a fully autonomous multi-step planner. This distinction is intentional: deterministic gates remain authoritative, while language generation is constrained to verified outputs.

## Tool policy

Tools are registered, typed operations including profiling, data-quality validation, schema mapping, feasibility detection, descriptive analytics, classification, regression, clustering, anomaly detection, Spark execution, model evaluation, explainability, insight synthesis, and reporting.

Tool outputs are structured and validated before synthesis. The agent cannot alter deterministic results, execute arbitrary user-generated code, or directly access unrestricted employee rows.

## Planning and safeguards

Before analytical execution, the workflow requires a stored dataset, accepted schema mappings, and a feasible objective. Workload routing selects the local or Spark path from explicit workload characteristics. Model execution uses confirmed targets/features, excludes identifier-like/constant predictors, applies bounded evaluation, and reports task-appropriate metrics.

The synthesis service produces reversible investigation actions rather than employment decisions. Predictive feature importance is described as associative evidence; clustering/anomaly signals are explicitly treated as statistical review signals. Data-quality warnings result in remediation-oriented recommendations rather than employee-level conclusions.

## Provenance

Run records retain dataset ID and fingerprint, operation, execution engine, status, timestamp, and a structured provenance object. Analytical results also carry schema version where applicable. Dataset manifests persist the source metadata, profile, and confirmed mappings. Report generation exposes privacy guarantees that raw source records and employee-level identifiers are not included in the exported report payload.

## Failure and recovery policy

Failures should be explicit rather than silently converted into fabricated results. Validation failures are surfaced to the caller; transient/runtime failures use safe bounded handling; run history can record failed operations with error type and recoverability metadata. The application should not retry schema or data-quality prerequisite failures indefinitely.

## Privacy boundary

Raw HR records are used by deterministic analytical services only as necessary to compute aggregate results. The synthesis layer receives analytical evidence rather than the raw dataset. Exported reports are aggregate/evidence oriented and explicitly mark raw-record inclusion as false.

## Current implementation boundary

The implemented agentic layer is a **bounded evidence synthesizer**, not an autonomous general-purpose data-science agent. Multi-step planning/execution state, richer retry orchestration, human approval workflows for consequential actions, and evidence-object-level recommendation citations remain future research/product layers.