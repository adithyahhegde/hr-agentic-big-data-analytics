# Evaluation and Benchmark Plan

## Purpose

Evaluate the system as an evidence-led heterogeneous HR analytics pipeline, not only as a collection of API endpoints.

## Dataset matrix

| Scenario | What it tests |
|---|---|
| Clean canonical HR CSV | baseline correctness |
| Renamed columns | deterministic schema mapping |
| Mixed numeric/categorical predictors | heterogeneous ML |
| Missing-heavy CSV | data-quality warnings and task blocking |
| Duplicate-heavy CSV | duplicate detection |
| Ambiguous column names | abstention and user confirmation |
| Unsupported fields | safe `unknown` handling |
| Small dataset | statistical/task feasibility safeguards |
| Large synthetic dataset | LOCAL vs SPARK routing and scalability |
| High-cardinality categorical data | bounded categorical summaries |
| Outlier-heavy numeric data | anomaly-screen behaviour and limitations |

The deterministic fixture generator lives at `scripts/generate_hr_data.py`. The benchmark harness at `scripts/benchmark.py` supports a reproducible scenario/size matrix and distinct missing-heavy, duplicate-heavy, high-cardinality, and outlier-heavy fixtures in addition to clean, renamed, categorical, mixed, ambiguous, and leakage-prone scenarios. Objective-feasibility evaluation is available at `scripts/feasibility_evaluation.py` and compares pipeline decisions with fixture-contract labels and a deliberately weak target-presence baseline.

## Reproducible commands

```bash
python scripts/benchmark.py --rows 100000 --seed 42 --scenario clean --output benchmark.json
python scripts/benchmark.py --matrix --seed 42 --output benchmark-matrix.json
python scripts/feasibility_evaluation.py --sizes 10 20 100 --seed 42 --output feasibility.json
python scripts/schema_mapping_evaluation.py --sizes 20 100 --seed 42 --output schema-mapping.json
python scripts/agent_reliability_evaluation.py --seed 42 --output agent-reliability.json
python scripts/scalability_evaluation.py --sizes 100 1000 10000 --seed 42 --repeats 1 --output scalability.json
HR_ANALYTICS_SPARK_MASTER=spark://host:7077 python scripts/external_spark_validation.py --rows 10000 --seed 42 --output external-spark.json
```

The GitHub Actions evaluation workflow at `.github/workflows/evaluation.yml` executes feasibility, comparative mapping, bounded-agent reliability, robustness, local scalability, and SHAP smoke evaluation on relevant `main` changes and manual dispatch. It uploads JSON outputs as a 30-day artifact and fails on deterministic fixture-contract violations. This does not substitute for target-environment Spark measurements.

The external Spark protocol at `scripts/external_spark_validation.py` is opt-in and requires an explicit non-local `HR_ANALYTICS_SPARK_MASTER`. It validates a clean fixture's distributed descriptive path without collecting raw rows. The repository does not claim external-cluster results until this command is executed against a reachable target cluster and its output is retained as evaluation evidence.

## Functional metrics

- schema mapping precision/recall against a labelled mapping fixture
- comparative exact-mapping accuracy against a normalized-name-only baseline that intentionally ignores aliases
- percentage of ambiguous mappings correctly abstained
- task-feasibility precision against expected capabilities
- analytics aggregate consistency between local and Spark paths within defined tolerances
- model metric reproducibility with fixed seeds
- no raw employee records in ML/agent/report outputs
- report provenance completeness
- structured failure responses recorded in run history
- planner-to-synthesis safety rate across valid, blocked, unsupported, malformed, provenance-mismatched, and bounded-evidence scenarios

The schema comparison intentionally excludes ambiguous and leakage-prone fixtures from exact-mapping accuracy because correct behaviour is abstention rather than forced assignment. It reports method accuracy but does not establish generalization to real-world HR schemas.

The objective-feasibility runner is an executable protocol whose fixture labels are benchmark assumptions, not measurements of real-world HR datasets. The bounded-agent reliability runner composes the actual deterministic planner and evidence synthesizer and checks valid flow, abstention, provenance rejection, malformed-input rejection, citation integrity, and evidence bounds. These are service-contract protocols, not measures of LLM quality, human agreement, or real-world generalization.

## Scalability metrics

For increasing synthetic sizes, record ingestion time, analytics wall-clock time, ML wall-clock time where applicable, rows/second, peak memory where measurable, selected engine, and whether raw rows were collected to the driver. `scripts/scalability_evaluation.py` provides bounded local measurement with sorted/de-duplicated sizes and 1–5 median timing repeats. CI measures 100, 1,000, and 10,000-row clean fixtures. These timings are environment-specific evidence, not universal guarantees. External Spark validation is a separate target-environment requirement.

Do not claim Spark is faster for every workload. The evaluation should identify the workload size at which distributed execution becomes operationally useful under the configured environment.

## Reproducibility and academic reporting

Every benchmark should record the dataset fingerprint, schema version, engine, objective, configuration/seed, status, and timestamp. Results should use fixed fixtures and documented tolerances. Report successes and abstentions/failures so the system's ability to avoid unsafe conclusions is visible.

## Current evidence status

The benchmark harness and deterministic fixture tests are implemented, including the reproducible size/scenario matrix, explicit schema-gate handling, data-quality stress fixtures, comparative schema mapping, objective-feasibility evaluation, bounded-agent reliability evaluation, local scalability evaluation, external Spark validation protocol, and optional SHAP smoke protocol. **No empirical accuracy or scalability claim is made until workflow artifacts are inspected and, for Spark claims, the target environment has been measured.** Benchmark numbers are intentionally generated in the target runtime rather than hard-coded into the repository.
