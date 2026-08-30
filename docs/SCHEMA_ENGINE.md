# Schema Understanding & Analytical Capability Engine

## Foundation implementation alignment

The implemented stage comprises deterministic structural profiling, the M1 data-quality engine, and the **M2 Canonical HR Schema Engine**. It includes the 35-field canonical HR ontology, multi-signal evidence scoring (normalised aliases, datatype compatibility, sample value pattern checks, uniqueness/cardinality profile scoring), explicit mapping policies (`AUTO_MAPPED`, `NEEDS_REVIEW`, `UNMAPPED`), alternative candidate tracking, canonical collision resolution, order-invariant dataset fingerprinting (SHA-256), schema versioning (`2.0.0`), temporary schema acceptance, and preliminary capability detection. Relationship context evidence, LLM fallback, durable database version persistence, and multi-file drift comparison remain planned for subsequent milestones.

## 1. Purpose

The Schema Engine is the bridge between an arbitrary HR dataset and the autonomous analytics pipeline. It must infer meaning from evidence without assuming that source column names are standard, and it must refuse to make unsupported semantic claims.

The product remains an **autonomous HR Big Data analytics and decision-support system**. Schema understanding is a prerequisite and enabling component, not the research product by itself.

## 2. Design principles

1. Never infer semantic meaning from a column name alone.
2. Prefer deterministic, inspectable evidence before LLM reasoning.
3. Use the local LLM only for ambiguous semantic interpretation and controlled language tasks.
4. Never let an LLM calculate statistics or silently alter raw data.
5. Every mapping has evidence, confidence, status, and provenance.
6. Low-confidence mappings must not silently enter consequential analyses.
7. Unknown columns may remain unmapped.
8. Canonical schema changes are versioned.
9. Analytical feasibility is determined from validated evidence, not from LLM optimism.
10. The system must fail closed when required information is missing or contradictory.

## 3. End-to-end flow

```text
Raw dataset
    |
    v
File/source validation
    |
    v
Structural profiling
    |
    v
Column/value profiling
    |
    v
Candidate semantic generation
    |
    +--> deterministic evidence
    |
    +--> controlled local-LLM evidence for ambiguous cases
    |
    v
Candidate scoring + conflict detection
    |
    v
Mapping status
    |       |        |
    |       |        +--> unmapped
    |       +-----------> human review
    +-------------------> auto-map when policy permits
    |
    v
Canonical HR schema
    |
    v
Data-quality + analytical feasibility engine
    |
    v
Supported analytical objectives
    |
    v
Agent planner
```

## 4. Profiling contract

For each dataset and column, collect only the information required for inference and validation.

### Dataset-level profile

- row count or estimated row count
- column count
- file format and encoding
- duplicate-row estimate/count where feasible
- empty-row statistics
- partition/file information where applicable
- dataset fingerprint/version identifier
- overall missingness
- candidate entity/grain
- suspected target variables
- validation warnings

### Column-level profile

- source name
- normalized source name
- inferred physical datatype
- logical type candidates: numeric, categorical, date/time, text, identifier, boolean, etc.
- null count and percentage
- distinct count/cardinality
- uniqueness ratio
- sample values using bounded sampling
- numeric min/max/quantiles where safe
- categorical frequency summary where bounded
- string length statistics where useful
- date range where applicable
- format/pattern signals
- constant/near-constant signal
- suspicious identifier signal
- potential PII/sensitive-field signal
- distribution/quality warnings

Large datasets must be profiled with bounded scans/aggregations rather than loading all records into driver memory.

## 5. Canonical HR schema

The initial ontology is intentionally small and extensible. It is not assumed to cover every organisation.

### Identity / entity

- `employee_id`
- `employee_record_id`
- `employment_status`

### Organisation

- `department`
- `business_unit`
- `job_role`
- `job_level`
- `location`
- `manager_id`

### Workforce characteristics

- `age`
- `tenure`
- `hire_date`
- `termination_date`
- `work_mode`
- `employment_type`

### Compensation

- `salary`
- `bonus`
- `compensation_band`

### Performance / engagement

- `performance_rating`
- `job_satisfaction`
- `engagement_score`
- `training_hours`
- `absence_days`
- `overtime`

