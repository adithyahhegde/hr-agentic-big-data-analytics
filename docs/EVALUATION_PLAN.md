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

The deterministic fixture generator lives at `scripts/generate_hr_data.py`. The benchmark harness at `scripts/benchmark.py` now supports a reproducible scenario/size matrix as well as a single fixture run.

Examples:

```bash
python scripts/benchmark.py --rows 100000 --seed 42 --scenario clean --output benchmark.json
python scripts/benchmark.py --matrix --seed 42 --output benchmark-matrix.json
```

The harness reports elapsed time, throughput, row/duplicate counts, selected routing engine, task-feasibility results, and aggregate consistency checks. It does not print or persist employee-level records. The matrix currently covers clean, renamed, categorical, and mixed schema conditions across configurable row-counts; missing-heavy, duplicate-heavy, high-cardinality, and outlier-heavy fixtures remain separate evaluation extensions.

## Functional metrics

- schema mapping precision/recall against a labelled mapping fixture
- percentage of ambiguous mappings correctly abstained
- task-feasibility precision against expected capabilities
- analytics aggregate consistency between local and Spark paths within defined tolerances
- model metric reproducibility with fixed seeds
- no raw employee records in ML/agent/report outputs
- report provenance completeness
- failure responses are structured and recorded in run history

## Scalability metrics

For synthetic datasets at increasing row counts, record:

- ingestion time
- analytics wall-clock time
- ML wall-clock time
- rows/second
- peak process memory where measurable
- selected execution engine
- whether raw rows were collected to the driver

Do not claim Spark is faster for every workload. The evaluation should identify the workload size at which distributed execution becomes operationally useful under the configured environment.

## Reproducibility

Every benchmark run should record the dataset fingerprint, schema version, engine, objective, configuration/seed, status, and timestamp. Results should be compared using fixed fixtures and documented tolerances.

## Academic reporting

Report both successes and abstentions/failures. A useful evaluation should demonstrate that the system avoids unsafe conclusions when mappings, data quality, sample size, or analytical assumptions are insufficient.

## Current evidence status

The benchmark harness and deterministic fixture tests are implemented, including a reproducible size/scenario matrix. Benchmark numbers are intentionally not hard-coded into the repository. They must be generated in the target runtime environment so hardware, Spark availability, and configuration are visible alongside the measurements.
