# API Failure and Recovery Contract

The execution API distinguishes successful results from failed attempts in the persistent SQLite run ledger.

## Failure recording

Dataset-scoped API failures with HTTP status `422`, `500`, or `503` are recorded as `FAILED` runs. The ledger stores the dataset id, fingerprint when the dataset is available, operation, timestamp, engine when known, and a sanitized error type.

Raw exception messages are not persisted in the failure result and are not returned to API clients. Client responses use a fixed operational message for dependency failures and unexpected server failures. This prevents implementation details, local paths, or accidental employee-level values from becoming part of the public API contract.

Failure persistence is best-effort: if the ledger itself is unavailable, the original API response is not replaced by a secondary persistence error.

## Recovery semantics

Only `SUCCEEDED` runs are eligible for analytical result recovery. A `FAILED` record therefore cannot be mistaken for a valid analytical result after restart. Successful recovery additionally requires the dataset fingerprint and, when supplied, schema version to match.

The `/api/datasets/{dataset_id}/runs` endpoint exposes both successful and failed attempts so operators can distinguish a missing run from an execution failure.

## Current end-to-end abstention matrix

The API test suite exercises these failure/abstention paths:

| Scenario | Expected behavior |
| --- | --- |
| Missing dataset/schema state | `409`, no analytical execution |
| Ambiguous canonical mapping | `422`, schema confirmation blocked |
| Insufficient rows for supervised ML | `409`, model execution blocked |
| Unsupported ML objective | `404`, no model execution |
| Runtime/dependency failure | `503`, sanitized response + `FAILED` ledger record |
| Unexpected server failure | `500`, generic response + `FAILED` ledger record |

These tests establish application-level failure semantics. They do **not** constitute a production-scale reliability measurement or an external-cluster validation; those remain part of the evaluation protocol.
