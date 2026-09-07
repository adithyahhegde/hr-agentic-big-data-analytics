# Evidence-linked recommendation contract

The bounded insight synthesizer emits stable, response-local `evidence_id` values (`evidence-1`, `evidence-2`, ...) for every evidence object. Each generated recommendation includes an `evidence_ids` list pointing to the evidence objects that justify that recommendation.

This makes the decision-support layer auditable at the individual evidence-object level without exposing raw HR records.

## Contract

- Evidence IDs are unique within one synthesis response.
- Recommendations may reference only evidence IDs emitted in the same response.
- Empty-evidence fallback recommendations use an empty `evidence_ids` list and explicitly state that no automated recommendation should be inferred from the empty result.
- Rejected or provenance-invalid analytical runs cannot generate evidence IDs or recommendations.
- Evidence remains bounded to the existing synthesis limits; IDs do not increase the amount of analytical content exposed.

This is provenance linkage, not a claim that the evidence is causal or that a recommendation is an employment decision. Human review and domain validation remain required.
