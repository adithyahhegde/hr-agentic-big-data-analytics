# Robustness, Failure Handling & Feature Brainstorm

## Purpose
This document defines how the platform should behave when data, models, tools, agents, infrastructure, or user inputs are imperfect. Robustness is a product requirement, not an implementation afterthought.

## Design principles
1. Never silently produce a result when a prerequisite failed.
2. Prefer a safe partial result over a fabricated complete result.
3. Separate recoverable failures from blocking failures.
4. Preserve raw input and immutable run metadata where practical; transformations create new versions.
5. Quarantine invalid records rather than silently deleting them.
6. Every automated decision must have evidence, confidence, provenance, and validation status.
7. The agent can plan and orchestrate, but deterministic tools perform calculations and validation.
8. Ambiguity should trigger clarification or human review, not guessing.
9. Every run must be resumable or restartable from a known checkpoint where practical.
10. Errors shown to users should be actionable and should not expose secrets, stack traces, or sensitive records.

## Inspired patterns from mature data/ML systems
- Data-quality expectations should have explicit actions such as warn, drop/quarantine, or fail rather than one generic error path. Databricks documents this pattern for pipeline expectations. See the research notes in `RESEARCH_GAP.md` and external references.
- Schema validation should be treated as a first-class gate because schema drift can cause downstream failures or silently degrade results. Great Expectations documents schema validation and validation checkpoints for this purpose.
- Experiment/run tracking should capture parameters, metrics, artifacts and code/version information so results can be reproduced and compared. MLflow Tracking follows this model.
- Agentic analytics should expose plans, intermediate outputs and user control instead of behaving as an opaque black box. Microsoft Data Formulator is a useful design reference.

## Failure taxonomy

### A. Input / upload failures
- Unsupported file type
- Corrupt CSV
- Empty file
- Empty dataset
- Encoding errors
- Delimiter detection failure
- Malformed quoting
- File too large
- Too many columns
- Duplicate column names
- Illegal/null column names
- Mixed data types
- Unexpected binary content

Expected behavior:
- Reject or quarantine safely.
- Explain the exact issue.
- Offer a corrective action where possible.
- Never partially ingest without recording what was accepted/rejected.

### B. Data-quality failures
Detect and report:
- Missing values
- Duplicate rows
- Duplicate IDs
- Invalid IDs
- Impossible numeric values
- Invalid dates
- Future dates where inappropriate
- Negative values where impossible
- Category explosion
- Constant columns
- Near-zero variance
- Severe class imbalance
- Outliers
- Unit inconsistencies
- Contradictory records
- Leakage candidates

Possible outcomes:
- warn and continue
- clean with a recorded transformation
- quarantine affected rows
- block the analysis

The action must depend on the rule and analytical objective; never blindly drop bad rows.

### C. Schema interpretation failures
For each source column:
- Generate candidate canonical fields.
- Use deterministic evidence first: normalized name, aliases, datatype, value patterns, uniqueness, cardinality, examples, and relationships.
- Use the local LLM only for genuinely ambiguous semantic cases.
- Produce a confidence score and evidence.
- Detect collisions where multiple source columns map to the same canonical field.
- Detect missing required concepts.
- Detect unsupported/unknown fields.
- Allow user correction.
- Persist the accepted mapping as a versioned schema.

If confidence is below the configured threshold, do not silently map.

### D. Objective feasibility failures
Before modelling, verify:
- target exists
- target is usable
- enough observations exist
- target has sufficient variation
- required features exist
- temporal information exists when needed
- leakage risks are acceptable
- sample/class balance is not obviously unusable
- required historical structure exists for forecasting
- the objective matches available data types

Return explicit reasons for infeasibility and suggest nearby feasible analyses where appropriate.

### E. Spark/data-engine failures
Handle:
- Spark startup failure
- Java/configuration errors
- executor/driver memory pressure
- serialization errors
- malformed records
- schema mismatch
- shuffle failures
- task failures
- timeout
- disk exhaustion
- oversized partitions/skew
- accidental `collect()` of large datasets

Mitigations:
- configurable resource limits
- partition-aware processing
- avoid unnecessary driver collection
- bounded previews
- checkpoint/intermediate persistence where useful
- retry only idempotent/recoverable operations
- fail with a resumable run state

### F. ML failures
Handle:
- insufficient samples
- one-class target
- missing target
- unsupported feature types
- convergence failure
- singular matrix/numerical instability
- high-cardinality categorical features
- class imbalance
- train/test split failure
- metric undefined
- model serialization failure
- SHAP incompatibility
- prediction failure

The system should not automatically switch algorithms forever. The agent may try a bounded fallback set and record every attempted model and reason for failure.

