from __future__ import annotations

import re

from app.models import ColumnProfile, DatasetProfile, Issue, Severity
from app.services.data_quality import compute_numeric_stats, generate_data_quality_report_for_rows
from app.services.schema_engine import (
    CANONICAL_SCHEMA_VERSION,
    canonical_field_names,
    detect_collisions,
    map_column,
    normalize_name,
    schema_fingerprint,
)


def canonical_fields() -> set[str]:
    """Public re-export used by app/main.py for schema acceptance validation."""
    return canonical_field_names()


def normalize_column_name(value: str) -> str:
    """Compatibility alias — delegates to schema_engine.normalize_name."""
    return normalize_name(value)


def _infer_type(values: list[str]) -> str:
    """Infer the physical column type from populated sample values."""
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


def profile_dataset(headers: list[str], rows: list[dict[str, str]]) -> DatasetProfile:
    columns: list[ColumnProfile] = []
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
            normalized_name=normalize_name(header),
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

    # M2: multi-signal mapping via schema_engine
    raw_mappings = {col.source_name: map_column(col) for col in columns}

    # M2: collision detection — multiple sources → same canonical
    mappings = detect_collisions(raw_mappings)

    # Emit MAPPING_COLLISION issues for any collisions detected
    seen_collisions: set[str] = set()
    for source, m in mappings.items():
        if "canonical_mapping_collision" in m.evidence and m.canonical_field not in seen_collisions:
            seen_collisions.add(m.canonical_field)
            sources_in_collision = [
                s for s, mc in mappings.items()
                if mc.canonical_field == m.canonical_field and "canonical_mapping_collision" in mc.evidence
            ]
            base_issues.append(
                Issue(
                    code="MAPPING_COLLISION",
                    severity=Severity.blocking,
                    message=f"Multiple source columns map to {m.canonical_field}; confirm one mapping.",
                    column=", ".join(sources_in_collision),
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
        schema_version=CANONICAL_SCHEMA_VERSION,
        dataset_fingerprint=schema_fingerprint(headers),
    )
