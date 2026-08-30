from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import re

from app.models import (
    ColumnProfile,
    DataQualityMetrics,
    DataQualityReport,
    Issue,
    NumericStats,
    QualityRuleResult,
    RuleStatus,
    Severity,
)

PII_EMAIL_REGEX = re.compile(r"^[\w\.\+\-]+@[\w\.\-]+\.[a-zA-Z]{2,}$")
PII_PHONE_REGEX = re.compile(r"^\+?[0-9\-\(\)\s]{7,20}$")
PII_SSN_REGEX = re.compile(r"^(?:\d{3}-\d{2}-\d{4}|\d{9})$")


@dataclass(frozen=True)
class DataQualityConfig:
    """Configurable heuristics and thresholds for the Data Quality Engine."""
    min_age_heuristic: float = 16.0
    max_age_heuristic: float = 100.0
    max_tenure_heuristic: float = 70.0
    allow_negative_salary: bool = False
    high_missingness_threshold: float = 0.20
    critical_missingness_threshold: float = 0.80
    pii_sample_limit: int = 50


DEFAULT_QUALITY_CONFIG = DataQualityConfig()


@dataclass(frozen=True)
class DatasetSummaryStats:
    """Engine-agnostic dataset summary metrics for in-memory, streaming, or distributed engines."""
    row_count: int
    column_count: int
    duplicate_row_count: int = 0
    empty_row_count: int = 0
    clean_row_count: int = 0


def summarize_in_memory_dataset(
    headers: list[str], rows: list[dict[str, str]]
) -> DatasetSummaryStats:
    """Compute dataset summary statistics in a memory-efficient single pass."""
    row_count = len(rows)
    column_count = len(headers)
    if row_count == 0 or column_count == 0:
        return DatasetSummaryStats(row_count=row_count, column_count=column_count)

    empty_row_count = 0
    clean_row_count = 0
    row_counter: Counter[tuple[str, ...]] = Counter()

    for row in rows:
        row_tuple = tuple(row.get(h, "") for h in headers)
        row_counter[row_tuple] += 1
        is_empty = True
        is_clean = True
        for val in row_tuple:
            stripped = val.strip()
            if stripped:
                is_empty = False
            else:
                is_clean = False
        if is_empty:
            empty_row_count += 1
        if is_clean:
            clean_row_count += 1

    duplicate_row_count = sum(count - 1 for count in row_counter.values() if count > 1)

    return DatasetSummaryStats(
        row_count=row_count,
        column_count=column_count,
        duplicate_row_count=duplicate_row_count,
        empty_row_count=empty_row_count,
        clean_row_count=clean_row_count,
    )


def compute_numeric_stats(values: list[str]) -> NumericStats | None:
    """Safely compute numeric distribution summary without materializing non-numeric rows."""
    populated = [v.strip() for v in values if v and v.strip()]
    if not populated:
        return None
    numbers: list[float] = []
    zeros_count = 0
    negatives_count = 0
    for v in populated:
        try:
            num = float(v)
            numbers.append(num)
            if num == 0.0:
                zeros_count += 1
            elif num < 0.0:
                negatives_count += 1
        except ValueError:
            return None
    if not numbers:
        return None
    return NumericStats(
        min=round(min(numbers), 4),
        max=round(max(numbers), 4),
        mean=round(sum(numbers) / len(numbers), 4),
        zeros_count=zeros_count,
        negatives_count=negatives_count,
    )


