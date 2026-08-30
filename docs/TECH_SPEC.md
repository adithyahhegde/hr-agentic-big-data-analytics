# Technical Specification

## Architecture principle
Use a modular, tool-driven architecture. The application agent orchestrates deterministic data/ML tools; it should not perform numerical computation by language-model reasoning.

The technical architecture must preserve the project's identity as an **end-to-end autonomous HR Big Data analytics and decision-support system**. Individual components such as schema interpretation, objective discovery, Spark, ML, SHAP, or the LLM are supporting mechanisms, not standalone research products.

## Proposed stack
- Frontend: a static HTML/CSS/JavaScript intake foundation; React + Vite remains a future option once the workflow needs client-side state and richer visualizations
- Backend API: Python + FastAPI
- Data processing: PySpark; Pandas for small-data paths
- Storage format: Parquet for internal analytical datasets where practical
- ML: Spark ML for scalable supported algorithms; scikit-learn/XGBoost for appropriate local workflows
- Explainability: SHAP for supported predictive models
- Agent orchestration: Python-based agent layer; framework choice remains open pending evaluation
- Local LLM: Ollama, optional and local-first
- Database: PostgreSQL as target; SQLite may be used for early development
- Version control: Git/GitHub
- UI prototyping: Google Stitch
- Development agents: Antigravity/Jules/Codex as external development tooling, not application runtime dependencies

## Data paths
Small datasets may use Pandas where it is materially simpler. Larger workloads should use Spark DataFrames and avoid unnecessary `collect()` operations. The system should make the processing-path decision based on measured/defined thresholds rather than using Spark merely as a label for Big Data.

## Ingestion
MVP: CSV upload.
Future: REST API source and database connectors.
Future/optional: streaming ingestion.

## Semantic schema layer
Source columns are mapped to canonical HR fields using deterministic normalization and metadata first. Ambiguous cases may invoke a local LLM. Every mapping must expose confidence and validation status; low-confidence mappings require confirmation.

This layer exists to support the end-to-end analytics workflow; it is not the sole research contribution.

## Analytical objective layer
The system should infer which supported HR analytical objectives are feasible from the profiled dataset and explain why an objective is feasible, infeasible, or uncertain. Initial objectives include classification, regression, clustering, and anomaly detection. Objective discovery must be constrained by the actual data, target availability, sample size, data types, temporal structure, and quality checks.

The initial MVP still presents candidate objectives for human selection before execution. Fully autonomous objective execution is a future extension and must not bypass governance checks.

## Agent responsibilities
The application agent is an orchestrator. It may:
- inspect data-profile outputs;
- identify feasible objectives;
- select tools/workflows;
- sequence tool execution;
- handle recoverable failures;
- summarize structured outputs;
- request user confirmation for ambiguous or consequential decisions;
- preserve a reproducible execution plan and provenance.

The agent must not invent computed values or bypass validation.

## Execution and validation
Every analytical run should produce a structured execution record containing:
- dataset/profile version;
- schema mapping version;
- selected objective;
- planned tools and steps;
- actual tools/steps executed;
- model/configuration;
- evaluation metrics;
- data-quality warnings;
- explainability outputs where applicable;
- recommendation evidence;
- timestamps/status/errors.

This record supports both reproducibility and research evaluation of the complete autonomous workflow.

## Explainability
SHAP is used for supported predictive models to attribute feature contributions. SHAP is not an LLM and does not generate natural-language reasoning by itself.

## Persistence
Store datasets' metadata, schema mappings, analysis plans, execution metadata, model metadata, metrics, explanation summaries, recommendations, and provenance. Do not store raw sensitive HR data unless explicitly required and authorized.

## Deployment target
Initial target is local development on Windows. Production/cloud deployment is out of MVP scope. The design should keep local execution possible without paid APIs.

## Security
- Keep secrets out of source control.
- Do not transmit HR data to external LLM APIs by default.
- Validate uploaded files and source URLs.
- Restrict file sizes and resource-intensive operations.
- Log provenance without logging sensitive raw records.

## Research constraint
Do not introduce a technical component solely because it sounds novel. Any proposed differentiator must strengthen the end-to-end autonomous HR analytics workflow and have a measurable evaluation plan. The research gap remains provisional until the closest current systems have been inspected in sufficient depth.
