from app.models import Capability


def determine_capabilities(mappings: dict[str, str], row_count: int) -> list[Capability]:
    accepted = set(mappings.values()) - {"unknown"}
    usable_features = accepted - {"employee_id", "attrition", "salary"}
    has_features = bool(usable_features)
    enough_rows = row_count >= 10

    def capability(objective: str, target: str | None = None) -> Capability:
        reasons: list[str] = []
        if target and target not in accepted:
            reasons.append(f"A confirmed {target} target is required.")
        if not has_features:
            reasons.append("At least one confirmed non-identifier feature is required.")
        if not enough_rows:
            reasons.append("At least 10 rows are required for this preliminary feasibility check.")
        return Capability(objective=objective, status="FEASIBLE" if not reasons else "BLOCKED", reasons=reasons or ["Required confirmed fields are present; model-specific validation is still required."])

    return [
        capability("attrition_classification", "attrition"),
        capability("salary_regression", "salary"),
        capability("employee_clustering"),
        capability("anomaly_detection"),
    ]
