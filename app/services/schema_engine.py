"""
Canonical HR Schema Engine — M2
================================
Deterministic, multi-signal mapping from arbitrary HR source columns to the
canonical HR ontology defined in docs/SCHEMA_ENGINE.md §5.

Design principles (from SCHEMA_ENGINE.md §2):
  1. Never infer semantic meaning from a column name alone.
  2. Prefer deterministic, inspectable evidence before LLM reasoning.
  3. Every mapping has evidence, confidence, status, and provenance.
  4. Low-confidence mappings must not silently enter consequential analyses.
  5. Unknown columns may remain unmapped.
  6. Canonical schema changes are versioned.

No LLM, no Spark, no network calls in this module.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Optional

from app.models import ColumnProfile, MappingCandidate

# ─────────────────────────────────────────────────────────────
# Versioning
# ─────────────────────────────────────────────────────────────

CANONICAL_SCHEMA_VERSION = "2.0.0"
"""Increment on every breaking change to the canonical field definitions."""


# ─────────────────────────────────────────────────────────────
# Mapping policy thresholds (documented engineering defaults)
# ─────────────────────────────────────────────────────────────

AUTO_MAP_THRESHOLD = 0.75
"""Minimum composite score for AUTO_MAPPED (no competing candidate within GAP_THRESHOLD)."""

NEEDS_REVIEW_THRESHOLD = 0.40
"""Minimum composite score to produce NEEDS_REVIEW rather than UNMAPPED."""

AMBIGUITY_GAP_THRESHOLD = 0.15
"""
If top two candidate scores are within this gap, treat as ambiguous and
downgrade to NEEDS_REVIEW even if the top score is high.
"""

# Score component weights — must sum to 1.0.
W_NAME = 0.50
W_TYPE = 0.20
W_VALUE = 0.20
W_PROFILE = 0.10


# ─────────────────────────────────────────────────────────────
# Sensitivity classification
# ─────────────────────────────────────────────────────────────

class Sensitivity:
    NONE = "NONE"
    QUASI_PII = "QUASI_PII"    # indirectly identifying (age, location, tenure)
    PII = "PII"                # directly identifying (employee_id, manager_id)


# ─────────────────────────────────────────────────────────────
# Canonical field definition
# ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class CanonicalFieldDef:
    """
    Describes one canonical HR concept.

    Attributes
    ----------
    name:
        Canonical field identifier (snake_case, matches SCHEMA_ENGINE.md §5).
    group:
        Ontology group (identity, organisation, workforce, compensation, performance, outcomes).
    aliases:
        Normalised source-name strings that map directly to this field.
    accepted_types:
        Inferred physical types that are compatible with this concept.
    value_set:
        If non-empty, populated sample values should be a subset of these lower-cased strings.
    value_regex:
        If set, sample values are checked against this regex for positive value evidence.
    sensitivity:
        Sensitivity classification of this field.
    min_uniqueness:
        Expected lower bound on uniqueness ratio for this concept.
    max_uniqueness:
        Expected upper bound on uniqueness ratio.
    analytical_objectives:
        Objectives this field can contribute to.
    """
    name: str
    group: str
    aliases: frozenset[str]
    accepted_types: frozenset[str] = field(default_factory=frozenset)
    value_set: frozenset[str] = field(default_factory=frozenset)
    value_regex: Optional[re.Pattern[str]] = None
    sensitivity: str = Sensitivity.NONE
    min_uniqueness: float = 0.0
    max_uniqueness: float = 1.0
    analytical_objectives: tuple[str, ...] = ()


# ─────────────────────────────────────────────────────────────
# Helpers for building the ontology cleanly
# ─────────────────────────────────────────────────────────────

def _fa(*aliases: str) -> frozenset[str]:
    return frozenset(aliases)

def _ft(*types: str) -> frozenset[str]:
    return frozenset(types)

def _fv(*values: str) -> frozenset[str]:
    return frozenset(v.lower() for v in values)

_BINARY_VALUES = _fv("yes", "no", "y", "n", "true", "false", "0", "1")
_RATING_REGEX = re.compile(r"^[1-5]$")
_DATE_REGEX = re.compile(
    r"^(\d{4}[-/]\d{2}[-/]\d{2}|\d{2}[-/]\d{2}[-/]\d{4}|[A-Za-z]+\s+\d{1,2},?\s+\d{4})$"
)
_NUMERIC_TYPES = _ft("numeric")
_CATEGORICAL_TYPES = _ft("categorical", "boolean")
_ANY_TYPES: frozenset[str] = frozenset()


# ─────────────────────────────────────────────────────────────
# The canonical HR ontology (SCHEMA_ENGINE.md §5)
# ─────────────────────────────────────────────────────────────

CANONICAL_FIELDS: dict[str, CanonicalFieldDef] = {
    # ── Identity / entity ────────────────────────────────────────────────────
    "employee_id": CanonicalFieldDef(
        name="employee_id", group="identity",
        aliases=_fa(
            "employee_id", "employeeid", "emp_id", "emp_no", "empno",
            "employee_no", "staff_id", "staffid", "worker_id", "workerid",
            "personnel_id", "personnelid", "eid",
        ),
        accepted_types=_ft("numeric", "categorical"),
        sensitivity=Sensitivity.PII,
        min_uniqueness=0.95,
        analytical_objectives=("all",),
    ),
    "employee_record_id": CanonicalFieldDef(
        name="employee_record_id", group="identity",
        aliases=_fa("employee_record_id", "record_id", "recordid", "row_id"),
        accepted_types=_ft("numeric", "categorical"),
        sensitivity=Sensitivity.PII,
        min_uniqueness=0.95,
    ),
    "employment_status": CanonicalFieldDef(
        name="employment_status", group="identity",
        aliases=_fa(
            "employment_status", "emp_status", "empstatus",
            "status", "employment_state", "active_status",
        ),
        accepted_types=_CATEGORICAL_TYPES,
        sensitivity=Sensitivity.NONE,
    ),

    # ── Organisation ─────────────────────────────────────────────────────────
    "department": CanonicalFieldDef(
        name="department", group="organisation",
        aliases=_fa("department", "dept", "division", "business_division"),
        accepted_types=_CATEGORICAL_TYPES,
        analytical_objectives=("attrition_classification", "employee_clustering", "anomaly_detection"),
    ),
    "business_unit": CanonicalFieldDef(
        name="business_unit", group="organisation",
        aliases=_fa("business_unit", "businessunit", "bu", "unit", "org_unit", "orgunit"),
        accepted_types=_CATEGORICAL_TYPES,
    ),
    "job_role": CanonicalFieldDef(
        name="job_role", group="organisation",
        aliases=_fa(
            "job_role", "jobrole", "role", "job_title", "jobtitle",
            "position", "job_function", "jobfunction", "title",
        ),
        accepted_types=_CATEGORICAL_TYPES,
        analytical_objectives=("attrition_classification", "salary_regression", "employee_clustering"),
    ),
    "job_level": CanonicalFieldDef(
        name="job_level", group="organisation",
        aliases=_fa(
            "job_level", "joblevel", "level", "grade", "pay_grade",
            "paygrade", "band", "job_grade", "jobgrade",
        ),
        accepted_types=_ft("numeric", "categorical"),
        analytical_objectives=("salary_regression", "employee_clustering"),
    ),
    "location": CanonicalFieldDef(
        name="location", group="organisation",
        aliases=_fa(
            "location", "office", "city", "site", "work_location",
            "worklocation", "state", "country", "region",
        ),
        accepted_types=_CATEGORICAL_TYPES,
        sensitivity=Sensitivity.QUASI_PII,
    ),
    "manager_id": CanonicalFieldDef(
        name="manager_id", group="organisation",
        aliases=_fa("manager_id", "managerid", "mgr_id", "mgrid", "supervisor_id", "supervisorid"),
        accepted_types=_ft("numeric", "categorical"),
        sensitivity=Sensitivity.PII,
    ),

    # ── Workforce characteristics ─────────────────────────────────────────────
    "age": CanonicalFieldDef(
        name="age", group="workforce",
        aliases=_fa("age", "employee_age", "emp_age", "age_years"),
        accepted_types=_NUMERIC_TYPES,
        sensitivity=Sensitivity.QUASI_PII,
        min_uniqueness=0.0, max_uniqueness=0.5,
        analytical_objectives=("attrition_classification", "salary_regression", "employee_clustering"),
    ),
    "tenure": CanonicalFieldDef(
        name="tenure", group="workforce",
        aliases=_fa(
            "tenure", "tenure_years", "tenureyears", "years_at_company",
            "yearsatcompany", "years_service", "yearsservice", "yrs",
            "years_with_company", "service_years", "years_employed",
        ),
        accepted_types=_NUMERIC_TYPES,
        analytical_objectives=("attrition_classification", "salary_regression", "employee_clustering"),
    ),
    "hire_date": CanonicalFieldDef(
        name="hire_date", group="workforce",
        aliases=_fa(
            "hire_date", "hiredate", "date_hired", "datehired",
            "start_date", "startdate", "join_date", "joindate",
            "date_of_joining", "dateofjoining", "date_joined",
        ),
        accepted_types=_CATEGORICAL_TYPES,
        value_regex=_DATE_REGEX,
        sensitivity=Sensitivity.QUASI_PII,
    ),
    "termination_date": CanonicalFieldDef(
        name="termination_date", group="workforce",
        aliases=_fa(
            "termination_date", "terminationdate", "date_terminated",
            "exit_date", "exitdate", "leave_date", "leavedate",
            "separation_date", "separationdate",
        ),
        accepted_types=_CATEGORICAL_TYPES,
        value_regex=_DATE_REGEX,
    ),
    "work_mode": CanonicalFieldDef(
        name="work_mode", group="workforce",
        aliases=_fa(
            "work_mode", "workmode", "remote", "remote_work",
            "work_arrangement", "workplace_type", "hybrid",
        ),
        accepted_types=_CATEGORICAL_TYPES,
    ),
    "employment_type": CanonicalFieldDef(
        name="employment_type", group="workforce",
        aliases=_fa(
            "employment_type", "employmenttype", "emp_type",
            "contract_type", "contracttype", "job_type", "jobtype",
            "employee_type", "full_time", "part_time",
        ),
        accepted_types=_CATEGORICAL_TYPES,
    ),

    # ── Compensation ──────────────────────────────────────────────────────────
    "salary": CanonicalFieldDef(
        name="salary", group="compensation",
        aliases=_fa(
            "salary", "monthly_income", "monthlyincome", "annual_salary",
            "annualsalary", "compensation", "pay", "wage", "wages",
            "base_salary", "basesalary", "gross_salary", "grosssalary",
            "total_pay", "income",
        ),
        accepted_types=_NUMERIC_TYPES,
        analytical_objectives=("salary_regression", "employee_clustering"),
    ),
    "bonus": CanonicalFieldDef(
        name="bonus", group="compensation",
        aliases=_fa(
            "bonus", "bonus_amount", "bonusamount", "annual_bonus",
            "annualbonus", "incentive", "variable_pay",
        ),
        accepted_types=_NUMERIC_TYPES,
        analytical_objectives=("salary_regression",),
    ),
    "compensation_band": CanonicalFieldDef(
        name="compensation_band", group="compensation",
        aliases=_fa(
            "compensation_band", "compensationband", "pay_band", "payband",
            "salary_band", "salaryband", "salary_grade", "salarygrade",
        ),
        accepted_types=_CATEGORICAL_TYPES,
    ),

    # ── Performance / engagement ──────────────────────────────────────────────
    "performance_rating": CanonicalFieldDef(
        name="performance_rating", group="performance",
        aliases=_fa(
            "performance_rating", "performancerating", "performance",
            "perf", "perf_rating", "rating", "performance_score",
            "performancescore", "review_score",
        ),
        accepted_types=_ft("numeric", "categorical"),
        value_regex=_RATING_REGEX,
        max_uniqueness=0.4,
        analytical_objectives=("attrition_classification", "salary_regression", "employee_clustering"),
    ),
    "job_satisfaction": CanonicalFieldDef(
        name="job_satisfaction", group="performance",
        aliases=_fa(
            "job_satisfaction", "jobsatisfaction", "satisfaction",
            "job_sat", "work_satisfaction",
        ),
        accepted_types=_ft("numeric", "categorical"),
        value_regex=_RATING_REGEX,
        max_uniqueness=0.4,
        analytical_objectives=("attrition_classification",),
    ),
    "engagement_score": CanonicalFieldDef(
        name="engagement_score", group="performance",
        aliases=_fa(
            "engagement_score", "engagementscore", "engagement",
            "employee_engagement", "survey_score",
        ),
        accepted_types=_NUMERIC_TYPES,
        max_uniqueness=0.6,
    ),
    "training_hours": CanonicalFieldDef(
        name="training_hours", group="performance",
        aliases=_fa(
            "training_hours", "traininghours", "training_time",
            "training_completed", "hours_trained",
        ),
        accepted_types=_NUMERIC_TYPES,
    ),
    "absence_days": CanonicalFieldDef(
        name="absence_days", group="performance",
        aliases=_fa(
            "absence_days", "absencedays", "absent_days", "absenteeism",
            "leave_days", "leavedays", "days_absent",
        ),
        accepted_types=_NUMERIC_TYPES,
    ),
    "overtime": CanonicalFieldDef(
        name="overtime", group="performance",
        aliases=_fa("overtime", "over_time", "overtime_flag", "ot"),
        accepted_types=_CATEGORICAL_TYPES,
        value_set=_BINARY_VALUES,
        analytical_objectives=("attrition_classification",),
    ),

    # ── Career outcomes ───────────────────────────────────────────────────────
    "promotion_status": CanonicalFieldDef(
        name="promotion_status", group="outcomes",
        aliases=_fa(
            "promotion_status", "promotionstatus", "prm_st",
            "promoted", "promotion_flag", "was_promoted",
        ),
        accepted_types=_CATEGORICAL_TYPES,
        value_set=_BINARY_VALUES,
        max_uniqueness=0.3,
        analytical_objectives=("attrition_classification",),
    ),
    "promotion_date": CanonicalFieldDef(
        name="promotion_date", group="outcomes",
        aliases=_fa(
            "promotion_date", "promotiondate", "last_promotion",
            "lastpromotion", "date_promoted",
        ),
        accepted_types=_CATEGORICAL_TYPES,
        value_regex=_DATE_REGEX,
    ),
    "attrition": CanonicalFieldDef(
        name="attrition", group="outcomes",
        aliases=_fa(
            "attrition", "left_org", "left_company", "terminated",
            "termination_flag", "churn", "churned", "turnover",
            "voluntary_exit", "resigned", "is_attrition",
        ),
        accepted_types=_CATEGORICAL_TYPES,
        value_set=_BINARY_VALUES,
        max_uniqueness=0.3,
        analytical_objectives=("attrition_classification",),
    ),
    "termination_reason": CanonicalFieldDef(
        name="termination_reason", group="outcomes",
        aliases=_fa(
            "termination_reason", "terminationreason", "exit_reason",
            "exitreason", "separation_reason", "separation_type",
            "attrition_reason", "attritionreason",
        ),
        accepted_types=_CATEGORICAL_TYPES,
    ),
}


# ─────────────────────────────────────────────────────────────
# Public helpers
# ─────────────────────────────────────────────────────────────

def canonical_field_names() -> set[str]:
    """Return the full set of valid canonical field names plus 'unknown'."""
    return set(CANONICAL_FIELDS.keys()) | {"unknown"}


def normalize_name(raw: str) -> str:
    """
    Deterministic column-name normalisation.

    Steps:
      1. camelCase → snake_case
      2. lower-case
      3. replace non-alphanumeric characters with '_'
      4. collapse consecutive underscores
      5. strip leading/trailing underscores
    """
    raw = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", raw)
    raw = raw.lower()
    raw = re.sub(r"[^a-z0-9]+", "_", raw)
    raw = re.sub(r"_+", "_", raw)
    return raw.strip("_")


def schema_fingerprint(headers: list[str]) -> str:
    """
    Compute a stable SHA-256 fingerprint of a dataset's column names.

    The fingerprint is computed over the *sorted* normalized header list so
    that column order does not affect identity.
    """
    normalized = sorted(normalize_name(h) for h in headers)
    raw = ",".join(normalized).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


# ─────────────────────────────────────────────────────────────
# Evidence scoring — pure functions, no side effects
# ─────────────────────────────────────────────────────────────

def score_name_evidence(normalized: str, field_def: CanonicalFieldDef) -> float:
    """
    Name evidence score [0, 1].

    - Exact alias match: 1.0
    - All canonical tokens present in normalized name tokens: 0.7
    - Normalized name tokens are a subset of canonical tokens: 0.6
    - Otherwise: 0.0
    """
    if normalized in field_def.aliases:
        return 1.0
    norm_tokens = set(normalized.split("_")) - {""}
    canon_tokens = set(field_def.name.split("_")) - {""}
    if norm_tokens and canon_tokens and canon_tokens <= norm_tokens:
        return 0.7
    if norm_tokens and canon_tokens and norm_tokens <= canon_tokens:
        return 0.6
    return 0.0


def score_type_evidence(inferred_type: str, field_def: CanonicalFieldDef) -> float:
    """
    Type compatibility score [0, 1].

    - Empty accepted_types → 0.5 (neutral).
    - Exact type match → 1.0.
    - Otherwise → 0.0.
    """
    if not field_def.accepted_types:
        return 0.5
    return 1.0 if inferred_type in field_def.accepted_types else 0.0


def score_value_evidence(sample_values: list[str], field_def: CanonicalFieldDef) -> float:
    """
    Value-pattern evidence score [0, 1].

    - No value constraints → 0.5 (neutral).
    - value_set: hit_rate >= 0.8 → 1.0, >= 0.5 → 0.6, else 0.0.
    - value_regex: hit_rate >= 0.8 → 1.0, >= 0.5 → 0.6, else 0.0.
    """
    populated = [v.strip().lower() for v in sample_values if v and v.strip()]
    if not populated:
        return 0.5

    if field_def.value_set:
        hit_rate = sum(1 for v in populated if v in field_def.value_set) / len(populated)
        if hit_rate >= 0.8:
            return 1.0
        if hit_rate >= 0.5:
            return 0.6
        return 0.0

    if field_def.value_regex:
        hit_rate = sum(1 for v in populated if field_def.value_regex.match(v)) / len(populated)
        if hit_rate >= 0.8:
            return 1.0
        if hit_rate >= 0.5:
            return 0.6
        return 0.0

    return 0.5


def score_profile_evidence(col: ColumnProfile, field_def: CanonicalFieldDef) -> float:
    """
    Statistical profile evidence score [0, 1].

    Uses uniqueness_ratio against expected range.
    """
    score = 0.5
    u = col.uniqueness_ratio
    if field_def.min_uniqueness <= u <= field_def.max_uniqueness:
        score = min(score + 0.5, 1.0)
    elif u < field_def.min_uniqueness or u > field_def.max_uniqueness:
        score = max(score - 0.3, 0.0)
    return round(score, 4)


def compute_mapping_score(col: ColumnProfile, field_def: CanonicalFieldDef) -> tuple[float, float, float, float, float]:
    """
    Compute weighted composite mapping confidence score.

    Returns (composite, name_score, type_score, value_score, profile_score).
    """
    n = score_name_evidence(col.normalized_name, field_def)
    t = score_type_evidence(col.inferred_type, field_def)
    v = score_value_evidence(col.sample_values, field_def)
    p = score_profile_evidence(col, field_def)
    composite = round(W_NAME * n + W_TYPE * t + W_VALUE * v + W_PROFILE * p, 4)
    return composite, n, t, v, p


# ─────────────────────────────────────────────────────────────
# Column mapper
# ─────────────────────────────────────────────────────────────

def map_column(col: ColumnProfile) -> MappingCandidate:
    """
    Map a single ColumnProfile to the canonical ontology.

    Decision policy:
      - score >= AUTO_MAP_THRESHOLD AND gap >= AMBIGUITY_GAP_THRESHOLD → AUTO_MAPPED
      - score >= NEEDS_REVIEW_THRESHOLD → NEEDS_REVIEW
      - score < NEEDS_REVIEW_THRESHOLD → UNMAPPED
    """
    scored = []
    for fname, fdef in CANONICAL_FIELDS.items():
        composite, n, t, v, p = compute_mapping_score(col, fdef)
        scored.append((composite, n, t, v, p, fname))

    scored.sort(key=lambda x: x[0], reverse=True)

    top_score, n1, t1, v1, p1, top_field = scored[0]
    second_score = scored[1][0] if len(scored) > 1 else 0.0
    gap = top_score - second_score

    alternatives = [s[5] for s in scored[1:4] if s[0] >= NEEDS_REVIEW_THRESHOLD]

    evidence = []
    if n1 >= 1.0:
        evidence.append("exact_alias_match")
    elif n1 >= 0.7:
        evidence.append("partial_name_token_match")
    if t1 >= 1.0:
        evidence.append("type_compatible")
    if v1 >= 0.9:
        evidence.append("value_pattern_match")
    elif v1 >= 0.5:
        evidence.append("value_pattern_partial")
    if p1 >= 0.9:
        evidence.append("profile_compatible")

    # Without name evidence (n1 == 0) and without strong value evidence (v1 < 0.8),
    # a column cannot be mapped on generic physical type / uniqueness alone.
    if top_score < NEEDS_REVIEW_THRESHOLD or (n1 == 0.0 and v1 < 0.8):
        decision = "UNMAPPED"
        canonical = "unknown"
        evidence = ["no_deterministic_alias_match"]
        alternatives = []
        n1 = t1 = v1 = p1 = 0.0
        top_score = 0.0
    elif top_score >= AUTO_MAP_THRESHOLD and gap >= AMBIGUITY_GAP_THRESHOLD:
        decision = "AUTO_MAPPED"
        canonical = top_field
    else:  # top_score >= NEEDS_REVIEW_THRESHOLD
        decision = "NEEDS_REVIEW"
        canonical = top_field
        if not evidence:
            evidence.append("low_confidence_match")
        if gap < AMBIGUITY_GAP_THRESHOLD and len(alternatives) > 0:
            evidence.append("ambiguous_candidates")

    return MappingCandidate(
        canonical_field=canonical,
        confidence=top_score,
        decision=decision,
        evidence=evidence,
        alternatives=alternatives,
        name_score=round(n1, 4),
        type_score=round(t1, 4),
        value_score=round(v1, 4),
        profile_score=round(p1, 4),
    )


# ─────────────────────────────────────────────────────────────
# Collision detection
# ─────────────────────────────────────────────────────────────

def detect_collisions(mappings: dict[str, MappingCandidate]) -> dict[str, MappingCandidate]:
    """
    Detect cases where multiple source columns map to the same canonical field.

    Returns a new dict with collision sources downgraded to NEEDS_REVIEW.
    """
    collisions: dict[str, list[str]] = {}
    for source, m in mappings.items():
        if m.canonical_field != "unknown":
            collisions.setdefault(m.canonical_field, []).append(source)

    result = dict(mappings)
    for canonical_field, sources in collisions.items():
        if len(sources) > 1:
            for source in sources:
                m = result[source]
                result[source] = MappingCandidate(
                    canonical_field=m.canonical_field,
                    confidence=m.confidence,
                    decision="NEEDS_REVIEW",
                    evidence=m.evidence + ["canonical_mapping_collision"],
                    alternatives=m.alternatives,
                    name_score=m.name_score,
                    type_score=m.type_score,
                    value_score=m.value_score,
                    profile_score=m.profile_score,
                )
    return result
