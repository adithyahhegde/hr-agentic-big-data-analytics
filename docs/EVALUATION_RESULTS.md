# Evaluation Results

## CI evidence

The reproducible evaluation workflow completed successfully on 2026-09-08 UTC for commit `c86e337b1ca1a6dcfbf6a8f92f1963fce33c586d` (GitHub Actions run `34212312393`). The run executed objective feasibility, schema mapping, bounded agent reliability, the 30-case robustness matrix, local scalability, and the SHAP explainability smoke test. The generated JSON artifact was retained by GitHub Actions for 30 days.

This document records observed CI evidence from that run. It is not a claim that the results generalize to real HR datasets or external Spark clusters.

## Observed results

| Protocol | Observed result | Interpretation |
|---|---|---|
| Objective feasibility | Pipeline accuracy `1.0`; weak baseline accuracy `0.7778` across 18 fixture/objective records | The pipeline matched the deterministic fixture-contract labels in this benchmark. The labels are synthetic evaluation assumptions, not real-world ground truth. |
| Schema mapping | `104/106 = 0.9811` exact semantic mappings vs `92/106 = 0.8679` for the normalized-name-only baseline | The semantic mapper beat the intentionally weaker name-only baseline on the evaluated non-blocked fixture columns. Ambiguous and leakage-prone fixtures were correctly excluded from exact-mapping accuracy because the expected behaviour is abstention. |
| Agent reliability | `7/7` safe scenarios; safety rate `1.0` | The bounded deterministic planner/synthesizer satisfied the tested bounds, provenance rejection, malformed-input rejection, abstention, and citation-integrity contracts. This is not an LLM-quality or human-agreement measurement. |
| Robustness matrix | `30` fixture evaluations across 10 scenarios × 3 sizes; `24` accepted and `6` blocked by schema collision | Ambiguous and leakage-prone cases were blocked at all three sizes; the remaining fixture cases completed on the local path. Spark was unavailable in this runner, so no Spark/local consistency comparison was made. |
| Local scalability | 100 rows: `0.001977s`, `50,584 rows/s`; 1,000 rows: `0.010824s`, `92,391 rows/s`; 10,000 rows: `0.110283s`, `90,676 rows/s` | The clean-fixture local descriptive path processed all three sizes successfully. The 100-row timing is small and therefore noisy; the 100× row increase produced a `55.783×` elapsed-time increase in this single-repeat CI run. These are environment-specific measurements, not performance guarantees. |
| SHAP smoke test | CI step passed | Optional bounded SHAP explainability was exercised in the evaluation environment. The workflow currently records this as a test result rather than a standalone JSON metric. |

## Reproducibility

- Seed: `42`
- Local scalability sizes: `100`, `1000`, `10000`
- Schema comparison sizes: `20`, `100`
- Feasibility sizes: `10`, `20`, `100`
- Robustness sizes: `100`, `1000`, `10000`
- Agent reliability scenarios: `7`

## What remains unverified

External Spark scalability remains unverified because the repository does not have a reachable non-local Spark cluster as part of CI. The local measurements above must not be presented as evidence that Spark is faster or that the system scales identically on a cluster.

The observed fixture results also do not establish generalization to real-world heterogeneous HR schemas, human approval quality, causal validity, or production HR decision performance.
