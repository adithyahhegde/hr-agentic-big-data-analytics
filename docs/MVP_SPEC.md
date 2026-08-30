# MVP Scope and Acceptance Contract

## Status
Frozen for the foundation release. This scope refines the end-to-end HR analytics project; it does not claim a new research contribution.

## Included in the first vertical slice

1. Local FastAPI service with a health/configuration endpoint.
2. UTF-8 CSV-only intake with bounded file, row, and column limits.
3. Structural validation: non-empty payload, header, non-blank/unique names, row shape, encoding, and binary-content rejection.
4. Deterministic column and dataset profiling: inferred type, missingness, cardinality, samples, duplicate rows, and warnings.
5. Canonical HR mapping proposals using aliases plus value-pattern evidence for supported fields.
6. Editable temporary-session schema review and collision detection; collisions are blocking and require review.
7. Preliminary feasibility results for attrition classification, salary regression, clustering, and anomaly detection.
8. A small browser interface for upload, status, profile, mapping proposal, feasibility, and warning states.

## Explicitly deferred

Persistent datasets/runs, durable mapping reuse, local-LLM calls, Spark routing, agent planning, ML, SHAP, reports, and recommendations. The contracts are documented now so these stages can be added without changing the foundation’s meaning.

## Acceptance criteria

- `GET /api/health` returns service status and non-sensitive configuration state.
- `POST /api/datasets/profile` rejects invalid input with an actionable 4xx response and never retains it.
- A valid CSV returns a deterministic profile and a mapping decision with evidence for every field.
- Unknown fields remain `UNMAPPED`; the service must not force a semantic interpretation.
- Duplicate canonical mappings become `NEEDS_REVIEW` with a blocking issue.
- The UI visibly presents success and error states, with no AI-marketing language or decorative AI imagery.
- Unit tests cover malformed CSV, encoding, deterministic mapping, and collision behavior.

## Resource and privacy limits

Defaults are 10 MiB per upload, 10,000 profiled data rows, and 500 columns. These are engineering safeguards, not a universal definition of big data. Payloads are processed in request memory only and are not logged or persisted by this release. Local LLM integration is disabled by default.
