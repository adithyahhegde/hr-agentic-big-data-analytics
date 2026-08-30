# Implementation Plan

## Phase 0 — Research and contracts
- [ ] Complete literature/product gap review.
- [ ] Freeze MVP requirements.
- [ ] Validate architecture and canonical schema.

## Phase 1 — Repository foundation
- [ ] Backend skeleton.
- [ ] Frontend skeleton.
- [ ] Configuration and environment management.
- [ ] Basic health checks.

## Phase 2 — Data ingestion and profiling
- [ ] CSV upload.
- [ ] File validation.
- [ ] Dataset profiling.
- [ ] Data-quality report.

## Phase 3 — Semantic schema layer
- [ ] Canonical HR schema.
- [ ] Deterministic mappings.
- [ ] Confidence scoring.
- [ ] Ambiguity handling.
- [ ] Optional local LLM fallback.

## Phase 4 — Big Data engine
- [ ] Spark integration.
- [ ] Small/large workload routing.
- [ ] Parquet intermediate representation.
- [ ] Scalable joins/transforms.

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