def detect_pii_signals(
    source_name: str,
    values: list[str],
    sample_limit: int = 50,
) -> list[str]:
    """
    Detect heuristic sensitive/PII data signals on a bounded sample of values.
    
    IMPORTANT: This is a heuristic sample scan. Detecting no signals DOES NOT guarantee
    absence of sensitive data across the entire dataset. Raw sensitive values are never
    persisted or returned in outputs.
    """
    signals: list[str] = []
    lowered_name = source_name.lower().replace("_", "").replace("-", "")
    populated = [v.strip() for v in values if v and v.strip()]
    sample = populated[:sample_limit]

    # Email pattern signal
    if any(k in lowered_name for k in ["email", "e_mail", "mail"]) or (
        sample and any(PII_EMAIL_REGEX.match(v) for v in sample)
    ):
        signals.append("email_address")

    # Phone pattern signal
    if any(k in lowered_name for k in ["phone", "mobile", "cell", "tel"]) or (
        sample and sum(1 for v in sample if PII_PHONE_REGEX.match(v)) >= max(1, len(sample) * 0.7)
    ):
        signals.append("phone_number")

    # SSN / National ID pattern signal
    if any(k in lowered_name for k in ["ssn", "socialsecurity", "nationalid", "aadhaar", "sin"]) or (
        sample and any(PII_SSN_REGEX.match(v) for v in sample)
    ):
        signals.append("national_id_or_ssn")

    return signals


def evaluate_domain_validity(
    source_name: str,
    normalized_name: str,
    values: list[str],
    config: DataQualityConfig = DEFAULT_QUALITY_CONFIG,
) -> list[tuple[Severity, str, str]]:
    """
    Evaluate domain validity against configurable sanity heuristics.
    Never output raw unmasked values in issue messages.
    """
    findings: list[tuple[Severity, str, str]] = []
    populated = [v.strip() for v in values if v and v.strip()]
    if not populated:
        return findings

    # Age domain heuristic validation
    if normalized_name in {"age", "employee_age"}:
        for v in populated:
            try:
                num = float(v)
                if num < config.min_age_heuristic or num > config.max_age_heuristic:
                    findings.append(
                        (
                            Severity.warning,
                            "AGE_OUT_OF_RANGE",
                            f"Age value outside configured heuristic employment range [{config.min_age_heuristic:.0f}, {config.max_age_heuristic:.0f}] detected (heuristic check).",
                        )
                    )
                    break
            except ValueError:
                findings.append(
                    (
                        Severity.warning,
                        "NON_NUMERIC_AGE",
                        "Non-numeric value detected in age column.",
                    )
                )
                break

    # Salary/Compensation domain heuristic validation
    if normalized_name in {"salary", "monthly_income", "annual_salary", "compensation", "pay"}:
        for v in populated:
            try:
                num = float(v)
                if num < 0 and not config.allow_negative_salary:
                    findings.append(
                        (
                            Severity.blocking,
                            "NEGATIVE_COMPENSATION",
                            "Negative compensation value detected. Compensation cannot be negative under configured heuristic rules.",
                        )
                    )
                    break
            except ValueError:
                pass

    # Tenure domain heuristic validation
    if normalized_name in {"tenure", "tenure_years", "years_at_company", "years_service"}:
        for v in populated:
            try:
                num = float(v)
                if num < 0:
                    findings.append(
                        (
                            Severity.warning,
                            "NEGATIVE_TENURE",
                            "Negative tenure value detected. Tenure cannot be negative under configured heuristic rules.",
                        )
                    )
                    break
                elif num > config.max_tenure_heuristic:
                    findings.append(
                        (
                            Severity.warning,
                            "HIGH_TENURE_OUTLIER",
                            f"Tenure value outside plausible heuristic range [0, {config.max_tenure_heuristic:.0f}] years detected.",
                        )
                    )
                    break
            except ValueError:
                pass

    return findings


