from __future__ import annotations

from collections import Counter
import re

from app.models import ColumnProfile, DatasetProfile, Issue, MappingCandidate, Severity
from app.services.data_quality import compute_numeric_stats, generate_data_quality_report_for_rows

CANONICAL_ALIASES = {
    "employee_id": {"employee_id", "employeeid", "emp_id", "emp_no", "employee_no", "staff_id"},
    "department": {"department", "dept", "business_unit"},
    "job_role": {"job_role", "role", "job_title", "position"},
    "age": {"age", "employee_age"},
    "tenure_years": {"tenure", "tenure_years", "years_at_company", "yrs", "years_service"},
    "salary": {"salary", "monthly_income", "annual_salary", "compensation"},
    "performance_rating": {"performance_rating", "performance", "perf", "rating"},
    "attrition": {"attrition", "left_org", "left_company", "terminated", "termination_flag"},
    "overtime": {"overtime", "over_time"},
}


def canonical_fields() -> set[str]:
    return set(CANONICAL_ALIASES) | {"unknown"}


def normalize_column_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def _infer_type(values: list[str]) -> str:
    populated = [value for value in values if value]
    if not populated:
        return "unknown"
    lowered = {value.lower() for value in populated}
    if lowered <= {"yes", "no", "y", "n", "true", "false", "0", "1"}:
        return "boolean"
    try:
        [float(value) for value in populated]
        return "numeric"
    except ValueError:
        return "categorical"


def _mapping_for(name: str, values: list[str]) -> MappingCandidate:
    normalized = normalize_column_name(name)
    matches = [field for field, aliases in CANONICAL_ALIASES.items() if normalized in aliases]
    if len(matches) == 1:
        evidence = ["normalized_name_alias"]
        field = matches[0]
        confidence = 0.9
        if field == "attrition" and {v.lower() for v in values if v} <= {"yes", "no", "y", "n", "0", "1", "true", "false"}:
            confidence = 0.96
            evidence.append("binary_value_pattern")
        return MappingCandidate(canonical_field=field, confidence=confidence, decision="AUTO_MAPPED", evidence=evidence)
    return MappingCandidate(canonical_field="unknown", confidence=0.0, decision="UNMAPPED", evidence=["no_deterministic_alias_match"])


def profile_dataset(headers: list[str], rows: list[dict[str, str]]) -> DatasetProfile:
    columns: list[ColumnProfile] = []
    mappings: dict[str, MappingCandidate] = {}
    base_issues: list[Issue] = []

    for header in headers:
        values = [row[header] for row in rows]
        populated = [value for value in values if value]
        non_null_count = len(populated)
        null_count = len(values) - non_null_count
        unique_count = len(set(populated))
        missing_pct = round(null_count / len(values), 4) if values else 0.0
        uniq_ratio = round(unique_count / non_null_count, 4) if non_null_count else 0.0

        profile = ColumnProfile(
            source_name=header,
            normalized_name=normalize_column_name(header),
            inferred_type=_infer_type(values),
            non_null_count=non_null_count,
            null_count=null_count,
            missing_percentage=missing_pct,
            unique_count=unique_count,
            uniqueness_ratio=uniq_ratio,
            sample_values=list(dict.fromkeys(populated))[:5],
            numeric_stats=compute_numeric_stats(values),
        )
        columns.append(profile)
        mappings[header] = _mapping_for(header, values)

        if profile.null_count:
            base_issues.append(
                Issue(
                    code="MISSING_VALUES",
                    severity=Severity.warning,
                    message=f"{profile.null_count} values ({missing_pct:.1%}) are missing.",
                    column=header,
                )
            )
        if profile.unique_count <= 1:
            base_issues.append(
                Issue(
                    code="CONSTANT_OR_EMPTY_COLUMN",
                    severity=Severity.warning,
                    message="The column has at most one populated value.",
                    column=header,
                )
            )

    collisions: dict[str, list[str]] = {}
    for source, mapping in mappings.items():
        if mapping.canonical_field != "unknown":
            collisions.setdefault(mapping.canonical_field, []).append(source)
    for field, sources in collisions.items():
        if len(sources) > 1:
            for source in sources:
                mappings[source] = MappingCandidate(
                    canonical_field=field,
                    confidence=mappings[source].confidence,
                    decision="NEEDS_REVIEW",
                    evidence=mappings[source].evidence + ["canonical_mapping_collision"],
                )
            base_issues.append(
                Issue(
                    code="MAPPING_COLLISION",
                    severity=Severity.blocking,
                    message=f"Multiple source columns map to {field}; confirm one mapping.",
                    column=", ".join(sources),
                )
            )

    dq_report, all_issues = generate_data_quality_report_for_rows(
        headers=headers,
        rows=rows,
        columns=columns,
        existing_issues=base_issues,
    )

    duplicate_rows = dq_report.metrics.duplicate_row_count

    return DatasetProfile(
        row_count=len(rows),
        column_count=len(headers),
        duplicate_row_count=duplicate_rows,
        columns=columns,
        mappings=mappings,
        issues=all_issues,
        data_quality=dq_report,
    )

