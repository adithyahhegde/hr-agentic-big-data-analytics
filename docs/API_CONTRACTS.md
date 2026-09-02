# API and Tool Contracts

## Common rules

- JSON uses UTF-8 and stable, versioned response shapes.
- API errors are safe for users: no stack traces, raw employee records, secrets, or absolute paths.
- Future tool responses use `{run_id, status, warnings, provenance, result}` and reject unknown fields where safety depends on the schema.
- A mapping decision is one of `AUTO_MAPPED`, `NEEDS_REVIEW`, or `UNMAPPED`.

## Health

`GET /api/health`

Response `200`:

```json
{"status":"ok","service":"HR Agentic Analytics","local_llm_enabled":false}
```

## Profile a CSV

`POST /api/datasets/profile` uses multipart form data with exactly one `file` field.

Preconditions: `.csv` extension, UTF-8 (BOM allowed), non-empty payload, header row, non-blank unique trimmed names, configured resource limits, and no extra row values.

Response `200` contains `row_count`, `column_count`, `duplicate_row_count`, `columns`, `mappings`, `issues`, `data_quality`, `llm_used`, `schema_version`, and `dataset_fingerprint`. This endpoint remains intentionally bounded for profiling.

No source file, samples, or mapping is persisted by the profiling endpoint.

## Workload routing

`POST /api/workloads/route` accepts workload metadata and returns the deterministic execution-path decision without loading dataset records.

Request:

```json
{
  "row_count": 1000000,
  "column_count": 40,
  "estimated_bytes": 200000000,
  "file_count": 1,
  "requires_distributed": false
}
```

Response `200` includes the selected `engine` (`LOCAL` or `SPARK`), the supplied workload metadata, and the active routing policy. The default policy routes to Spark when the workload explicitly requires distributed processing, exceeds 1,000,000 rows, exceeds 512 MiB, exceeds 500 columns, or contains more than 32 files. These are configurable engineering defaults, not a universal definition of Big Data.

This endpoint exposes routing only; it does not persist or execute a dataset.

## Execute a dataset

`POST /api/datasets/execute` accepts one `.csv` upload. The file is streamed to process-local disk, counted without loading all records into application memory, routed using the M4 policy, and read through the selected execution engine.

Response `200`:

```json
{
  "dataset_id": "uuid",
  "status": "EXECUTED",
  "engine": "LOCAL",
  "row_count": 100,
  "column_count": 20,
  "size_bytes": 12000,
  "dataset_fingerprint": "sha256",
  "warnings": []
}
```

The execution upload has its own bounded size limit (`HR_ANALYTICS_MAX_EXECUTION_UPLOAD_BYTES`, default 2 GiB) so the profiling limit does not prevent genuine large-workload routing. Spark and local analytical dependencies remain optional installation extras. A missing selected engine dependency returns `503`; malformed uploads return `422`; unsupported extensions return `415`.

The stored dataset is process-local and is not a durable database record. Later persistence work will add lifecycle management, provenance records, and analysis history.

## Accept schema and assess feasibility

`POST /api/datasets/{dataset_id}/schema` accepts `{"mappings":{"source_field":"canonical_field"}}`. A submitted mapping must name every source field exactly once, use a supported canonical HR field or `unknown`, and cannot assign one canonical field twice. This permits a user correction to an otherwise unknown source field. The temporary profile ID is created by the profiling endpoint and expires when the process restarts.

Response `200` returns the accepted mapping and four preliminary capability records: attrition classification, salary regression, employee clustering, and anomaly detection. Each is `FEASIBLE` or `BLOCKED` with human-readable reasons. This is an eligibility screen, not model validation or execution.

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
