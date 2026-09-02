# API and Tool Contracts

## Common rules

- JSON uses UTF-8 and stable, versioned response shapes.
- API errors are safe for users: no stack traces, raw employee records, secrets, or absolute paths.
- Future tool responses use `{run_id, status, warnings, provenance, result}` and reject unknown fields where safety depends on the schema.
- A mapping decision is one of `AUTO_MAPPED`, `NEEDS_REVIEW`, or `UNMAPPED`.

## Health

`GET /api/health`

Response `200` exposes service health and whether the optional local LLM fallback is enabled.

## Profile a CSV

`POST /api/datasets/profile` uses multipart form data with exactly one `file` field. The endpoint is intentionally bounded for profiling and does not persist the source file.

## Workload routing

`POST /api/workloads/route` accepts workload metadata and returns the deterministic `LOCAL` or `SPARK` execution-path decision without loading dataset records. Thresholds are configurable engineering defaults, not a universal definition of Big Data.

## Execute a dataset

`POST /api/datasets/execute` accepts one `.csv` upload, streams it to process-local disk, routes it using the M4 policy, and reads it through the selected engine. The response contains dataset ID, execution status, selected engine, dimensions, byte size, and SHA-256 content fingerprint. Missing optional engine dependencies return `503`; malformed uploads return `422`; unsupported extensions return `415`.

## Accept schema and assess feasibility

`POST /api/datasets/{dataset_id}/schema` accepts a complete canonical mapping and records the human-confirmed mapping for subsequent task detection. The existing capability response remains an eligibility screen, not model execution.

## Detect analytical tasks

`GET /api/datasets/{dataset_id}/tasks` runs deterministic task detection **after schema confirmation**. It returns candidate objectives, status, target field where applicable, selected feature fields, and human-readable reasons.

The detector currently evaluates four objective families:

- `attrition_classification` — requires a confirmed attrition field, usable numeric HR features, and sufficient rows.
- `salary_regression` — requires a confirmed salary field, usable numeric predictors, and sufficient rows.
- `employee_clustering` — requires at least two supported numeric HR features and sufficient rows.
- `anomaly_detection` — requires at least two supported numeric HR features and sufficient rows.

The detector does not invent targets and does not train a model. A `BLOCKED` result is an explicit valid outcome rather than an error.

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