def generate_data_quality_report(
    columns: list[ColumnProfile],
    summary_stats: DatasetSummaryStats,
    sample_values_by_column: dict[str, list[str]] | None = None,
    existing_issues: list[Issue] | None = None,
    config: DataQualityConfig = DEFAULT_QUALITY_CONFIG,
) -> tuple[DataQualityReport, list[Issue]]:
    """
    Generate a deterministic Data Quality Report and Dataset Health Score.
    
    This function accepts summary statistics and column profiles so that future
    distributed engines (e.g. PySpark) can produce reports from distributed aggregations
    without materializing full datasets into Python driver memory.
    """
    row_count = summary_stats.row_count
    column_count = summary_stats.column_count
    total_cells = row_count * column_count if (row_count and column_count) else 0

    all_issues: list[Issue] = list(existing_issues or [])
    rules: list[QualityRuleResult] = []

    # 0. Empty dataset handling
    if row_count == 0:
        msg = "The dataset contains no data rows."
        rules.append(
            QualityRuleResult(
                rule_name="non_empty_dataset",
                category="completeness",
                status=RuleStatus.failed,
                severity=Severity.critical,
                message=msg,
                metric_value=0.0,
                threshold=1.0,
            )
        )
        all_issues.append(Issue(code="EMPTY_DATASET", severity=Severity.critical, message=msg))
        metrics = DataQualityMetrics(
            total_cells=0,
            missing_cells=0,
            completeness_rate=0.0,
            duplicate_row_count=0,
            duplicate_row_rate=0.0,
            clean_row_count=0,
            clean_row_rate=0.0,
            constant_column_count=len(columns),
        )
        return (
            DataQualityReport(
                health_score=0.0,
                metrics=metrics,
                rules=rules,
                summary_by_severity={"INFO": 0, "WARNING": 0, "BLOCKING": 0, "CRITICAL": 1},
            ),
            all_issues,
        )

    # 1. Empty rows check
    empty_rows = summary_stats.empty_row_count
    if empty_rows > 0:
        msg = f"{empty_rows} completely empty rows detected."
        rules.append(
            QualityRuleResult(
                rule_name="no_empty_rows",
                category="completeness",
                status=RuleStatus.warning,
                severity=Severity.warning,
                message=msg,
                metric_value=float(empty_rows),
                threshold=0.0,
            )
        )
        if not any(i.code == "EMPTY_ROWS" for i in all_issues):
            all_issues.append(Issue(code="EMPTY_ROWS", severity=Severity.warning, message=msg))
    else:
        rules.append(
            QualityRuleResult(
                rule_name="no_empty_rows",
                category="completeness",
                status=RuleStatus.passed,
                severity=Severity.info,
                message="No completely empty rows detected in dataset.",
                metric_value=0.0,
                threshold=0.0,
            )
        )

    # 2. Duplicate rows check
    duplicate_rows = summary_stats.duplicate_row_count
    duplicate_row_rate = (duplicate_rows / row_count) if row_count > 0 else 0.0
    if duplicate_rows > 0:
        msg = f"{duplicate_rows} duplicate data rows found ({duplicate_row_rate:.1%})."
        rules.append(
            QualityRuleResult(
                rule_name="row_uniqueness",
                category="uniqueness",
                status=RuleStatus.warning,
                severity=Severity.warning,
                message=msg,
                metric_value=round(duplicate_row_rate, 4),
                threshold=0.0,
            )
        )
        if not any(i.code == "DUPLICATE_ROWS" for i in all_issues):
            all_issues.append(Issue(code="DUPLICATE_ROWS", severity=Severity.warning, message=msg))
    else:
        rules.append(
            QualityRuleResult(
                rule_name="row_uniqueness",
                category="uniqueness",
                status=RuleStatus.passed,
                severity=Severity.info,
                message="All evaluated data rows are distinct.",
                metric_value=0.0,
                threshold=0.0,
            )
        )

    # 3. Completeness and missingness
    missing_cells = sum(col.null_count for col in columns)
    completeness_rate = (1.0 - (missing_cells / total_cells)) if total_cells > 0 else 1.0

    high_missing_cols = [
        col for col in columns if col.missing_percentage > config.high_missingness_threshold
    ]
    critical_missing_cols = [
        col for col in columns if col.missing_percentage > config.critical_missingness_threshold
    ]

    if critical_missing_cols:
        col_names = ", ".join(c.source_name for c in critical_missing_cols)
        msg = f"Columns with critical missingness (>{config.critical_missingness_threshold:.0%}): {col_names}."
        rules.append(
            QualityRuleResult(
                rule_name="column_completeness",
                category="completeness",
                status=RuleStatus.failed,
                severity=Severity.blocking,
                message=msg,
                metric_value=round(completeness_rate, 4),
                threshold=config.critical_missingness_threshold,
            )
        )
        all_issues.append(
            Issue(code="CRITICAL_MISSING_DATA", severity=Severity.blocking, message=msg, column=col_names)
        )
    elif high_missing_cols:
        col_names = ", ".join(c.source_name for c in high_missing_cols)
        msg = f"Columns with high missingness (>{config.high_missingness_threshold:.0%}): {col_names}."
        rules.append(
            QualityRuleResult(
                rule_name="column_completeness",
                category="completeness",
                status=RuleStatus.warning,
                severity=Severity.warning,
                message=msg,
                metric_value=round(completeness_rate, 4),
                threshold=config.high_missingness_threshold,
            )
        )
        all_issues.append(
            Issue(code="HIGH_MISSINGNESS", severity=Severity.warning, message=msg, column=col_names)
        )
    else:
        rules.append(
            QualityRuleResult(
                rule_name="column_completeness",
                category="completeness",
                status=RuleStatus.passed,
                severity=Severity.info,
                message=f"Overall dataset completeness is {completeness_rate:.1%}.",
                metric_value=round(completeness_rate, 4),
                threshold=1.0 - config.high_missingness_threshold,
            )
        )

    # 4. Column variance and constant columns
    constant_cols = [col for col in columns if col.unique_count <= 1 and row_count > 1]
    if constant_cols:
        col_names = ", ".join(c.source_name for c in constant_cols)
        rules.append(
            QualityRuleResult(
                rule_name="column_variance",
                category="variance",
                status=RuleStatus.warning,
                severity=Severity.warning,
                message=f"Constant or zero-variance columns detected: {col_names}.",
                metric_value=float(len(constant_cols)),
                threshold=0.0,
            )
        )
    else:
        rules.append(
            QualityRuleResult(
                rule_name="column_variance",
                category="variance",
                status=RuleStatus.passed,
                severity=Severity.info,
                message="All columns contain varied populated values.",
                metric_value=0.0,
                threshold=0.0,
            )
        )

    # 5. Identifier uniqueness check
    for col in columns:
        if col.normalized_name in {
            "employee_id",
            "employeeid",
            "emp_id",
            "emp_no",
            "employee_no",
            "staff_id",
            "id",
        }:
            if col.non_null_count > 0 and col.unique_count < col.non_null_count:
                dup_ids = col.non_null_count - col.unique_count
                msg = f"Identifier column '{col.source_name}' contains {dup_ids} non-unique IDs."
                rules.append(
                    QualityRuleResult(
                        rule_name="identifier_uniqueness",
                        category="uniqueness",
                        status=RuleStatus.failed,
                        severity=Severity.blocking,
                        message=msg,
                        column=col.source_name,
                        metric_value=round(col.uniqueness_ratio, 4),
                        threshold=1.0,
                    )
                )
                all_issues.append(
                    Issue(
                        code="DUPLICATE_IDENTIFIERS",
                        severity=Severity.blocking,
                        message=msg,
                        column=col.source_name,
                    )
                )
            else:
                rules.append(
                    QualityRuleResult(
                        rule_name="identifier_uniqueness",
                        category="uniqueness",
                        status=RuleStatus.passed,
                        severity=Severity.info,
                        message=f"Identifier column '{col.source_name}' has 100% unique populated values.",
                        column=col.source_name,
                        metric_value=1.0,
                        threshold=1.0,
                    )
                )

    # 6. PII / Sensitive data detection (Sampled signal)
    pii_found: list[str] = []
    for col in columns:
        sample_vals = (
            sample_values_by_column.get(col.source_name, col.sample_values)
            if sample_values_by_column
            else col.sample_values
        )
        signals = detect_pii_signals(col.source_name, sample_vals, sample_limit=config.pii_sample_limit)
        if signals:
            pii_found.append(f"{col.source_name} ({', '.join(signals)})")
    if pii_found:
        msg = f"Potential sensitive/PII data signals detected in sampled values for: {', '.join(pii_found)}. Never expose unmasked raw sensitive values."
        rules.append(
            QualityRuleResult(
                rule_name="pii_detection",
                category="privacy",
                status=RuleStatus.warning,
                severity=Severity.warning,
                message=msg,
                metric_value=float(len(pii_found)),
                threshold=0.0,
            )
        )
        all_issues.append(
            Issue(code="POTENTIAL_PII_DETECTED", severity=Severity.warning, message=msg)
        )
    else:
        rules.append(
            QualityRuleResult(
                rule_name="pii_detection",
                category="privacy",
                status=RuleStatus.passed,
                severity=Severity.info,
                message="No direct sensitive/PII pattern signals detected in the analyzed sample. Note: Sample-based heuristic scan does not guarantee absence of sensitive data across the full dataset.",
                metric_value=0.0,
                threshold=0.0,
            )
        )

    # 7. Domain validity checks (Configurable heuristics)
    for col in columns:
        sample_vals = (
            sample_values_by_column.get(col.source_name, col.sample_values)
            if sample_values_by_column
            else col.sample_values
        )
        findings = evaluate_domain_validity(col.source_name, col.normalized_name, sample_vals, config=config)
        for sev, code, finding_msg in findings:
            all_issues.append(Issue(code=code, severity=sev, message=finding_msg, column=col.source_name))
            rules.append(
                QualityRuleResult(
                    rule_name=f"domain_validity_{col.normalized_name}",
                    category="domain_validity",
                    status=RuleStatus.failed if sev in (Severity.blocking, Severity.critical) else RuleStatus.warning,
                    severity=sev,
                    message=finding_msg,
                    column=col.source_name,
                )
            )

    clean_row_count = summary_stats.clean_row_count
    clean_row_rate = (clean_row_count / row_count) if row_count > 0 else 0.0

    # Summary metrics
    metrics = DataQualityMetrics(
        total_cells=total_cells,
        missing_cells=missing_cells,
        completeness_rate=round(completeness_rate, 4),
        duplicate_row_count=duplicate_rows,
        duplicate_row_rate=round(duplicate_row_rate, 4),
        clean_row_count=clean_row_count,
        clean_row_rate=round(clean_row_rate, 4),
        constant_column_count=len(constant_cols),
    )

    # Calculate deterministic Composite Health Score (0 - 100)
    # The Health Score is an engineering quality indicator, not a percentage of truth.
    base_score = (
        (completeness_rate * 40.0)
        + ((1.0 - duplicate_row_rate) * 20.0)
        + (clean_row_rate * 20.0)
        + 20.0
    )

    deductions = 0.0
    for issue in all_issues:
        if issue.severity == Severity.critical:
            deductions += 20.0
        elif issue.severity == Severity.blocking:
            deductions += 10.0
        elif issue.severity == Severity.warning:
            deductions += 2.0

    health_score = max(0.0, min(100.0, round(base_score - deductions, 1)))

    summary_by_severity = {
        "INFO": sum(1 for i in all_issues if i.severity == Severity.info),
        "WARNING": sum(1 for i in all_issues if i.severity == Severity.warning),
        "BLOCKING": sum(1 for i in all_issues if i.severity == Severity.blocking),
        "CRITICAL": sum(1 for i in all_issues if i.severity == Severity.critical),
    }

    report = DataQualityReport(
        health_score=health_score,
        metrics=metrics,
        rules=rules,
        summary_by_severity=summary_by_severity,
    )

    return report, all_issues


def generate_data_quality_report_for_rows(
    headers: list[str],
    rows: list[dict[str, str]],
    columns: list[ColumnProfile],
    existing_issues: list[Issue] | None = None,
    config: DataQualityConfig = DEFAULT_QUALITY_CONFIG,
) -> tuple[DataQualityReport, list[Issue]]:
    """Convenience helper for in-memory row collections."""
    summary_stats = summarize_in_memory_dataset(headers, rows)
    sample_values_by_column = {
        h: [r.get(h, "") for r in rows[: config.pii_sample_limit]] for h in headers
    }
    return generate_data_quality_report(
        columns=columns,
        summary_stats=summary_stats,
        sample_values_by_column=sample_values_by_column,
        existing_issues=existing_issues,
        config=config,
    )
