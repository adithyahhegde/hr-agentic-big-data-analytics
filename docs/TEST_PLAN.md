# Test Plan

## Unit tests
- Data type inference.
- Column normalization.
- Alias matching.
- Semantic mapping confidence.
- Objective feasibility rules.
- Metric selection.
- Tool input/output contracts.

## Implemented foundation tests

- Empty/invalid UTF-8 and duplicate trimmed headers are rejected.
- Alias mapping emits field, confidence, and evidence.
- Canonical-field collisions change the mapping decision to review and emit a blocking issue.
- Schema acceptance rejects duplicate canonical-field assignments and returns explained preliminary capability decisions.
- A user can correct an unknown source field to a supported canonical HR field; browser rendering uses DOM text nodes for uploaded headers rather than injecting them as HTML.
- Data Quality Engine tests verify deterministic numeric profiling (min, max, mean, zero/negative counts), sampled PII/sensitive pattern signals (email, phone, SSN) with explicit non-guarantee semantics, configurable domain validations (negative compensation, out-of-range age, tenure outliers), duplicate identifiers, completeness gates (>20%, >80%), empty row detection, single-row handling, all-null columns, and composite dataset health scoring (0-100).



## Integration tests
- Upload → profiling.
- Profiling → schema mapping.
- Schema → objective discovery.
- Objective → execution plan.
- Spark → ML pipeline.
- ML → SHAP.
- Analysis → persistence.
- Backend → frontend.

## Robustness datasets
1. Clean conventional HR dataset.
2. Dataset with inconsistent column names.
3. Dataset with abbreviations.
4. Missing and duplicated data.
5. Imbalanced classification target.
6. Dataset without a supported target.
7. Dataset with potential leakage.
8. Multiple related HR tables.
9. Large synthetic dataset for Spark benchmarking.

## Acceptance principles
- No unsupported objective is executed silently.
- Low-confidence mappings are surfaced.
- Failed models are not presented as valid recommendations.
- Computed values shown in the UI must originate from deterministic outputs.
- AI-generated prose must be distinguishable from computed evidence.
- Sensitive raw HR data must not appear in logs.

## Scalability evaluation
Benchmark representative dataset sizes and compare processing behavior rather than claiming a universal Big Data threshold.
