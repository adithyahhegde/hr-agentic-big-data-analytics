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
- [ ] Canonical HR schema.
- [x] Deterministic mappings.
- [x] Confidence scoring.
- [x] Collision/ambiguity blocking at schema acceptance.
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

## Foundation release (0.1.0)

Implemented `GET /api/health`, `POST /api/datasets/profile`, and temporary-session `POST /api/datasets/{dataset_id}/schema`; these provide deterministic alias/value-pattern mapping, collision review gates, preliminary feasibility, and a minimal intake UI. Spark, durable persistence, local LLM, agent execution, and ML are deliberately not implemented. See `MVP_SPEC.md` and `API_CONTRACTS.md`.
