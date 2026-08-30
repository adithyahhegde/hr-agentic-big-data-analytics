from __future__ import annotations

import re
from app.models import ColumnProfile, Severity
from app.services.schema_engine import (
    AMBIGUITY_GAP_THRESHOLD,
    AUTO_MAP_THRESHOLD,
    CANONICAL_FIELDS,
    CANONICAL_SCHEMA_VERSION,
    NEEDS_REVIEW_THRESHOLD,
    CanonicalFieldDef,
    canonical_field_names,
    compute_mapping_score,
    detect_collisions,
    map_column,
    normalize_name,
    schema_fingerprint,
    score_name_evidence,
    score_profile_evidence,
    score_type_evidence,
    score_value_evidence,
)
from app.services.profiling import profile_dataset


def test_canonical_ontology_integrity():
    """Verify all canonical fields defined in SCHEMA_ENGINE.md §5 are present and valid."""
    assert len(CANONICAL_FIELDS) >= 28  # all core ontology concepts
    names = canonical_field_names()
    assert "unknown" in names
    assert "employee_id" in names
    assert "attrition" in names
    assert "salary" in names
    assert "performance_rating" in names

    for field_name, fdef in CANONICAL_FIELDS.items():
        assert fdef.name == field_name
        assert len(fdef.group) > 0
        assert len(fdef.aliases) > 0
        assert fdef.min_uniqueness >= 0.0
        assert fdef.max_uniqueness <= 1.0


def test_normalize_name():
    """Verify deterministic name normalization handles camelCase, punctuation, and whitespace."""
    assert normalize_name("EmployeeId") == "employee_id"
    assert normalize_name("emp_no") == "emp_no"
    assert normalize_name("Years At Company") == "years_at_company"
    assert normalize_name("salary ($ USD)") == "salary_usd"
    assert normalize_name("___department___") == "department"
    assert normalize_name("leftOrg") == "left_org"
    assert normalize_name("PerfRating2026") == "perf_rating2026"


def test_schema_fingerprint_deterministic():
    """Verify dataset fingerprint is order-invariant and deterministic."""
    headers1 = ["emp_id", "dept", "salary", "attrition"]
    headers2 = ["attrition", "salary", "dept", "emp_id"]
    headers3 = ["emp_id", "dept", "salary", "age"]

    fp1 = schema_fingerprint(headers1)
    fp2 = schema_fingerprint(headers2)
    fp3 = schema_fingerprint(headers3)

    assert len(fp1) == 64
    assert fp1 == fp2  # Order-invariant
    assert fp1 != fp3  # Different headers produce different fingerprint


def test_score_name_evidence():
    """Verify alias scoring: exact matches, token matches, and non-matches."""
    emp_def = CANONICAL_FIELDS["employee_id"]
    assert score_name_evidence("emp_no", emp_def) == 1.0
    assert score_name_evidence("employee_id", emp_def) == 1.0
    assert score_name_evidence("unrelated_notes", emp_def) == 0.0


def test_score_type_evidence():
    """Verify physical/logical type compatibility scoring."""
    salary_def = CANONICAL_FIELDS["salary"]
    assert score_type_evidence("numeric", salary_def) == 1.0
    assert score_type_evidence("categorical", salary_def) == 0.0

    dept_def = CANONICAL_FIELDS["department"]
    assert score_type_evidence("categorical", dept_def) == 1.0
    assert score_type_evidence("boolean", dept_def) == 1.0


def test_score_value_evidence():
    """Verify value-pattern evidence evaluation on bounded samples."""
    attrition_def = CANONICAL_FIELDS["attrition"]
    assert score_value_evidence(["Yes", "No", "Yes", "No"], attrition_def) == 1.0
    assert score_value_evidence(["Active", "Resigned"], attrition_def) == 0.0

    perf_def = CANONICAL_FIELDS["performance_rating"]
    assert score_value_evidence(["1", "3", "5", "4", "2"], perf_def) == 1.0
    assert score_value_evidence(["999", "abc"], perf_def) == 0.0

    hire_def = CANONICAL_FIELDS["hire_date"]
    assert score_value_evidence(["2020-01-15", "2019-06-30"], hire_def) == 1.0


