# Implementation Plan

## Phase 0 — Research and contracts
- [x] Complete evidence-checked, no-claim research-gap review.
- [x] Freeze MVP requirements in `MVP_SPEC.md`.
- [x] Define agent and API/tool contracts in `AGENT_ENGINE.md` and `API_CONTRACTS.md`.

## Phase 1 — Repository foundation
- [x] Backend skeleton.
- [x] Frontend skeleton.
- [x] Configuration and environment management.
- [x] Basic health checks.

## Phase 2 — Data ingestion and profiling
- [x] CSV upload (request-scoped analysis state).
- [x] File validation.
- [x] Deterministic dataset profiling.
- [x] Data-quality report.

## Phase 3 — Semantic schema layer
- [x] Canonical HR schema.
- [x] Deterministic mappings.
- [x] Confidence scoring.
- [x] Collision/ambiguity blocking at schema acceptance.
- [x] Optional local LLM fallback.

## Phase 4 — Big Data engine
- [x] Spark integration (optional runtime dependency).
- [x] Small/large workload routing.
- [x] Parquet intermediate representation.
- [x] Scalable grouped transformations.
- [x] API-level workload routing contract.
- [x] Streamed dataset execution boundary.
- [ ] Production/durable dataset persistence and lifecycle.
- [ ] Scalability benchmark validation.

## Phase 5 — Analytics/ML engine
- [x] Deterministic task detection.
- [x] Bounded candidate model comparison for classification and regression.
- [x] Train/test evaluation pipeline.
- [x] Task-appropriate metrics and reproducible seed.
- [x] Identifier/constant-feature exclusion and basic imbalance handling.
- [x] K-Means clustering with candidate-k comparison and silhouette evidence on local execution.
- [x] Isolation Forest anomaly detection with aggregate-only output on local execution.
- [x] Native Spark ML path for routed supervised classification/regression.
- [x] Distributed Spark K-Means path for routed clustering workloads.
- [ ] Broader categorical feature preparation in the local engine.
- [ ] Distributed anomaly detection equivalent.

## Phase 6 — Explainability
- [x] Structured feature-importance/permutation evidence for supported local supervised models.
- [x] Model-selection evidence surfaced in the UI.
- [x] Dataset/schema/model provenance fields exposed by the API.
- [x] Spark execution exposes explainability metadata and an explicit limitation when grouped attribution is unavailable.
- [ ] SHAP integration for supported models.
- [ ] Persistent explanation artifacts.

## Phase 7 — Agent orchestration
- [x] Tool/interface contracts documented.
- [x] Bounded evidence-to-action synthesis service.
- [ ] Multi-step planning/execution state.
- [ ] Retry/recovery.
- [ ] Human confirmation points for agentic actions.

## Phase 8 — Decision support
- [x] Deterministic evidence cards.
- [x] Predictive evidence cards.
- [x] Unsupervised segmentation/anomaly evidence cards.
- [x] Conservative recommendation generation from verified evidence.
- [x] Explicit limitations and non-decision safeguards.
- [ ] Evidence-linked recommendation citations at individual evidence-object level.

## Phase 9 — Persistence and UI
- [x] End-to-end workflow UI.
- [x] Analytics dashboard tables.
- [x] Model comparison and explanation presentation.
- [x] SQLite-backed analytical run history.
- [x] JSON and standalone HTML report exports.
- [ ] Durable dataset persistence and multi-user lifecycle.

## Phase 10 — Evaluation
- [ ] Functional tests for the new end-to-end workflow.
- [ ] Schema-mapping tests.
- [ ] Model-selection tests.
- [ ] Scalability benchmarks.
- [ ] Robustness tests.
- [ ] Documentation consistency check.

## Definition of done
A phase is complete only when implementation, tests, documentation, and known limitations agree. New functionality is therefore intentionally marked as implemented but not yet formally validated until the dedicated testing pass.

## Current status
The product now spans upload, deterministic data health, canonical schema confirmation, task detection, descriptive analytics, bounded supervised ML comparison, local unsupervised analysis, routed Spark supervised ML, distributed Spark clustering, basic explainability, provenance, persistent run history, reproducible JSON/HTML reporting, and bounded evidence-to-action synthesis in one workflow. The routing layer decides between local and Spark execution from workload characteristics; it is an engineering execution policy rather than a universal definition of Big Data. The agentic layer consumes structured analytical outputs rather than unrestricted HR records and does not make employment decisions.

The remaining major product gaps are broader local categorical feature preparation, distributed anomaly detection, SHAP/persistent explanation artifacts, durable dataset lifecycle, richer agent execution state, evidence-object-level recommendation citations, and then the dedicated robustness/benchmark test pass. No new ML test results are claimed in this document yet.
