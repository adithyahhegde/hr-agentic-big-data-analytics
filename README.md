# HR Agentic Big Data Analytics

A local-first HR analytics workbench for heterogeneous and messy workforce datasets.

## Current product

The application provides an end-to-end analytical workflow:

`CSV upload → data health → canonical HR schema review → feasible-task detection → analytical planning → descriptive analytics → bounded AutoML/model comparison → explainability evidence → bounded insights → provenance/report`

The system automatically profiles uploaded data, evaluates data-quality rules, proposes canonical HR schema mappings with confidence/evidence, blocks unresolved mapping collisions, lets the user confirm mappings, detects feasible analytical objectives, uses a bounded planning agent to rank validated investigations, routes workloads between local and Spark execution policies, computes descriptive analytics, and supports supervised model comparison plus optional bounded AutoML for local classification/regression tasks. It also supports local clustering/anomaly detection and routed Spark execution for supervised ML, clustering, and distributed anomaly screening.

ML execution is deliberately bounded: only confirmed targets are used; identifier-like and constant predictors are excluded; reproducible evaluation is used; task-appropriate metrics are reported; categorical preprocessing is bounded; and explainability evidence is surfaced with explicit limitations. The AutoML path uses the optional FLAML extra with an explicit time budget and a constrained learner set. The system does not make automated employment decisions.

The agentic layer is a constrained evidence synthesizer rather than an unrestricted data-science chatbot. It consumes structured analytical outputs, generates conservative investigation actions, records provenance, and never receives unrestricted raw HR records. The optional local LLM is not required for the core workflow.

## Big-data execution

Workloads are routed using explicit engineering thresholds for row count, estimated bytes, column count, file count, or an explicit distributed requirement. Small workloads use the lightweight local path; routed large workloads use Spark. Spark execution is currently local-distributed (`local[*]`) and is intended as a reproducible scalable-processing path, not a claim that every dataset is universally "Big Data".

## Persistence and reproducibility

Uploaded datasets are stored under the configured local data directory (`HR_ANALYTICS_DATA_DIR`, default `data/`). SQLite stores dataset manifests, profiling state, confirmed schema mappings, and analytical run history. Dataset fingerprints, schema versions, execution engines, and run provenance are retained so the workflow can be recovered after process restart when the configured data directory persists.

Runtime data is excluded from Git by `.gitignore`.

## Run locally

Create an environment and install the project with the desired extras, then run:

`uvicorn app.main:app --reload`

Open `http://127.0.0.1:8000`.

- Base install: upload, profiling, schema, routing and deterministic analytics foundation.
- `ml` extra: local heterogeneous supervised/unsupervised ML.
- `automl` extra: bounded FLAML model/feature preprocessing search for local supervised objectives; configure `HR_ANALYTICS_AUTOML_TIME_BUDGET_SECONDS` from 1–600 seconds.
- `bigdata` extra: PySpark-backed large-data analytics and Spark ML.
- `dev` extra: test tooling.

The benchmark harness can compare local and Spark descriptive execution when PySpark is installed:

`python scripts/benchmark.py --rows 100000 --seed 42`

## Research/evaluation status

The project deliberately makes **no broad novelty or "first" claim**. Existing agentic data-science, enterprise analytics, workforce analytics and HR decision-support systems overlap with the broad concept. The research direction is narrower: evaluate whether confidence-aware HR schema interpretation, objective-feasibility gates, bounded evidence-led planning/synthesis, automated model search, scalable routing, and provenance improve reliability on heterogeneous HR datasets.

The repository includes deterministic benchmark generation plus regression tests for routing, data quality, schema interpretation, persistence/provenance, bounded synthesis, report privacy, bounded AutoML guardrails, and benchmark behavior. CI installs the lightweight `dev,ml,automl` environment; Spark remains an optional dependency and is handled explicitly by the benchmark harness.

Formal comparative robustness/scalability results should only be reported after the benchmark protocol has been executed and recorded. Do not infer research performance from unit-test counts.

## Product boundary

This is a research-grade implementation foundation, not a validated production HR decision system. Important limitations include:

- Spark uses local distributed execution unless deployed against an external Spark cluster.
- Distributed anomaly detection is a scalable z-score screening method, not an exact distributed equivalent of every local detector.
- Spark explainability is currently more limited than local feature-importance/permutation evidence.
- The current AutoML implementation is intentionally bounded to local supervised objectives; Spark AutoML and unsupervised AutoML remain separate engineering tracks.
- Statistical/predictive evidence is associative and does not establish causality.
- Recommendations require human review and must not be used as automated hiring, firing, promotion, or compensation decisions.
- The current workflow is primarily CSV-based and single-application/local-storage oriented.

See `docs/MVP_SPEC.md`, `docs/API_CONTRACTS.md`, `docs/AGENT_ENGINE.md`, `docs/IMPLEMENTATION.md`, `docs/RESEARCH_GAP.md`, and `docs/EVALUATION_PROTOCOL.md` for contracts, architecture, research positioning, and evaluation methodology.
