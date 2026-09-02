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
- [x] CSV upload (request-scoped only).
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
- [ ] End-to-end API integration of workload routing and execution.

## Phase 5 — Analytics/ML engine
- [ ] Task detection.
- [ ] Candidate model registry.
- [ ] Training/evaluation pipelines.
- [ ] Appropriate metrics.
- [ ] Leakage and imbalance checks.

## Phase 6 — Explainability
- [ ] SHAP integration for supported models.
- [ ] Structured explanation outputs.
- [ ] Evidence provenance.

## Phase 7 — Agent orchestration
- [ ] Tool interface contracts.
- [ ] Planning.
- [ ] Execution state.
- [ ] Retry/recovery.
- [ ] Human confirmation points.

## Phase 8 — Decision support
- [ ] Insight synthesis.
- [ ] Recommendation generation.
- [ ] Evidence links.
- [ ] Uncertainty/limitations.

## Phase 9 — Persistence and UI
- [ ] Analysis history.
- [ ] Database persistence.
- [ ] Results dashboard.
- [ ] Export/reporting.

## Phase 10 — Evaluation
- [ ] Functional tests.
- [ ] Schema-mapping tests.
- [ ] Model-selection tests.
- [ ] Scalability benchmarks.
- [ ] Robustness tests.
- [ ] Documentation consistency check.

## Definition of done
A phase is complete only when implementation, tests, documentation, and known limitations agree. The agent must update the relevant docs in the same change set.

## Current status
M0 Foundation, M1 Data Quality, M2 Canonical HR Schema, M3 optional local LLM fallback, and the core M4 Big Data execution services are implemented. M4 now has deterministic workload routing, optional Spark execution, local execution, Parquet output, and distributed-safe grouped aggregation. API-level execution integration and benchmark validation remain before Phase 4 is fully closed.

Next target: integrate the M4 execution services into the analytical API, then proceed to Phase 5 task detection and ML.
