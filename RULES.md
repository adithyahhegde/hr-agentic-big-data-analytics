# Non-Negotiable Project Rules

1. No unsupported research novelty claims.
2. No fabricated statistics, model metrics, findings, or recommendations.
3. The LLM must not perform numerical computation that should be done by deterministic tools.
4. The agent is an orchestrator, not a replacement for Spark, ML, statistical, or validation tools.
5. Use Spark for workloads designated for scalable processing and avoid unnecessary full-data collection into local memory.
6. Do not force Spark onto tiny workloads without a measured reason.
7. Schema mappings must have confidence and evidence/reason codes.
8. Low-confidence semantic mappings require human confirmation.
9. Never silently infer a consequential HR field when evidence is insufficient.
10. Model selection must use task-appropriate evaluation metrics.
11. Do not treat accuracy as universally sufficient, especially for imbalanced HR outcomes.
12. Check for obvious leakage and severe data-quality problems before trusting model results.
13. Explainability outputs must be tied to the actual fitted model/data.
14. Recommendations must be traceable to computed evidence and clearly labeled as decision support.
15. The system must not autonomously make hiring, firing, promotion, compensation, or other consequential employment decisions.
16. Keep sensitive HR data local by default; never add external AI APIs without explicit approval.
17. Never commit secrets, credentials, tokens, or private datasets.
18. Validate uploaded files and external data sources before processing.
19. Add tests for new analytical behavior and update `docs/TEST_PLAN.md` when testing strategy changes.
20. Update affected documentation whenever implementation changes its assumptions, interfaces, architecture, schema, flow, design, or limitations.
21. Do not mark a feature complete until code, tests, and documentation are consistent.
22. Preserve provenance: record what data, configuration, model, and tool produced an analytical result.
23. All UI work must comply with `docs/AI_UI_DESIGN_RULES.md` and `docs/DESIGN.md`.
24. Do not use generic AI visual tropes or marketing language merely to signal that AI is present.
25. UI must include realistic empty, loading, validation, ambiguity, partial-success, error, and no-result states where applicable.
26. Do not use decorative icons, gradients, glows, or other visual effects unless they have a clear product/usability purpose.
27. Stitch or AI-generated UI output is a proposal, not an authority; reconcile it with the project's design source of truth before implementation.
