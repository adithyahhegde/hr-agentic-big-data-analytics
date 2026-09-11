# External Spark validation operator runbook

The final Definition-of-Done evaluation gate is intentionally an **independent target-environment experiment**, not a local or ephemeral-CI benchmark. The repository provides the executable protocol and evidence validator; this runbook defines the operator-side handoff needed to produce admissible evidence.

## Target requirements

Provide a reachable Spark standalone master from the GitHub Actions runner. The target must not be `localhost`, `127.0.0.1`, or `::1`. The target should be independently operated from the runner rather than provisioned by the validation workflow itself.

Configure the repository environment with:

- `HR_ANALYTICS_SPARK_MASTER`: a `spark://host:port` master endpoint.
- `HR_ANALYTICS_SPARK_DRIVER_HOST`: optional routable hostname/IP for the validation driver's callback path.
- `HR_ANALYTICS_SPARK_DRIVER_BIND_ADDRESS`: optional bind address when the target network requires it.

The workflow stores the target endpoint only as a secret. Evidence records a SHA-256 fingerprint instead of the endpoint itself.

## Run protocol

1. Open the **External Spark Validation** workflow and dispatch it manually.
2. Set `spark_version` to the exact Spark/PySpark version installed on the target cluster.
3. The workflow performs a TCP preflight before installing dependencies or running the benchmark.
4. The protocol generates deterministic fixtures at exactly 100, 1,000, and 10,000 rows using seed 42.
5. Each fixture is analyzed through the configured Spark master and compared with the deterministic local aggregate baseline.
6. The workflow rejects non-distributed execution, raw-row return, aggregate mismatch, missing Spark execution provenance, invalid timing, and malformed provenance.
7. The reusable validator additionally binds available GitHub revision and target/version environment identities to the artifact.
8. Retain the generated `external-spark.json` artifact from the successful run.

## Evidence acceptance

A result is admissible only when the workflow completes successfully and the retained artifact passes `scripts/validate_external_spark_evidence.py`. Do not convert an ephemeral Spark result, a local result, a skipped workflow, or a hand-created JSON file into external-cluster evidence.

The final documentation entry should record the successful workflow run ID, commit SHA, target Spark version, fixture sizes, and artifact provenance. Do not record the target endpoint itself.

## Current blocker

No independently operated target cluster is available to this automation environment. Until a real target is supplied through the repository's configured secret/environment, the external Spark DoD item remains unchecked. The repository intentionally records this as **unverified** rather than substituting ephemeral/local measurements.

See issue #7 for the tracked completion gate.