### G. Agent/LLM failures
Handle:
- unavailable LLM
- timeout
- malformed structured output
- hallucinated tool name
- invalid tool arguments
- repeated failed plans
- context overflow
- contradictory instructions
- unsafe request
- agent loop / excessive tool calls

Controls:
- strict tool schemas
- structured outputs
- maximum planning/tool-call budget
- per-step timeouts
- retry with backoff for transient failures
- validation after every tool call
- deterministic fallback paths where possible
- circuit breaker after repeated failure
- human intervention for unresolved ambiguity

The agent must never invent metrics, model results, sample sizes, or data-quality claims.

### H. LLM semantic mapping failures
If the local LLM is unavailable, schema processing must still work using deterministic methods. LLM use is an enhancement for ambiguous cases, not a single point of failure.

### I. Database/storage failures
Handle:
- connection failure
- transaction failure
- locked database
- missing table
- schema migration mismatch
- disk full
- corrupted metadata

Use transactions for metadata updates and make analysis runs idempotent where practical.

### J. Frontend/API failures
Handle:
- network timeout
- request cancellation
- duplicate submission
- stale run state
- backend unavailable
- malformed API response
- expired session
- unsupported browser capability

Use stable run IDs and polling/status endpoints rather than assuming a long-running analysis request remains connected.

## Run state machine
Recommended states:
`CREATED -> VALIDATING -> PROFILED -> SCHEMA_REVIEW -> READY -> PLANNING -> EXECUTING -> VALIDATING_RESULT -> COMPLETED`

Failure/alternate states:
`BLOCKED`, `NEEDS_REVIEW`, `PARTIAL`, `FAILED`, `CANCELLED`.

Every state transition should be persisted with timestamp and reason.

## Retry policy
Retry only when the failure is plausibly transient and the operation is safe to repeat.

- network timeout: bounded exponential backoff
- temporary service unavailable: bounded retry
- deterministic schema error: no automatic retry
- invalid user input: no retry; request correction
- model convergence failure: bounded model fallback
- Spark resource failure: do not blindly retry; diagnose and reduce/adjust workload
- agent malformed output: one or more bounded repair attempts, then stop

## Quarantine
Rows rejected by data-quality rules should be traceable in a quarantine output containing a reason code and run/version identifier. Do not expose raw sensitive HR values in application logs.

## Observability
Every analysis run should capture:
- run ID
- dataset/version ID
- input fingerprint where safe
- schema version
- mapping decisions
- data-quality summary
- objective
- agent plan
- tools invoked
- Spark job metadata where available
- models attempted
- selected model
- metrics
- explanations
- warnings
- recommendations
- execution duration
- failure/retry events
- software/configuration version

Use structured logs and correlation IDs.

## Security and privacy
- Never commit credentials.
- Do not send HR data to external LLMs by default.
- Redact sensitive values from logs and error messages.
- Validate file paths and uploaded content.
- Limit resource-intensive operations.
- Restrict arbitrary code execution from model output.
- Treat model-generated SQL/code as untrusted until validated/sandboxed.
- Provide deletion/retention controls for uploaded data.

## Feature backlog / robustness enhancements
### MVP candidates
- Dataset health score
- Schema mapping confidence UI
- Data-quality report
- Feasibility report before model execution
- Run progress/status page
- Cancel analysis
- Retry failed run from checkpoint where practical
- Quarantine download
- Analysis run history
- Reproducible run summary
- Model comparison table
- Evidence-linked recommendations
- Warnings/limitations panel
- Clear partial-result handling

### Post-MVP candidates
- Multiple data-source connectors
- Dataset version comparison
- Schema drift detection between uploads
- Scheduled analyses
- Streaming ingestion
- Model monitoring
- drift detection
- role-based access control
- collaborative analysis threads
- report export
- experiment/model registry integration
- human approval workflow

## Reliability acceptance criteria
A feature is not complete unless its failure modes are identified and tested. Every major module needs tests for:
- happy path
- malformed input
- missing data
- boundary values
- dependency failure
- timeout
- cancellation
- retry behavior
- partial failure
- recovery/resume behavior where supported
- security-sensitive input

## Research/evaluation opportunities
Robustness itself can become part of the project's evaluation without changing the project identity. Measure:
- schema mapping accuracy on unseen variants
- false-feasible and false-infeasible objective rates
- invalid-plan rate
- successful recovery rate
- unsupported-analysis detection
- result reproducibility
- recommendation evidence coverage
- execution success rate
- latency/resource usage by dataset size
- degradation as data quality worsens

These metrics evaluate the autonomous HR analytics system as a whole rather than turning robustness into a separate product.
