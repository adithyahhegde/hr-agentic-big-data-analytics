# Design Specification

## Product character
Professional HR analytics: clear, evidence-led, restrained, and data-dense without looking like a generic admin dashboard.

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
- Do not encode critical information by color alone.
- Clearly distinguish prediction, explanation, recommendation, and user action.

## Design system source of truth
This file is intentionally compatible with a future Stitch-generated/maintained `DESIGN.md`. If Stitch is used, generated design decisions must be reconciled with this file rather than blindly replacing it.

## Status
Initial design direction. Detailed tokens and component specifications will be added before production UI implementation.
