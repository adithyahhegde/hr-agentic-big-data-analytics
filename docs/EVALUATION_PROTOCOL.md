# Evaluation Protocol

## Objective

Evaluate whether the proposed HR-specific pipeline improves reliability when compared with simpler baselines on heterogeneous HR datasets. The evaluation must report measured results rather than infer novelty from implementation complexity.

## Research hypotheses

**H1 — Schema interpretation:** confidence-aware canonical HR mapping will achieve higher exact-mapping accuracy than name-only normalization/synonym matching on heterogeneous column names.

**H2 — Feasibility gating:** objective detection will abstain on unsupported or insufficient datasets instead of incorrectly presenting an analytical task as feasible.

**H3 — Evidence traceability:** recommendations generated from structured analytical evidence will retain a verifiable path to the underlying metric/model result and avoid unsupported numerical claims.

**H4 — Scalable execution:** Spark routing will become operationally useful as workload size/complexity crosses the configured local execution boundary, while small workloads will avoid unnecessary distributed overhead.

**H5 — Robustness:** deterministic-first processing will degrade to `NEEDS_REVIEW`/blocked states on ambiguous inputs rather than silently forcing low-confidence schema mappings.

## Dataset scenarios

Construct seeded synthetic datasets plus, where legally and ethically appropriate, public anonymized HR datasets. Required scenarios:

1. **Clean canonical:** standard names, valid types, low missingness, unique identifiers.
2. **Alias variation:** abbreviations, synonyms, punctuation/case variation, reordered columns.
3. **Messy types:** numeric values represented as strings, commas/currency symbols, mixed categorical encodings.
4. **Missingness:** low, moderate, high, and critical missingness.
5. **Duplicates:** exact duplicate rows and duplicate identifiers with different attributes.
6. **Ambiguous schema:** fields that plausibly map to multiple canonical concepts.
7. **Categorical-heavy:** departments, roles, locations, satisfaction bands and other categorical predictors.
8. **Mixed supervised:** numeric + categorical predictors with a valid classification target.
9. **Unsupported objective:** datasets intentionally missing required targets/features.
10. **Scale ladder:** repeated deterministic fixtures at increasing row counts and file sizes.

Every generated dataset records its seed, row count, column count, scenario, and generation configuration. Do not include real employee identifiers in benchmark fixtures.

## Metrics

### Schema mapping

- exact canonical-field accuracy
- macro precision/recall/F1 across mapped fields
- abstention rate
- collision detection rate
- false-auto-map rate
- confidence calibration where labelled confidence bins are available

### Feasibility detection

- feasible-task precision/recall/F1
- unsupported-task false-positive rate
- correct abstention rate
- prerequisite failure classification accuracy

### Analytics consistency

- row-count agreement between execution engines
- duplicate-count agreement
- aggregate statistic relative error where both engines support the same statistic
- missingness-rate agreement

### ML

Report task-appropriate metrics from held-out data. Classification should include F1, precision, recall and ROC-AUC when mathematically defined. Regression should include MAE, RMSE and R². Report test-set size, class balance, random seed, selected model and candidate models.

Do not compare metrics across unrelated objectives as though they were on one common scale.

### Reliability and safety

- unsupported-claim rate in generated recommendations
- evidence-link coverage
- raw-record exposure count in agent/report payloads (target: zero)
- failure-to-safe-state rate
- silent-failure rate (target: zero)
- percentage of ambiguous inputs correctly routed to review/block states

### Scalability

For each scale point record:

- rows
- bytes
- columns
- selected engine
- wall-clock runtime
- rows/second
- peak memory where available
- Spark startup overhead separately when possible
- aggregate consistency result

The benchmark should compare like-for-like analytical workloads and should not claim Spark is faster at tiny scales if startup overhead dominates.

## Baselines

At minimum compare schema mapping against:

1. exact normalized-name matching;
2. synonym/alias matching without value/profile evidence;
3. the implemented deterministic confidence-aware mapper.

For feasibility, compare the implemented capability detector against a simple rule baseline that only checks whether a named target column exists and whether the minimum row threshold is met.

For execution routing, compare the configured router with always-local and always-Spark policies on the same workload ladder.

## Statistical reporting

Use multiple deterministic seeds where runtime permits. Report mean, median, standard deviation and sample size for runtime measures. For classification-style comparisons report confidence intervals or paired comparisons when enough repeated observations exist. Keep train/test partitions fixed per seed so model comparisons are reproducible.

Do not cherry-pick favourable seeds or dataset scenarios. Report failures, unavailable dependencies and blocked tasks as outcomes.

## Acceptance criteria

These are evaluation targets, not claimed results:

- false-auto-map rate should be near zero on ambiguous labelled cases;
- unsupported objectives should not be reported as feasible;
- exported reports and agent inputs should contain no raw employee records;
- engine consistency should hold for statistics explicitly defined as cross-engine comparable;
- every recommendation containing a numerical/factual claim should trace to a structured evidence object;
- benchmark outputs should be reproducible from the same seed and configuration.

Performance thresholds must be chosen after baseline measurements rather than invented to make the proposed system pass.

## Reproducibility record

Every experiment should preserve:

`dataset scenario + seed + dataset fingerprint + schema version + mapping decisions + workload policy + engine + software version + model configuration + random seed + metrics + warnings + failures + timestamp`.

Store aggregate benchmark results under an ignored runtime-results directory; do not commit raw HR-like records or generated employee rows to the repository.

## Interpretation rules

A positive result supports the corresponding hypothesis only for the tested dataset distribution and configuration. It does not establish universal superiority or novelty. A negative result should be retained and used to refine the contribution. The final paper must distinguish implementation capability, evaluation result, and research claim.