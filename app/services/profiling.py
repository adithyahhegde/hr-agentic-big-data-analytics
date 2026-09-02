from __future__ import annotations

from app.config import get_settings
from app.models import ColumnProfile, DatasetProfile, Issue, Severity, MappingCandidate
from app.services.data_quality import compute_numeric_stats, generate_data_quality_report_for_rows
from app.services.local_llm import LocalLLMError, resolve_ambiguous_mapping
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


def _apply_local_llm_fallback(
    columns: list[ColumnProfile],
    mappings: dict[str, MappingCandidate],
) -> tuple[dict[str, MappingCandidate], bool, list[Issue]]:
    """Resolve only ambiguous deterministic mappings using optional local Ollama."""
    settings = get_settings()
    if not settings.allow_local_llm:
        return mappings, False, []

    result = dict(mappings)
    issues: list[Issue] = []
    used = False
    profiles = {column.source_name: column for column in columns}

    for source_name, mapping in mappings.items():
        if mapping.decision != "NEEDS_REVIEW" or not mapping.alternatives:
            continue

        profile = profiles[source_name]
        candidates = [mapping.canonical_field, *mapping.alternatives]
        candidates = list(dict.fromkeys(candidates))
        try:
            decision = resolve_ambiguous_mapping(
                source_name=source_name,
                inferred_type=profile.inferred_type,
                uniqueness_ratio=profile.uniqueness_ratio,
                sample_values=profile.sample_values,
                candidates=candidates,
                base_url=settings.local_llm_base_url,
                model=settings.local_llm_model,
                timeout_seconds=settings.local_llm_timeout_seconds,
            )
        except LocalLLMError:
            # The deterministic decision remains authoritative when local inference fails.
            issues.append(
                Issue(
                    code="LOCAL_LLM_FALLBACK_UNAVAILABLE",
                    severity=Severity.info,
                    message="Local LLM evidence was unavailable; deterministic mapping retained.",
                    column=source_name,
                )
            )
            continue

        result[source_name] = MappingCandidate(
            canonical_field=decision.canonical_field,
            confidence=mapping.confidence,
            decision="NEEDS_REVIEW",
            evidence=[*mapping.evidence, "local_llm_candidate_support"],
            alternatives=[c for c in candidates if c != decision.canonical_field],
            name_score=mapping.name_score,
            type_score=mapping.type_score,
            value_score=mapping.value_score,
            profile_score=mapping.profile_score,
        )
        used = True

    return result, used, issues


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

    # M2: deterministic multi-signal mapping is always performed first.
    raw_mappings = {col.source_name: map_column(col) for col in columns}
    mappings = detect_collisions(raw_mappings)

    # M3: optional local LLM is a bounded evidence source for unresolved ambiguity only.
    mappings, llm_used, llm_issues = _apply_local_llm_fallback(columns, mappings)
    base_issues.extend(llm_issues)

    # Re-run collision detection after LLM-supported candidate selection.
    mappings = detect_collisions(mappings)

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
        llm_used=llm_used,
        schema_version=CANONICAL_SCHEMA_VERSION,
        dataset_fingerprint=schema_fingerprint(headers),
    )
