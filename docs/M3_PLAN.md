# M3 — Optional Local LLM Fallback

## Objective

Resolve only the schema mappings that deterministic M2 cannot safely resolve, using an optional local LLM while preserving deterministic behavior, uncertainty, privacy, and human review.

## Guardrail

Deterministic M2 remains authoritative. The LLM is a fallback, not the primary schema mapper and must never silently replace a deterministic `AUTO_MAPPED` result.

## Pipeline

`M2 mapping → unresolved/ambiguous selection → bounded metadata prompt → structured candidate response → schema/allowlist validation → confidence adjustment → NEEDS_REVIEW or accepted fallback → audit/provenance`

## Non-goals

- No cloud LLM calls.
- No raw HR dataset upload to an LLM.
- No Spark implementation.
- No autonomous consequential HR decisions.
- No automatic acceptance of an unvalidated LLM mapping.

## Required inputs

Only the minimum metadata needed for semantic interpretation should be supplied: source column name, normalized name, inferred physical type, bounded value-category summaries/patterns, cardinality/missingness/profile evidence, and the allowed canonical candidate set.

Raw sample values should not be sent unless a later privacy-reviewed design explicitly permits bounded masked examples.

## Output contract

The LLM adapter must return structured data containing candidate canonical field IDs, confidence, concise reasoning/evidence codes, and an explicit `UNKNOWN` option. Invalid field IDs, malformed output, unsupported claims, and confidence outside `[0,1]` are rejected.

## Acceptance policy

LLM results default to `NEEDS_REVIEW`. A later policy may allow a high-confidence fallback to become `AUTO_MAPPED` only if deterministic post-validation passes, ambiguity is sufficiently low, and the project contract explicitly permits it. The initial M3 implementation should favor review over silent automation.

## Providers

Use a local Ollama-compatible adapter with a configurable endpoint/model. Provider availability must be optional: if the service is unavailable, M2 results remain valid and unresolved fields stay `UNMAPPED` or `NEEDS_REVIEW`.

## Tests

Test provider absence, timeout/error, malformed JSON, invalid canonical IDs, prompt bounds/privacy, deterministic fallback, ambiguous inputs, and reproducibility of non-LLM behavior.