### Career outcomes

- `promotion_status`
- `promotion_date`
- `attrition`
- `termination_reason`

Each canonical field must have metadata describing accepted logical types, aliases, value patterns, semantic description, sensitivity class, and which analytical objectives can consume it.

The ontology must remain configurable; adding a field must not require rewriting the mapping engine.

## 6. Mapping evidence

Mapping should combine independent evidence sources.

### A. Name evidence

Normalize names using deterministic transformations:

- lowercase
- punctuation/underscore/camel-case normalization
- abbreviation dictionary
- alias dictionary
- token similarity

Examples:

`emp_no` -> `employee_id` candidate
`yrs` -> `tenure` candidate
`left_org` -> `attrition` candidate

Name similarity alone is insufficient for automatic mapping.

### B. Type evidence

Compare physical/logical type against the canonical field contract.

Examples:

- `employee_id` should generally behave like an identifier.
- `salary` should generally be numeric or safely coercible to numeric.
- `hire_date` should have date/time semantics.
- `attrition` may be binary categorical or a compatible boolean representation.

### C. Value evidence

Inspect bounded samples and distributions.

Examples:

`performance_rating = {1,2,3,4,5}` strongly supports a rating-like concept.

`attrition = {Yes, No}` supports a binary outcome but does not prove that the field means attrition.

### D. Statistical/profile evidence

Use:

- cardinality
- uniqueness
- range
- missingness
- distribution
- value patterns
- monotonic/date signals

### E. Relationship/context evidence

Where useful, inspect relationships between columns and dataset grain.

Examples:

- employee identifier should be compatible with the apparent employee-level grain.
- `department` and `job_role` may provide context for workforce data.
- a candidate target should have a plausible outcome distribution.

Relationships are supporting evidence, not proof of meaning.

### F. Local LLM evidence

Only invoke Ollama when deterministic evidence leaves material ambiguity.

The LLM receives a bounded structured description such as:

```json
{
  "column": "prm_st",
  "dtype": "string",
  "cardinality": 2,
  "sample_values": ["Y", "N"],
  "candidate_concepts": [
    "promotion_status",
    "performance_status",
    "employment_status"
  ]
}
```

It must return structured candidate interpretations with reasons and uncertainty. It must not invent observed values or statistics.

LLM output is treated as one evidence source, not ground truth.

## 7. Candidate scoring

The engine should maintain component scores rather than hiding everything in one opaque number.

Example conceptual score:

```text
mapping_score =
    name_similarity * w_name +
    type_compatibility * w_type +
    value_compatibility * w_value +
    profile_compatibility * w_profile +
    relationship_compatibility * w_relationship +
    llm_support * w_llm
```

Weights and thresholds are configuration, not scientific facts. They must be evaluated experimentally.

A score must be accompanied by an evidence breakdown, for example:

```text
employee_id -> emp_no
Overall confidence: 0.96

Name evidence:       strong
Type evidence:       strong
Uniqueness evidence: strong
Value evidence:      strong
LLM evidence:        not required
```

Do not display false precision. The UI should avoid implying that `0.9637` is a calibrated probability unless calibration has actually been demonstrated.

## 8. Mapping policy

Initial policy is intentionally conservative.

- **High confidence + no conflicts:** eligible for automatic mapping.
- **Medium confidence:** suggestion; user review required before use in consequential analysis.
- **Low confidence:** remain unmapped.
- **Conflicting candidates:** require review even if the top score is high.
- **Required field unmapped:** dependent analytical objectives are blocked.

Initial threshold values are configurable engineering defaults and must be validated experimentally before being described as optimal.

## 9. Collision handling

The engine must detect:

- two source columns mapping to one canonical field
- one source column matching multiple required concepts
- duplicate identifiers
- mutually incompatible mappings
- target leakage candidates
- fields whose semantics change across partitions/files

Never silently overwrite a previous mapping.

## 10. Human review

The review UI should show:

- source column
- candidate canonical field
- confidence band
- evidence breakdown
- representative values
- warnings
- alternative candidates
- reason for uncertainty

User actions:

- accept
- change mapping
- leave unmapped
- mark as intentionally excluded

All corrections become part of the run provenance and can optionally be used as explicit project-level mapping rules after validation.

