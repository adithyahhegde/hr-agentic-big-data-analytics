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
