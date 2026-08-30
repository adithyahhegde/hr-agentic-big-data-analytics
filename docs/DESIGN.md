# Design Specification

## Product character
Professional HR analytics: clear, evidence-led, restrained, and data-dense without looking like a generic admin dashboard or AI-generated showcase.

## Design source of truth
`docs/DESIGN.md` defines the core product design system. `docs/AI_UI_DESIGN_RULES.md` contains mandatory anti-AI-slop rules. If Stitch, Antigravity, Codex, or another agent proposes visual changes, those changes must be reconciled with these documents rather than blindly accepted.

## Information hierarchy
1. Current analysis state
2. Key findings
3. Evidence and metrics
4. Model/explanation details
5. Recommendations
6. Data quality and limitations

## Core screens
- Dashboard
- Data source/upload
- Data profile
- Schema mapping
- Objective selection
- Agent plan review
- Analysis progress
- Results dashboard
- Explainability view
- Recommendation view
- Analysis history

## Components
- Upload/dropzone
- Dataset summary cards
- Schema mapping table
- Confidence badge
- Objective cards
- Agent plan timeline
- Progress/state indicator
- Metric cards
- Charts
- Feature-importance/SHAP visualizations
- Recommendation cards
- Warning/limitation panels
- Data tables

## Visual rules
- Prefer accessible contrast and readable typography.
- Avoid decorative visuals that compete with analytical evidence.
- Use consistent spacing, hierarchy, and states.
- Every chart must have a title, units/context, and enough information to interpret it.
- Do not encode critical information by colour alone.
- Clearly distinguish prediction, explanation, recommendation, and user action.
- Prefer functional icons that represent the actual operation or data concept.
- Do not use decorative AI symbols as the product's visual identity.
- Avoid gradients, neon/glow effects, excessive glassmorphism, decorative background effects, excessive rounded containers, and repetitive card grids unless a specific usability reason justifies them.
- Use precise analytical language instead of AI/marketing hype.
- Design realistic empty, loading, validation, ambiguity, partial-success, error, and no-result states.

## UI quality gate
Before a UI feature is considered complete, verify it against `docs/AI_UI_DESIGN_RULES.md`, accessibility expectations, responsive behaviour, and the analytical information hierarchy.

## Stitch usage
Stitch may be used for exploration and visual prototyping. Generated designs must be reconciled with this document and `AI_UI_DESIGN_RULES.md` before implementation. Stitch output is not automatically authoritative.

## Status
Initial design direction. Detailed tokens and component specifications will be added before production UI implementation.

## Foundation UI implementation

The intake screen uses a restrained document-like layout, a single action, semantic table, responsive stylesheet, and explicit progress/error/warning text. It intentionally omits gradients, decorative AI visuals, and generic dashboard-card patterns. Mapping status is textually explicit; no critical meaning depends only on colour.

The primary schema action is “Continue with safe mappings”; detailed review is optional and collapsed by default. This keeps routine upload flows short without weakening the blocking behavior for mapping conflicts.
