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
- [x] CSV upload and reusable dataset storage.
- [x] File validation and bounded profiling.
- [x] Deterministic dataset profiling.
- [x] Data-quality report.
- [x] Persistent profile state.

## Phase 3 — Semantic schema layer
- [x] Canonical HR schema.
- [x] Deterministic mappings.
- [x] Confidence scoring.
- [x] Collision/ambiguity blocking at schema acceptance.
- [x] Optional local LLM fallback.
- [x] Persistent confirmed mappings.

## Phase 4 — Big Data engine
- [x] Spark integration (optional runtime dependency).
- [x] Small/large workload routing.
- [x] Parquet intermediate representation.
- [x] Scalable grouped transformations.
- [x] API-level workload routing contract.
- [x] Streamed dataset execution boundary.
- [x] Durable local dataset persistence and manifest registry.
- [x] Scalable descriptive analytics path.
- [x] Distributed anomaly screening path.
- [ ] External-cluster scalability validation.

## Phase 5 — Analytics/ML engine
- [x] Deterministic task detection.
- [x] Bounded candidate model comparison for classification and regression.
- [x] Train/test evaluation pipeline.
- [x] Task-appropriate metrics and reproducible seed.
- [x] Identifier/constant-feature exclusion and basic imbalance handling.
- [x] Local K-Means clustering with candidate-k comparison and silhouette evidence.
- [x] Local Isolation Forest anomaly detection with aggregate-only output.
- [x] Native Spark ML path for routed supervised classification/regression.
- [x] Distributed Spark K-Means path for routed clustering workloads.
- [x] Heterogeneous local supervised feature preparation with numeric imputation and categorical one-hot encoding.
- [x] Distributed anomaly screening with explicit method disclosure.

## Phase 6 — Explainability
- [x] Structured feature-importance/permutation evidence for supported local supervised models.
- [x] Model-selection evidence surfaced in the UI.
- [x] Dataset/schema/model provenance fields exposed by the API.
- [x] Spark execution exposes explainability metadata and explicit limitations where grouped attribution is unavailable.
- [ ] SHAP integration for supported models.
- [ ] Persistent explanation artifacts.

## Phase 7 — Agent orchestration
- [x] Tool/interface contracts documented.
- [x] Bounded evidence-to-action synthesis service.
- [x] Separate synthesis handling for predictive, segmentation, and anomaly evidence.
- [x] Structured provenance attached to analytical run records.
- [ ] Multi-step planning/execution state.
- [ ] Retry/recovery orchestration beyond bounded service-level handling.
- [ ] Human confirmation points for consequential agentic actions.

## Phase 8 — Decision support
- [x] Deterministic evidence cards.
- [x] Predictive evidence cards.
- [x] Unsupervised segmentation/anomaly evidence cards.
- [x] Conservative recommendation generation from verified evidence.
- [x] Explicit limitations and non-decision safeguards.
- [x] Evidence-linked recommendation citations at individual evidence-object level.

## Phase 9 — Persistence and UI
- [x] End-to-end workflow UI.
- [x] Analytics dashboard tables.
- [x] Model comparison and explanation presentation.
- [x] SQLite-backed analytical run history.
- [x] JSON and standalone HTML report exports.
- [x] Dataset list/manifest APIs.
- [x] Restart-recoverable dataset/profile/schema state when local data storage persists.
- [ ] Multi-user lifecycle and access control.

## Phase 10 — Evaluation
- [x] Benchmark fixture generator.
- [x] Benchmark harness with local/Spark optional comparison and consistency checks.
- [x] Regression tests for routing, profiling, data quality, persistence, provenance, bounded synthesis, reports, and benchmark behavior.
- [ ] Full robustness matrix across clean/messy/ambiguous/categorical/mixed datasets.
- [ ] Scalability measurements at multiple dataset sizes.
- [ ] Comparative schema-mapping evaluation against baseline methods.
- [x] Executable objective-feasibility evaluation protocol against explicit fixture-contract labels and a weak baseline (empirical execution still outstanding).
- [ ] End-to-end agent reliability/abstention evaluation.
- [ ] Documentation consistency audit after final feature freeze.

## Definition of done
A phase is complete only when implementation, tests, documentation, and known limitations agree. New functionality is intentionally marked as implemented but not as empirically validated until the dedicated evaluation protocol has been executed.

## Current status
The product now spans upload, deterministic data health, canonical schema confirmation, heterogeneous task detection, descriptive analytics, bounded supervised ML comparison with mixed numeric/categorical predictors, local unsupervised analysis, routed Spark supervised ML, distributed Spark clustering/anomaly screening, explainability evidence, persistent dataset/profile/schema state, persistent run history, reproducible JSON/HTML reporting, and bounded evidence-to-action synthesis in one workflow.

The remaining research-critical work is primarily **evaluation rather than adding unchecked features**: execute the robustness/scalability protocol, quantify schema-mapping and feasibility reliability, test abstention/failure behavior, and document the observed trade-offs. The broad product concept is not claimed as novel; the proposed contribution must be supported by measured results.