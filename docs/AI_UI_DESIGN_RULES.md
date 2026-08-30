# AI UI Design Rules

## Purpose
The product must be AI-built without looking like generic AI-generated software. It should feel like a credible professional workforce analytics product.

## Avoid AI-slop patterns
- No purple/blue/cyan gradient as the default visual identity.
- No gradient text.
- No decorative neon glows, excessive blur, or glassmorphism.
- No generic AI orb, robot, magic wand, sparkle, lightning, or emoji icons as decorative representations of AI.
- Do not use icons where text or a functional control is clearer.
- Avoid excessive rounded cards, nested cards, floating panels, and identical card grids.
- Avoid oversized hero sections or marketing-style copy inside the application.
- Avoid decorative background grids, blobs, particles, or visual noise.
- Avoid generic phrases such as "Unlock insights", "supercharge your workforce", or "next-generation AI".
- Do not label normal system states as "AI thinking" or similar anthropomorphic language.

## Product character
- Treat the product as analytical/enterprise software, not an AI showcase.
- Prioritize information hierarchy, evidence, usability, and data density.
- Use restrained visual styling with deliberate hierarchy.
- Prefer functional icons that communicate the underlying action or data concept.
- Use whitespace intentionally, not as a substitute for information architecture.
- Do not make every component visually prominent.

## Content language
Prefer precise labels such as:
- "Schema mapping"
- "Analysis plan"
- "Model performance"
- "Evidence"
- "Data quality"
- "Limitations"
- "Recommendation"

Avoid marketing/AI hype language.

## Real-product states
Every major workflow must have credible states:
- Empty state
- Loading/progress state
- Success state
- Partial-success state
- Validation state
- Ambiguous schema state
- Insufficient-data state
- Error state
- No-results state

Example: use "Processing 2.4M records" rather than "AI is thinking".

## Analytical integrity
- Never make a chart look more impressive than the underlying evidence.
- Charts must have titles, units/context, labels where appropriate, and accessible explanations.
- Do not use colour as the only encoding for important distinctions.
- Clearly distinguish observed data, model predictions, explanations, recommendations, and user actions.
- Show uncertainty and limitations where material.

## AI visibility
AI may be exposed as a capability where useful, but it should not dominate the visual language. The product should communicate intelligence through useful behaviour and evidence rather than decorative AI branding.

## Design review gate
Before UI work is considered complete, check:
1. Does the interface resemble a professional analytics product?
2. Did any generic AI visual pattern appear without a functional reason?
3. Are icons meaningful and consistent?
4. Are empty/error/ambiguous states realistic?
5. Is the visual hierarchy driven by analytical importance?
6. Is the interface understandable without relying on AI branding?

This file is part of the design source of truth and must be consulted by Stitch, Antigravity, Codex, or any other UI-building agent.
