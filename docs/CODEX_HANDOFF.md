# Codex Handoff

## Current state

- Phase 1 foundation: complete
- Phase 2 ingestion/profiling/data quality: complete
- Phase 3 deterministic canonical schema: implemented in M2
- Optional local LLM fallback: not implemented
- Spark / distributed execution: not implemented
- Analytics / ML: not implemented
- Explainability: not implemented
- Agent orchestration: not implemented
- Decision support: not implemented
- Persistence/history: not implemented

## Working rules

1. Preserve completed milestones unless a later integration requires a targeted correction.
2. Prefer deterministic, inspectable logic before LLM reasoning.
3. Unknown and ambiguous inputs must remain explicit; never force a mapping to increase coverage.
4. Keep APIs and data contracts stable and versioned.
5. Do not log or expose sensitive HR values.
6. Keep the small/local path separate from the future Spark path; do not materialize large datasets unnecessarily.
7. Every milestone must include tests and synchronized documentation.
8. Do not claim a capability is complete without executable verification.

## Next milestone

M3 — Optional local LLM fallback. It must operate only on unresolved/ambiguous schema mappings, return structured candidates, pass deterministic validation, preserve uncertainty, and never silently override deterministic mappings.
