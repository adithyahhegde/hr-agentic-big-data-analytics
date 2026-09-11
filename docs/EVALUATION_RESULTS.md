# Evaluation Results

## CI evidence

The reproducible evaluation workflow has produced successful CI evidence for the implemented evaluation contracts, including objective feasibility, schema mapping, bounded agent reliability, robustness, local scalability, and optional SHAP explainability. These results are fixture- and environment-specific and are not claims of generalization to real HR datasets or external Spark clusters.

## Distributed Spark parity evidence

GitHub Actions run `34520418685` (Ephemeral Spark Validation, run number `49`) completed successfully for commit `d0d363f3e210e94132124c03bf68d1946896b00c` on 2026-09-10 UTC. The workflow started a containerized Spark 3.5.8 master and worker, waited for worker registration, configured a routable driver, executed the `external_spark_scalability_v2` protocol at 100, 1,000, and 10,000 rows, validated aggregate equivalence, verified evidence provenance, uploaded the artifact, and completed cluster cleanup. This is empirical evidence that the distributed validation protocol executes successfully against the workflow's ephemeral multi-container Spark target. It is **not** independent external-cluster evidence because the Spark target is provisioned inside the GitHub Actions runner.

The run is a regression guard for distributed execution, local/Spark aggregate parity, Spark-version alignment, and evidence provenance. It must not be interpreted as evidence of performance, reliability, or generalization to an independently operated Spark environment.

## External Spark validation status

The repository contains a separate manual workflow, `.github/workflows/external-spark-validation.yml`, for the final target-environment gate. It requires the `HR_ANALYTICS_SPARK_MASTER` secret and rejects local/loopback masters. The workflow accepts an explicit target Spark/PySpark version, installs the same driver version, performs TCP preflight connectivity, and supports optional routable driver host/bind settings.

The protocol exercises 100, 1,000, and 10,000-row deterministic fixtures, records fixture SHA-256 and schema provenance, transfers CSV lines through Spark rather than assuming shared executor filesystem access, verifies exact row counts and distributed execution, compares bounded aggregates with the deterministic local baseline, and never returns raw rows. Evidence also records source revision, Python/platform runtime metadata, and a SHA-256 fingerprint of the configured target master so the target identity can be correlated across reruns without storing the master endpoint itself.

The external evidence gate uses a reusable validator (`scripts/validate_external_spark_evidence.py`) in addition to the workflow's inline checks. The validator independently enforces the protocol identifier, fixed seed, sorted/unique benchmark sizes, source-revision format, runtime provenance, expected Spark master kind, target fingerprint, optional workflow Spark-version binding, run/fixture metadata, aggregate-only validation flags, finite timing/throughput metrics, Spark execution provenance, and the driver-parallelized CSV input mode. This reduces the chance that malformed numerical evidence or future changes weaken the evidence contract while retaining a separate audit point from the workflow shell script.

No independent external-cluster scalability result is currently claimed. A valid final result must come from a reachable non-local Spark master and retain the generated `external-spark.json` artifact. A skipped external step, local Spark execution, or ephemeral CI cluster is not evidence of independent external scalability.

The remaining gate is tracked as GitHub issue #7, with an operator handoff in `docs/EXTERNAL_SPARK_VALIDATION_RUNBOOK.md`.

## Reproducibility

- Seed: `42`
- Local scalability sizes: `100`, `1000`, `10000`
- Schema comparison sizes: `20`, `100`
- Feasibility sizes: `10`, `20`, `100`
- Robustness sizes: `100`, `1000`, `10000`
- Agent reliability scenarios: `7`
- Ephemeral distributed Spark parity sizes: `100`, `1000`, `10000`
- Ephemeral distributed Spark version: `3.5.8`

## What remains unverified

External Spark scalability remains unverified because the repository does not currently have evidence from a reachable non-local Spark cluster. The local and ephemeral distributed measurements above must not be presented as evidence that Spark is faster or that the system scales identically on an independently operated cluster.

The observed fixture results also do not establish generalization to real-world heterogeneous HR schemas, human approval quality, causal validity, or production HR decision performance.
