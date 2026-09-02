"""Deterministic HR analytical task detection.

Task feasibility is based only on the confirmed canonical schema and row count.
Feature preparation is deliberately separated from task detection so the same
contract can be executed by local sklearn or distributed Spark engines.
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


IDENTIFIER_FIELDS = {"employee_id", "employee_record_id", "manager_id"}
SUPPORTED_ANALYTICAL_FIELDS = {
    "age", "monthly_income", "hourly_rate", "daily_rate", "distance_from_home",
    "education_level", "environment_satisfaction", "job_involvement", "job_level",
    "job_satisfaction", "monthly_rate", "num_companies_worked", "percent_salary_hike",
    "performance_rating", "relationship_satisfaction", "stock_option_level",
    "total_working_years", "training_times_last_year", "work_life_balance",
    "years_at_company", "years_in_current_role", "years_since_last_promotion",
    "years_with_current_manager", "bonus", "salary", "attrition", "department",
    "job_role", "job_level_name", "business_travel", "education_field", "gender",
    "marital_status", "job_satisfaction_label", "overtime", "employment_status",
    "work_location", "employment_type", "manager_name", "company_tenure_band",
}


def _fields(mappings: dict[str, str]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for source, canonical in mappings.items():
        if canonical == "unknown":
            continue
        result.setdefault(canonical, []).append(source)
    return result


def _usable_features(mappings: dict[str, str], target: str | None = None) -> tuple[str, ...]:
    return tuple(
        source for source, canonical in mappings.items()
        if canonical in SUPPORTED_ANALYTICAL_FIELDS
        and canonical not in IDENTIFIER_FIELDS
        and canonical != target
        and canonical != "attrition"
        and canonical != "salary"
    )


def detect_tasks(mappings: dict[str, str], row_count: int) -> list[TaskCandidate]:
    """Return explainable task candidates from the confirmed canonical schema."""
    fields = _fields(mappings)
    candidates: list[TaskCandidate] = []

    attrition = tuple(fields.get("attrition", []))
    attrition_features = _usable_features(mappings, "attrition")
    if attrition and attrition_features and row_count >= 20:
        candidates.append(TaskCandidate(
            "attrition_classification", "FEASIBLE", attrition[0], attrition_features,
            ("Confirmed attrition target and usable heterogeneous HR predictors are present; numeric and categorical predictors can be encoded by the execution engine.",),
        ))
    else:
        reasons = []
        if not attrition: reasons.append("No confirmed attrition field.")
        if not attrition_features: reasons.append("No supported non-identifier HR predictors.")
        if row_count < 20: reasons.append("At least 20 rows are required for the preliminary screen.")
        candidates.append(TaskCandidate("attrition_classification", "BLOCKED", attrition[0] if attrition else None, (), tuple(reasons)))

    salary = tuple(fields.get("salary", []))
    salary_features = _usable_features(mappings, "salary")
    if salary and salary_features and row_count >= 20:
        candidates.append(TaskCandidate(
            "salary_regression", "FEASIBLE", salary[0], salary_features,
            ("Confirmed salary target and usable heterogeneous HR predictors are present; categorical predictors can be encoded by the execution engine.",),
        ))
    else:
        reasons = []
        if not salary: reasons.append("No confirmed salary field.")
        if not salary_features: reasons.append("No supported predictor fields.")
        if row_count < 20: reasons.append("At least 20 rows are required for the preliminary screen.")
        candidates.append(TaskCandidate("salary_regression", "BLOCKED", salary[0] if salary else None, (), tuple(reasons)))

    unsupervised = _usable_features(mappings)
    if len(unsupervised) >= 2 and row_count >= 20:
        candidates.append(TaskCandidate("employee_clustering", "FEASIBLE", None, unsupervised, ("At least two confirmed analytical predictors and sufficient rows are present.",)))
        candidates.append(TaskCandidate("anomaly_detection", "FEASIBLE", None, unsupervised, ("At least two confirmed analytical predictors and sufficient rows are present.",)))
    else:
        reason = ("At least two confirmed analytical predictors and 20 rows are required.",)
        candidates.append(TaskCandidate("employee_clustering", "BLOCKED", None, unsupervised, reason))
        candidates.append(TaskCandidate("anomaly_detection", "BLOCKED", None, unsupervised, reason))

    return candidates
