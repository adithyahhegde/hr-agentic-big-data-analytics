# Agent and Orchestration Engine

## Purpose

The agent coordinates validated tools; it does not calculate metrics, fit models, or invent results. Its input is a capability profile produced by the schema/data-quality layer, not raw HR records.

## State machine

`CREATED → VALIDATING → PROFILED → SCHEMA_REVIEW → READY → PLANNING → EXECUTING → VALIDATING_RESULT → COMPLETED`

Alternate terminal or pause states are `NEEDS_REVIEW`, `BLOCKED`, `PARTIAL`, `FAILED`, and `CANCELLED`. Each transition must carry a timestamp, reason code, run ID, and correlation ID.

## Tool policy

Tools are registered, typed, permissioned operations. The initial registry is: `profile_dataset`, `validate_data`, `map_schema`, `detect_schema_drift`, `feasibility_check`, `descriptive_analysis`, `classification`, `regression`, `clustering`, `anomaly_detection`, `spark_profile`, `spark_transform`, `spark_aggregate`, `train_model`, `evaluate_model`, `explain_model`, `generate_insights`, and `create_report`.

Tool outputs are structured and validated before the next step. A tool cannot receive raw user-generated code, and the LLM cannot call an unregistered tool or alter a deterministic result.

## Planning and safeguards

Before execution, the planner must validate that the requested objective is feasible, the schema mapping is accepted, and data-quality gates pass. It emits a reviewable plan with prerequisites, tool calls, resource budget, expected artifacts, and stop conditions. The user confirms consequential or uncertain work.

- Each tool has a timeout, idempotency classification, and bounded retry limit.
- Retry only transient, safe failures; schema/data prerequisite failures block rather than loop.
- Enforce per-run tool-call, time, memory, row-preview, and output-size budgets.
- Route to Spark only via an explicit workload decision; avoid `collect()` for large paths.
- If a local LLM is unavailable, schema processing continues deterministically and ambiguous fields remain for review.
- Model execution requires target/feature checks, leakage review, task-appropriate metrics, and explicit limitations.

## Provenance and synthesis

Record dataset fingerprint, profile/schema version, user corrections, plan, tool inputs/outputs (redacted), runtime/configuration version, retries, artifacts, warnings, metrics, and model/explanation lineage. Language generation may summarize evidence only when every numerical or factual claim references a structured evidence ID. Recommendations must be labeled decision support and cannot make employment decisions.

## Current implementation boundary

The first slice implements the `VALIDATING → PROFILED → SCHEMA_REVIEW` foundation only. No autonomous planner or LLM execution is active.