def test_score_profile_evidence():
    """Verify profile evidence incorporates uniqueness ratio."""
    emp_def = CANONICAL_FIELDS["employee_id"]
    col_unique = ColumnProfile(
        source_name="emp_id",
        normalized_name="emp_id",
        inferred_type="numeric",
        non_null_count=100,
        null_count=0,
        missing_percentage=0.0,
        unique_count=100,
        uniqueness_ratio=1.0,
    )
    assert score_profile_evidence(col_unique, emp_def) == 1.0


def test_map_column_auto_mapped():
    """Verify standard high-confidence column maps to AUTO_MAPPED."""
    col = ColumnProfile(
        source_name="MonthlyIncome",
        normalized_name="monthly_income",
        inferred_type="numeric",
        non_null_count=100,
        null_count=0,
        missing_percentage=0.0,
        unique_count=90,
        uniqueness_ratio=0.9,
        sample_values=["5000", "6200", "4800"],
    )
    mapping = map_column(col)
    assert mapping.canonical_field == "salary"
    assert mapping.decision == "AUTO_MAPPED"
    assert mapping.confidence >= AUTO_MAP_THRESHOLD
    assert "exact_alias_match" in mapping.evidence
    assert "type_compatible" in mapping.evidence
    assert mapping.name_score == 1.0


def test_map_column_unmapped():
    """Verify completely unrecognized column is marked UNMAPPED with unknown canonical field."""
    col = ColumnProfile(
        source_name="random_custom_hash_999",
        normalized_name="random_custom_hash_999",
        inferred_type="categorical",
        non_null_count=50,
        null_count=0,
        missing_percentage=0.0,
        unique_count=50,
        uniqueness_ratio=1.0,
        sample_values=["a1b2", "c3d4"],
    )
    mapping = map_column(col)
    assert mapping.canonical_field == "unknown"
    assert mapping.decision == "UNMAPPED"
    assert mapping.confidence == 0.0
    assert "no_deterministic_alias_match" in mapping.evidence


def test_detect_collisions_and_downgrade():
    """Verify mapping collisions downgrade candidates to NEEDS_REVIEW."""
    col1 = ColumnProfile(
        source_name="emp_no",
        normalized_name="emp_no",
        inferred_type="numeric",
        non_null_count=10,
        null_count=0,
        missing_percentage=0.0,
        unique_count=10,
        uniqueness_ratio=1.0,
    )
    col2 = ColumnProfile(
        source_name="employee_id",
        normalized_name="employee_id",
        inferred_type="numeric",
        non_null_count=10,
        null_count=0,
        missing_percentage=0.0,
        unique_count=10,
        uniqueness_ratio=1.0,
    )
    raw = {
        "emp_no": map_column(col1),
        "employee_id": map_column(col2),
    }
    assert raw["emp_no"].canonical_field == "employee_id"
    assert raw["employee_id"].canonical_field == "employee_id"

    resolved = detect_collisions(raw)
    assert resolved["emp_no"].decision == "NEEDS_REVIEW"
    assert resolved["employee_id"].decision == "NEEDS_REVIEW"
    assert "canonical_mapping_collision" in resolved["emp_no"].evidence
    assert "canonical_mapping_collision" in resolved["employee_id"].evidence


def test_reproducibility():
    """Verify identical ColumnProfile produces identical MappingCandidate deterministically."""
    col = ColumnProfile(
        source_name="yrs_service",
        normalized_name="yrs_service",
        inferred_type="numeric",
        non_null_count=20,
        null_count=0,
        missing_percentage=0.0,
        unique_count=15,
        uniqueness_ratio=0.75,
        sample_values=["3", "5", "10"],
    )
    m1 = map_column(col)
    m2 = map_column(col)
    assert m1.model_dump() == m2.model_dump()


def test_profile_dataset_schema_provenance():
    """Verify DatasetProfile contains schema_version and dataset_fingerprint."""
    headers = ["emp_id", "job_role", "salary"]
    rows = [{"emp_id": "1", "job_role": "Engineer", "salary": "80000"}]
    profile = profile_dataset(headers, rows)
    assert profile.schema_version == CANONICAL_SCHEMA_VERSION
    assert len(profile.dataset_fingerprint) == 64
    assert profile.mappings["emp_id"].name_score > 0.0
    assert profile.mappings["job_role"].canonical_field == "job_role"