## 11. Unknown and sensitive fields

Unknown fields remain available in the raw/derived dataset but are not forced into the canonical HR ontology.

Potential sensitive fields must be flagged. The system should minimise their exposure to logs and external services. The local-first design means raw HR data should not be sent to external LLM APIs by default.

## 12. Schema versioning

Every analysis run references:

- canonical schema version
- source schema fingerprint
- mapping configuration version
- mapping results
- user corrections
- profile version

A source schema change should create a new mapping state rather than silently mutating historical runs.

## 13. Schema drift

For repeated analyses, detect:

- added columns
- removed columns
- renamed columns
- datatype changes
- category/value-set changes
- distribution shifts
- mapping-confidence changes

Structural schema validation should be combined with semantic checks; schema validation alone cannot establish semantic correctness. This mirrors established data-quality practice: schema checks catch structural changes, while field-level and integrity checks address broader correctness. citeturn0search0turn0search8

## 14. Analytical capability / feasibility engine

After mapping and validation, derive a machine-readable capability profile.

Example:

```text
Attrition classification       FEASIBLE
Salary regression              FEASIBLE
Employee clustering            FEASIBLE
Anomaly detection              FEASIBLE
Promotion prediction           BLOCKED
Reason: no validated promotion outcome/history
```

Each objective declares:

- required fields
- optional fields
- minimum data conditions
- target requirements
- task type
- known leakage risks
- required preprocessing
- supported execution engines
- evaluation metrics
- explainability support

The capability engine must explain both positive and negative decisions.

## 15. Objective feasibility checks

### Classification

Check:

- validated target exists
- target has sufficient classes
- no single-class target
- sufficient observations per class
- leakage candidates reviewed

### Regression

Check:

- validated numeric/compatible target exists
- sufficient non-null target values
- variance is not effectively zero
- leakage candidates reviewed

### Clustering

Check:

- sufficient usable feature set
- enough non-constant observations
- excessive missingness handled
- identifier columns excluded

### Anomaly detection

Check:

- sufficient usable features/records
- identifiers excluded
- scaling/type compatibility
- interpretation limitations shown

## 16. Data-quality gate

Use explicit machine-readable validation results before analysis. Established data-quality systems use declarative expectations for schema, types, presence, ranges, cardinality, and other conditions; our implementation uses deterministic checks without making external heavy frameworks a mandatory runtime dependency.

### Validation severity

- `INFO` — informational observations (e.g. clean column variance, passed uniqueness checks).
- `WARNING` — analysis may continue with visible limitation (e.g. high missingness >20%, duplicate rows, domain range outliers).
- `BLOCKING` — required prerequisite is not satisfied or collision/integrity failure is present (e.g. critical missingness >80%, duplicate identifiers, negative compensation).
- `CRITICAL` — dataset integrity cannot be trusted or dataset is empty (e.g. 0 data rows, corrupted structure).

The distinction between validation failure and validation execution failure must be preserved.

### Dataset Health Score methodology

The Dataset Health Score ($0.0 - 100.0$) is a deterministic **engineering quality indicator** summarizing structural data health. It is not a percentage of analytical truth, ground truth, or statistical accuracy.

1. **Score components & weights**:
   - **Completeness ($40\%$)**: $40 \times \text{completeness\_rate}$ (where $\text{completeness\_rate} = 1.0 - \frac{\text{missing\_cells}}{\text{total\_cells}}$).
   - **Uniqueness ($20\%$)**: $20 \times (1.0 - \text{duplicate\_row\_rate})$.
   - **Clean rows ($20\%$)**: $20 \times \text{clean\_row\_rate}$ (fraction of rows with no missing or blank values).
   - **Baseline integrity ($20\%$)**: Base 20 points minus severity-based deductions:
     - Each `CRITICAL` issue: $-20$ points.
     - Each `BLOCKING` issue: $-10$ points.
     - Each `WARNING` issue: $-2$ points.
   - Final score is bounded between $0.0$ and $100.0$, rounded to 1 decimal place.

