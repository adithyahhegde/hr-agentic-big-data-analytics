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

The deterministic fixture generator lives at `scripts/generate_hr_data.py`. The benchmark harness at `scripts/benchmark.py` now supports a reproducible scenario/size matrix as well as a single fixture run. Objective-feasibility evaluation is available at `scripts/feasibility_evaluation.py` and compares the pipeline's decisions with fixture-contract labels and a deliberately weak target-presence baseline.

Examples:

```bash
python scripts/benchmark.py --rows 100000 --seed 42 --scenario clean --output benchmark.json
python scripts/benchmark.py --matrix --seed 42 --output benchmark-matrix.json
python scripts/feasibility_evaluation.py --sizes 10 20 100 --seed 42 --output feasibility.json
```

A GitHub Actions evaluation workflow at `.github/workflows/evaluation.yml` executes the feasibility protocol and benchmark matrix on relevant `main` changes and manual dispatch. It uploads the generated JSON outputs as a 30-day workflow artifact and fails if the deterministic fixture-contract assertions do not hold. This creates an executable validation path; it does not substitute for target-environment Spark scalability measurements.

The benchmark harness reports elapsed time, throughput, row/duplicate counts, selected routing engine, task-feasibility results, and aggregate consistency checks. It does not print or persist employee-level records. The matrix currently covers clean, renamed, categorical, and mixed schema conditions plus deliberately invalid ambiguous/leakage-prone mappings. Invalid mapping scenarios are reported as `BLOCKED_COLLISION` and are not executed as if they were valid analytical inputs; missing-heavy, duplicate-heavy, high-cardinality, and outlier-heavy fixtures remain separate evaluation extensions.

## Functional metrics

- schema mapping precision/recall against a labelled mapping fixture
- percentage of ambiguous mappings correctly abstained
- task-feasibility precision against expected capabilities
- analytics aggregate consistency between local and Spark paths within defined tolerances
- model metric reproducibility with fixed seeds
- no raw employee records in ML/agent/report outputs
- report provenance completeness
- failure responses are structured and recorded in run history

The objective-feasibility runner is an executable protocol for the task-feasibility metric. Its fixture labels are explicit benchmark assumptions, not measurements of real-world HR datasets. The output should therefore be reported as a benchmark result only after execution in the target environment.

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

The benchmark harness and deterministic fixture tests are implemented, including a reproducible size/scenario matrix and explicit schema-gate handling for ambiguous/leakage-prone mappings. Objective-feasibility evaluation is executable with a transparent weak baseline. The new CI workflow executes both protocols automatically, but no empirical accuracy or scalability claim is made here until workflow artifacts are inspected and, for Spark claims, the target environment has been measured. Benchmark numbers are intentionally not hard-coded into the repository. They must be generated in the target runtime environment so hardware, Spark availability, and configuration are visible alongside the measurements.
