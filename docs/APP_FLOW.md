# Application Flow

## Implemented foundation path

`Dataset intake → CSV validation → deterministic profile → mapping proposal/collision check → schema-review state`

The current screen exposes upload, success, validation error, profile, and warning states. It does not imply that mappings have been accepted; `NEEDS_REVIEW` and `UNMAPPED` must halt dependent objectives.

## Primary flow
1. Landing/dashboard
2. Create analysis project
3. Upload CSV or select a future connector
4. Data profiling
5. Schema interpretation and canonical mapping
6. Feasible objective discovery
7. User selects an objective
8. Agent produces an execution plan
9. User reviews/starts the plan
10. Data processing
11. Model/analytics execution
12. Validation
13. Explainability where applicable
14. Findings and evidence
15. HR decision-support recommendations
16. Save/export analysis

## Error/uncertainty flow
- Invalid file → explain validation failure.
- Unsupported data type → identify unsupported fields and continue where safe.
- Ambiguous schema mapping → request confirmation.
- Objective unsupported → explain missing requirements.
- Model fails validation → do not present it as a reliable result.
- Insufficient data → report limitation rather than fabricate an analysis.

## UI principles
- Show what the system is doing.
- Make agent plans inspectable.
- Distinguish computed evidence from AI-generated text.
- Surface confidence and limitations.
- Keep consequential HR decisions with a human.

## Future flow
API/database connectors and streaming may be added without changing the core analysis contract.