2. **Score interpretation**:
   - `80.0 - 100.0` (Good): High structural completeness, distinct records, standard domain sanity checks satisfied.
   - `50.0 - 79.9` (Moderate): Acceptable for exploratory analysis, but contains missing values, duplicates, or non-critical anomalies.
   - `0.0 - 49.9` (Requires Attention): Heavy data defects, blocking issues, or severe structural corruption.

3. **Engine-agnostic architecture**:
   - Computations depend on aggregated summary statistics (`DatasetSummaryStats` and `ColumnProfile`) rather than requiring all rows in Python memory. This keeps the design compatible with future Spark and streaming engines where statistics are computed via distributed transformations.

4. **Sampled PII signal semantics**:
   - Sensitive and PII detection (email, phone, SSN / national ID patterns) is executed as a heuristic pattern scan on bounded sample values.
   - A passing result means no patterns were detected in the analyzed sample; it does **not** guarantee the absence of sensitive data across the entire dataset.
   - Raw sensitive values are never logged, persisted, or returned in user-facing error messages.


## 17. Failure and fallback policy

### File problems

- unsupported format -> reject with supported formats
- empty file -> reject
- unreadable encoding -> offer supported encoding options / clear error
- malformed CSV -> report parsing location when available
- excessive size -> use bounded/streaming-compatible path or reject with resource explanation

### Profiling problems

- partial profiling -> label results partial
- resource exhaustion -> stop safely and preserve failure state
- malformed column -> isolate where possible

### Mapping problems

- LLM unavailable -> deterministic mapping continues
- LLM timeout -> continue without LLM evidence
- malformed LLM JSON -> retry with bounded limit, then fallback
- conflicting candidates -> human review

### Feasibility problems

- required target missing -> block dependent objective
- insufficient observations -> block and explain
- ambiguous target semantics -> require review

## 18. Security and privacy

- Do not log raw employee records.
- Redact sensitive values from error messages.
- Limit sample values exposed to the LLM.
- Keep external LLM transmission disabled by default.
- Validate uploaded files before parsing.
- Enforce resource limits.
- Keep secrets out of source control.

## 19. Test strategy

Create fixtures covering:

1. Clean standard HR schema.
2. Abbreviated column names.
3. Completely unfamiliar names.
4. Mixed data types.
5. Missing values.
6. Duplicate columns/records.
7. Conflicting semantic candidates.
8. No valid target.
9. Single-class target.
10. Extreme class imbalance.
11. Sensitive fields.
12. Schema drift between runs.
13. LLM unavailable.
14. LLM malformed response.
15. Large dataset path.
16. Multiple files with inconsistent schemas.

Measure at minimum:

- correct mapping rate
- incorrect auto-mapping rate
- unresolved mapping rate
- human-review rate
- objective feasibility precision/recall where ground truth is available
- runtime/resource use
- failure recovery rate

Do not report mapping accuracy without a labelled evaluation set.

## 20. Provenance

Every mapping and capability decision should be traceable to:

- run ID
- source dataset fingerprint
- profile version
- schema version
- mapping rules/configuration
- deterministic evidence
- LLM model/version when used
- LLM request/response schema version where safe
- user correction
- timestamp

The final analysis record should make it possible to explain why an analytical objective was enabled or blocked.

## 21. Relationship to the agent

The agent consumes the capability profile. It does not directly guess the dataset's semantics.

```text
Schema Engine -> validated capability profile -> Agent planner
```

This separation is intentional:

- schema engine = evidence and validation
- agent = orchestration
- Spark/ML/statistics = computation
- SHAP = explainability
- LLM = controlled semantic/language assistance

The agent may request a re-profile or ask for human clarification, but it must not bypass schema/quality gates.

## 22. Research evaluation opportunity

The schema engine should support controlled experiments comparing:

- name-only mapping
- deterministic multi-signal mapping
- deterministic + local LLM fallback
- human-assisted mapping

The goal is not to assume the proposed method is superior. The experiment should determine whether the additional semantic/feasibility layer improves end-to-end analytical reliability on heterogeneous HR datasets.

## 23. Implementation note

Do not over-engineer the first implementation. Start with CSV, a configurable canonical schema, deterministic profiling/mapping, bounded local-LLM fallback, explicit confidence bands, human review, and capability detection. Add connectors and advanced ontology features only after the core path is reliable.
