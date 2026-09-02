# API and Tool Contracts

## Common rules

- JSON uses UTF-8 and stable, versioned response shapes.
- API errors are safe for users: no stack traces, raw employee records, secrets, or absolute paths.
- Future tool responses use `{run_id, status, warnings, provenance, result}` and reject unknown fields where safety depends on the schema.
- A mapping decision is one of `AUTO_MAPPED`, `NEEDS_REVIEW`, or `UNMAPPED`.

## Health

`GET /api/health`

Response `200` exposes service health and whether the optional local LLM fallback is enabled.

## Schema vocabulary

`GET /api/schema/fields`

Returns the canonical HR field vocabulary used by the schema-review UI. The frontend does not hard-code the ontology.

## Profile a CSV

`POST /api/datasets/profile` uses multipart form data with exactly one `file` field. The endpoint stores the upload temporarily on process-local disk so the confirmed schema can be reused by downstream analysis. Durable persistence is not implemented yet.

## Workload routing

`POST /api/workloads/route` accepts workload metadata and returns the deterministic `LOCAL` or `SPARK` execution-path decision without loading dataset records. Thresholds are configurable engineering defaults, not a universal definition of Big Data.

## Execute a dataset

`POST /api/datasets/execute` accepts one `.csv` upload, streams it to process-local disk, routes it using the M4 policy, and reads it through the selected engine. The response contains dataset ID, execution status, selected engine, dimensions, byte size, and SHA-256 content fingerprint. Missing optional engine dependencies return `503`; malformed uploads return `422`; unsupported extensions return `415`.

## Accept schema and assess feasibility

`POST /api/datasets/{dataset_id}/schema` accepts a complete canonical mapping and records the human-confirmed mapping for subsequent task detection. The existing capability response remains an eligibility screen, not model execution.

## Detect analytical tasks

`GET /api/datasets/{dataset_id}/tasks` runs deterministic task detection after schema confirmation. It returns candidate objectives, status, target field where applicable, selected feature fields, and human-readable reasons.

The detector currently evaluates four objective families: attrition classification, salary regression, employee clustering, and anomaly detection. Only the first two currently have supervised model execution.

## Descriptive analytics

`GET /api/datasets/{dataset_id}/analytics` runs deterministic summaries over the confirmed mapping and returns numeric/categorical summaries, missingness findings, duplicate evidence, execution engine, dataset fingerprint, and schema version.

## Supervised model execution

`POST /api/datasets/{dataset_id}/ml/{objective}` is available only for a detected `FEASIBLE` supervised objective. The service trains bounded local candidates and returns the held-out evaluation metrics, selected model, feature evidence, safeguards, dataset fingerprint, and schema version.

Current objectives and comparison sets:

- `attrition_classification`: logistic regression, random forest, histogram gradient boosting; selection metric is F1.
- `salary_regression`: ridge regression, random forest, histogram gradient boosting; selection metric is RMSE (lower is better).

The engine excludes identifier-like/constant predictors, uses a reproducible holdout seed, requires at least 20 complete rows, and rejects single-class classification data. The current implementation is numeric-feature-only and is not yet the native Spark ML path.

## Bounded insight synthesis

`GET /api/datasets/{dataset_id}/insights` consumes only verified descriptive analytics and completed ML results. It returns an explicit synthesis plan, evidence list, reversible recommendations, limitations, and a flag showing that unrestricted raw HR records were not accessed by the synthesis layer. Recommendations are decision-support drafts, not automated employment decisions.

## Future tool envelope

```json
{
  "tool": "profile_dataset",
  "contract_version": "1.0",
  "run_id": "uuid",
  "input": {"dataset_id": "uuid"},
  "resource_budget": {"timeout_seconds": 60, "max_preview_rows": 100},
  "result": {},
  "warnings": [],
  "provenance": {"dataset_fingerprint": "sha256", "configuration_version": "..."}
}
```

`result` must be schema-validated before it is consumed; this is the boundary that prevents fabricated metrics or tool outputs.
