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
