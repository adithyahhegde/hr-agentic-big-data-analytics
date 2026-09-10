# Evaluation Results

## CI evidence

The reproducible evaluation workflow completed successfully on 2026-09-09 UTC for commit `de35df64715da79dd8396418b834a24b5c0f3536` (GitHub Actions run `34325958699`). The run executed objective feasibility, schema mapping, bounded agent reliability, the 30-case robustness matrix, local scalability, and the SHAP explainability smoke test. Spark was installed in the evaluation environment and the robustness benchmark's Spark comparison path was exercised using the configured local Spark master; this is not external-cluster evidence. The generated JSON artifact was retained by GitHub Actions for 30 days.

This document records observed CI evidence from that run. It is not a claim that the results generalize to real HR datasets or external Spark clusters.

## Observed results

| Protocol | Observed result | Interpretation |
|---|---|---|
| Objective feasibility | Pipeline accuracy `1.0`; weak baseline accuracy `0.7778` across 18 fixture/objective records | The pipeline matched the deterministic fixture-contract labels in this benchmark. The labels are synthetic evaluation assumptions, not real-world ground truth. |
| Schema mapping | `104/106 = 0.9811` exact semantic mappings vs `92/106 = 0.8679` for the normalized-name-only baseline | The semantic mapper beat the intentionally weaker name-only baseline on the evaluated non-blocked fixture columns. Ambiguous and leakage-prone fixtures were correctly excluded from exact-mapping accuracy because the expected behaviour is abstention. |
| Agent reliability | `7/7` safe scenarios; safety rate `1.0` | The bounded deterministic planner/synthesizer satisfied the tested bounds, provenance rejection, malformed-input rejection, abstention, and citation-integrity contracts. This is not an LLM-quality or human-agreement measurement. |
| Robustness matrix | `30` fixture evaluations across 10 scenarios × 3 sizes; `24` accepted and `6` blocked by schema collision | Ambiguous and leakage-prone cases were blocked at all three sizes; the remaining fixture cases completed successfully. Spark was available in the runner for these cases, but used the local Spark master rather than an external target cluster. |
| Local scalability | 100 rows: `0.001918s`, `52,145 rows/s`; 1,000 rows: `0.010553s`, `94,763 rows/s`; 10,000 rows: `0.106766s`, `93,663 rows/s` | The clean-fixture local descriptive path processed all three sizes successfully. The 100-row timing is small and therefore noisy; the 100× row increase produced a `55.665×` elapsed-time increase in this single-repeat CI run. These are environment-specific measurements, not performance guarantees. |
| SHAP smoke test | CI step passed | Optional bounded SHAP explainability was exercised in the evaluation environment. The workflow records this as a test result rather than a standalone JSON metric. |

## Distributed Spark parity evidence

GitHub Actions run `34515696309` (Ephemeral Spark Validation, run number `46`) completed successfully for commit `1ecf440ff516f51fd04a050fcfb25f7f9ae60c56` on 2026-09-10 UTC. The workflow started a containerized Spark 3.5.8 master and worker, waited for worker registration, configured a routable driver, executed the `external_spark_scalability_v2` protocol at 100, 1,000, and 10,000 rows, validated aggregate equivalence, and completed artifact upload and cluster cleanup. This is empirical evidence that the distributed validation protocol executes successfully against the workflow's ephemeral multi-container Spark target. It is **not** independent external-cluster evidence because the Spark target is provisioned inside the GitHub Actions runner.

The run is useful as a regression guard for distributed execution and local/Spark aggregate parity. It must not be interpreted as evidence of cluster performance, reliability, or generalization to an independently operated Spark environment.

## External Spark validation status

The repository contains a separate manual workflow, `.github/workflows/external-spark-validation.yml`, for the final target-environment gate. It requires the `HR_ANALYTICS_SPARK_MASTER` secret and rejects local/loopback masters. The protocol exercises 100, 1,000, and 10,000-row fixtures, transfers CSV lines through Spark rather than assuming shared executor filesystem access, verifies exact row counts and distributed execution, compares bounded aggregates with the deterministic local baseline, and never returns raw rows.

The latest reproducible evaluation run did **not** execute against an external cluster. Its Spark work used the runner's local Spark master. No external-cluster scalability result is claimed.

A valid final result must come from a reachable non-local Spark master and must retain the generated `external-spark.json` artifact as evaluation evidence. A skipped external step or local/ephemeral Spark execution is not evidence of independent external scalability.

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
