# Architecture Decision Record Log

## ADR-001 — Local-first architecture
**Status:** Accepted for MVP

Keep core data processing and ML local so the prototype can operate without paid external AI/data APIs and sensitive HR data does not need to leave the machine.

## ADR-002 — Spark for scalable processing
**Status:** Accepted for MVP

Use PySpark for large-data processing. Do not equate Spark usage alone with Big Data; the project will benchmark workload scalability and document limitations.

## ADR-003 — HDFS is not required initially
**Status:** Accepted for MVP

Do not introduce HDFS on a single development laptop unless a research/deployment requirement justifies it. Spark plus local/Parquet storage is sufficient for the initial prototype.

## ADR-004 — Agent is an orchestrator
**Status:** Accepted

The application agent coordinates deterministic tools rather than replacing them. Numerical/statistical/model computations must be performed by validated software tools.

## ADR-005 — Human-in-the-loop for consequential HR decisions
**Status:** Accepted

The system provides recommendations and evidence. It must not autonomously make employment decisions.

## ADR-006 — Semantic schema mapping is confidence-based
**Status:** Accepted

Column-name normalization alone is insufficient. Mapping may use aliases, datatypes, value patterns, context, and optionally a local LLM. Low-confidence mappings require confirmation.

## ADR-007 — Small/large processing router
**Status:** Accepted for MVP design

Use Pandas for genuinely small workloads when appropriate and Spark for workloads where scalable processing is beneficial. Thresholds must be benchmarked rather than arbitrarily asserted.

## Pending decisions
- Agent framework.
- Exact local LLM model.
- PostgreSQL vs SQLite for MVP deployment.
- Exact model registry and supported algorithms.
- Objective-discovery methodology.
- Research contribution after literature review.
