# Technical Specification

## Architecture principle
Use a modular, tool-driven architecture. The agent orchestrates deterministic data/ML tools; it should not perform numerical computation by language-model reasoning.

## Proposed stack
- Frontend: React + Vite
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
Small datasets may use Pandas where it is materially simpler. Larger workloads should use Spark DataFrames and avoid unnecessary `collect()` operations.

## Ingestion
MVP: CSV upload.
Future: REST API source and database connectors.
Future/optional: streaming ingestion.

## Semantic schema layer
Source columns are mapped to canonical HR fields using deterministic normalization and metadata first. Ambiguous cases may invoke a local LLM. Every mapping must expose confidence and validation status; low-confidence mappings require confirmation.

## Analytical engine
Supported families:
- binary/multiclass classification;
- regression;
- clustering;
- anomaly detection;
- forecasting as a future extension.

The system selects task-appropriate evaluation metrics rather than optimizing accuracy universally.

## Agent responsibilities
The application agent is an orchestrator. It may:
- inspect data-profile outputs;
- identify feasible objectives;
- select tools/workflows;
- sequence tool execution;
- handle recoverable failures;
- summarize structured outputs;
- request user confirmation for ambiguous or consequential decisions.

The agent must not invent computed values or bypass validation.

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
