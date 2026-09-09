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
- [x] External-cluster scalability validation protocol (target-cluster execution outstanding).

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
- [x] Optional bounded SHAP integration for supported local supervised models; falls back safely when unavailable/unsupported.
- [x] Persistent explanation artifacts for successful runs, bounded and lineage-scoped in SQLite.

## Phase 7 — Agent orchestration
- [x] Tool/interface contracts documented.
- [x] Bounded evidence-to-action synthesis service.
- [x] Separate synthesis handling for predictive, segmentation, and anomaly evidence.
- [x] Structured provenance attached to analytical run records.
- [x] Durable multi-step planning/execution state machine with restart recovery.
- [x] Bounded retry/recovery orchestration for workflow steps.
- [x] Human confirmation gate for consequential action requests, persisted across restart and explicit approval/denial required.

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
- [x] Persistent bounded explanation artifacts associated with successful analytical runs.
- [x] JSON and standalone HTML report exports.
- [x] Dataset list/manifest APIs.
- [x] Restart-recoverable dataset/profile/schema state when local data storage persists.
- [x] Authenticated multi-user dataset lifecycle and owner isolation using per-user API credentials.
- [x] Owner isolation applied to cached datasets, analytical run history, explanations, and durable agent workflows.
- [x] Modern interaction layer: accessible landmarks, keyboard-reachable upload, focus-visible states, reduced-motion support, responsive touch targets, and non-blocking status/toast feedback.
- [x] Static UI contract tests covering workflow structure and accessibility interaction requirements.

## Phase 10 — Evaluation
- [x] Benchmark fixture generator.
- [x] Benchmark harness with local/Spark optional comparison and consistency checks.
- [x] Regression tests for routing, profiling, data quality, persistence, provenance, bounded synthesis, reports, and benchmark behavior.
- [x] Expanded robustness fixture matrix including missing-heavy, duplicate-heavy, high-cardinality, and outlier-heavy data plus ambiguous/leakage-prone schema gates.
- [x] Reproducible local scalability measurements at 100, 1,000, and 10,000 rows (CI evidence recorded; timings are environment-specific).
- [x] Comparative schema-mapping evaluation against baseline methods, with CI evidence recorded.
- [x] Executable objective-feasibility evaluation against explicit fixture-contract labels and a weak baseline, with CI evidence recorded.
- [x] Executable bounded planner-to-synthesis reliability/abstention evaluation, with CI evidence recorded.
- [x] SHAP smoke evaluation contract and CI smoke execution for optional local explainability.
- [ ] External Spark target-cluster scalability validation.
- [x] Documentation consistency audit after final feature freeze.

## Definition of done
A phase is complete only when implementation, tests, documentation, and known limitations agree. New functionality is intentionally marked as implemented but not as empirically validated until the dedicated evaluation protocol has been executed.

## Current status
The product now spans upload, deterministic data health, canonical HR schema confirmation, heterogeneous task detection, descriptive analytics, bounded supervised ML comparison with mixed numeric/categorical predictors, local unsupervised analysis, routed Spark supervised ML, distributed Spark clustering/anomaly screening, bounded optional SHAP explainability with safe fallback, persistent explanation artifacts, persistent dataset/profile/schema state, owner-scoped persistent run history, durable owner-scoped planner/execution/synthesis workflow state, durable human confirmation gates for future consequential actions, authenticated multi-user dataset ownership isolation, reproducible JSON/HTML reporting, bounded evidence-to-action synthesis, and an explicit external-Spark target-environment validation protocol in one workflow.

The reproducible evaluation workflow has now produced CI evidence for local robustness/scalability, comparative schema mapping, objective feasibility, bounded planner-to-synthesis reliability, and the optional SHAP smoke test. The observed results are recorded in `docs/EVALUATION_RESULTS.md`. Remaining research-critical work is external Spark target-cluster validation. These results are fixture- and environment-specific and do not establish generalization to real HR datasets, human agreement, causal validity, or production HR decision performance. The broad product concept is not claimed as novel. The current multi-user boundary is application-level API-key identity and dataset/state isolation, not a full IAM/RBAC system.
