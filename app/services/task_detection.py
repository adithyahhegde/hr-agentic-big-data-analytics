"""Deterministic HR analytical task detection.

This module converts an accepted canonical schema into feasible analytical
objectives. It does not train models and never invents a target column.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TaskCandidate:
    objective: str
    status: str
    target_field: str | None
    feature_fields: tuple[str, ...]
    reasons: tuple[str, ...]


def _fields(mappings: dict[str, str]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for source, canonical in mappings.items():
        if canonical == "unknown":
            continue
        result.setdefault(canonical, []).append(source)
    return result


def detect_tasks(mappings: dict[str, str], row_count: int) -> list[TaskCandidate]:
    """Return explainable task candidates from the confirmed canonical schema."""
    fields = _fields(mappings)
    sources = tuple(source for source, canonical in mappings.items() if canonical != "unknown")
    numeric_features = tuple(
        source for source, canonical in mappings.items()
        if canonical in {
            "age", "monthly_income", "hourly_rate", "daily_rate", "distance_from_home",
            "education_level", "environment_satisfaction", "job_involvement",
            "job_level", "job_satisfaction", "monthly_rate", "num_companies_worked",
            "percent_salary_hike", "performance_rating", "relationship_satisfaction",
            "stock_option_level", "total_working_years", "training_times_last_year",
            "work_life_balance", "years_at_company", "years_in_current_role",
            "years_since_last_promotion", "years_with_current_manager", "bonus",
            "salary",
        }
    )

    candidates: list[TaskCandidate] = []
    attrition = tuple(fields.get("attrition", []))
    if attrition and numeric_features and row_count >= 20:
        candidates.append(TaskCandidate(
            "attrition_classification", "FEASIBLE", attrition[0],
            tuple(f for f in numeric_features if f != attrition[0]),
            ("Confirmed attrition target and usable numeric HR features are present.",),
        ))
    else:
        reasons = []
        if not attrition: reasons.append("No confirmed attrition field.")
        if not numeric_features: reasons.append("No supported numeric HR features.")
        if row_count < 20: reasons.append("At least 20 rows are required for the preliminary screen.")
        candidates.append(TaskCandidate("attrition_classification", "BLOCKED", attrition[0] if attrition else None, (), tuple(reasons)))

    salary = tuple(fields.get("salary", []))
    regression_features = tuple(f for f in numeric_features if f not in salary)
    if salary and regression_features and row_count >= 20:
        candidates.append(TaskCandidate(
            "salary_regression", "FEASIBLE", salary[0], regression_features,
            ("Confirmed salary target and usable numeric HR features are present.",),
        ))
    else:
        reasons = []
        if not salary: reasons.append("No confirmed salary field.")
        if not regression_features: reasons.append("No supported numeric predictor fields.")
        if row_count < 20: reasons.append("At least 20 rows are required for the preliminary screen.")
        candidates.append(TaskCandidate("salary_regression", "BLOCKED", salary[0] if salary else None, (), tuple(reasons)))

    if len(numeric_features) >= 2 and row_count >= 20:
        candidates.append(TaskCandidate("employee_clustering", "FEASIBLE", None, numeric_features, ("At least two numeric HR features and sufficient rows are present.",)))
    else:
        candidates.append(TaskCandidate("employee_clustering", "BLOCKED", None, numeric_features, ("At least two numeric HR features and 20 rows are required.",)))

    if len(numeric_features) >= 2 and row_count >= 20:
        candidates.append(TaskCandidate("anomaly_detection", "FEASIBLE", None, numeric_features, ("At least two numeric HR features and sufficient rows are present.",)))
    else:
        candidates.append(TaskCandidate("anomaly_detection", "BLOCKED", None, numeric_features, ("At least two numeric HR features and 20 rows are required.",)))

    return candidates
