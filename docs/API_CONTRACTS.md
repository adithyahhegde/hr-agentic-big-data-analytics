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

Response `200` contains `row_count`, `column_count`, `duplicate_row_count`, `columns`, `mappings`, `issues`, `data_quality`, `llm_used`, `schema_version` (e.g. `"2.0.0"`), and `dataset_fingerprint` (SHA-256 hex digest of sorted headers). `columns[*]` includes source/normalized name, inferred type, non-null/null counts, `missing_percentage`, `unique_count`, `uniqueness_ratio`, bounded samples, and optional `numeric_stats` (`min`, `max`, `mean`, `zeros_count`, `negatives_count`). `mappings[source]` has `canonical_field`, confidence `0..1`, decision (`AUTO_MAPPED`, `NEEDS_REVIEW`, `UNMAPPED`), `evidence` reason codes, `alternatives` candidate list, and component scores (`name_score`, `type_score`, `value_score`, `profile_score`). `data_quality` contains `health_score` (0-100), summary `metrics` (completeness rate, duplicate rate, clean row rate, constant columns), evaluated `rules`, and issue counts by severity. Validation failures are `422`; unsupported files are `415`.

No source file, samples, or mapping is persisted in this slice.

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
