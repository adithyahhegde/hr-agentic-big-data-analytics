# Agent Instructions

## Mission
Build and maintain the HR Agentic Big Data Analytics project according to the repository documentation. Read the relevant docs before changing architecture or behavior.

## Source of truth
1. `docs/PRD.md` — product requirements
2. `docs/RESEARCH_GAP.md` — research positioning
3. `docs/TECH_SPEC.md` — architecture/technology
4. `docs/APP_FLOW.md` — user flow
5. `docs/DESIGN.md` — visual/product design
6. `docs/SCHEMA.md` — canonical data contract
7. `docs/IMPLEMENTATION.md` — implementation status/plan
8. `docs/DECISIONS.md` — architectural decisions
9. `docs/TEST_PLAN.md` — quality requirements
10. `RULES.md` — non-negotiable engineering rules
11. `docs/MVP_SPEC.md`, `docs/AGENT_ENGINE.md`, and `docs/API_CONTRACTS.md` — frozen delivery, orchestration, and interface boundaries

## Required development loop
Before a feature: inspect relevant docs and existing code.
During a feature: follow the documented architecture and contracts.
After a feature: run relevant tests, update implementation status, update any affected docs, and verify code/docs consistency.

## Documentation synchronization
A code change that changes behavior, architecture, data contracts, user flow, design, limitations, or decisions must update the relevant documentation in the same change set.

## Evidence discipline
Never invent metrics, model performance, HR findings, or research novelty. Distinguish measured results from assumptions.

## Agent behavior
Prefer small, reviewable changes. Do not rewrite unrelated working code. Keep deterministic analytics separate from LLM interpretation. Stop and request clarification when a consequential HR action or ambiguous schema mapping cannot be safely resolved.
