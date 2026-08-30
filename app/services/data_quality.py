from __future__ import annotations

from collections import Counter
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


def compute_numeric_stats(values: list[str]) -> NumericStats | None:
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


def detect_pii_signals(source_name: str, values: list[str]) -> list[str]:
    signals: list[str] = []
    lowered_name = source_name.lower().replace("_", "").replace("-", "")
    populated = [v.strip() for v in values if v and v.strip()]
    sample = populated[:20]

    # Email signal
    if any(k in lowered_name for k in ["email", "e_mail", "mail"]) or (
        sample and any(PII_EMAIL_REGEX.match(v) for v in sample)
    ):
        signals.append("email_address")

    # Phone signal
    if any(k in lowered_name for k in ["phone", "mobile", "cell", "tel"]) or (
        sample and sum(1 for v in sample if PII_PHONE_REGEX.match(v)) >= len(sample) * 0.7
    ):
        signals.append("phone_number")

    # SSN / National ID signal
    if any(k in lowered_name for k in ["ssn", "socialsecurity", "nationalid", "aadhaar", "sin"]) or (
        sample and any(PII_SSN_REGEX.match(v) for v in sample)
    ):
        signals.append("national_id_or_ssn")

    return signals


def evaluate_domain_validity(
    source_name: str, normalized_name: str, values: list[str]
) -> list[tuple[Severity, str, str]]:
    findings: list[tuple[Severity, str, str]] = []
    populated = [v.strip() for v in values if v and v.strip()]
    if not populated:
        return findings

    # Age domain validation (typically 16-100 for workforce)
    if normalized_name in {"age", "employee_age"}:
        for v in populated:
            try:
                num = float(v)
                if num < 16 or num > 100:
                    findings.append(
                        (
                            Severity.warning,
                            "AGE_OUT_OF_RANGE",
                            f"Age values outside standard employment range [16, 100] detected (e.g. {num}).",
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

    # Salary/Compensation domain validation (must not be negative)
    if normalized_name in {"salary", "monthly_income", "annual_salary", "compensation", "pay"}:
        for v in populated:
            try:
                num = float(v)
                if num < 0:
                    findings.append(
                        (
                            Severity.blocking,
                            "NEGATIVE_COMPENSATION",
                            f"Negative compensation value detected ({num}). Compensation cannot be negative.",
                        )
                    )
                    break
            except ValueError:
                pass

    # Tenure domain validation (cannot be negative or absurdly high e.g. > 70)
    if normalized_name in {"tenure", "tenure_years", "years_at_company", "years_service"}:
        for v in populated:
            try:
                num = float(v)
                if num < 0:
                    findings.append(
                        (
                            Severity.warning,
                            "NEGATIVE_TENURE",
                            f"Negative tenure value detected ({num}). Tenure cannot be negative.",
                        )
                    )
                    break
                elif num > 70:
                    findings.append(
                        (
                            Severity.warning,
                            "HIGH_TENURE_OUTLIER",
                            f"Tenure value exceeds plausible career duration ({num} years).",
                        )
                    )
                    break
            except ValueError:
                pass

    return findings


def generate_data_quality_report(
    headers: list[str],
    rows: list[dict[str, str]],
    columns: list[ColumnProfile],
    existing_issues: list[Issue] | None = None,
) -> tuple[DataQualityReport, list[Issue]]:
    row_count = len(rows)
    column_count = len(headers)
    total_cells = row_count * column_count if (row_count and column_count) else 0

    all_issues: list[Issue] = list(existing_issues or [])
    rules: list[QualityRuleResult] = []

    # 1. Empty rows check
    empty_row_indices = [
        idx
        for idx, row in enumerate(rows, start=1)
        if not any(row[h].strip() for h in headers if h in row)
    ]
    if empty_row_indices:
        msg = f"{len(empty_row_indices)} completely empty rows detected."
        rules.append(
            QualityRuleResult(
                rule_name="no_empty_rows",
                category="completeness",
                status=RuleStatus.warning,
                severity=Severity.warning,
                message=msg,
                metric_value=float(len(empty_row_indices)),
                threshold=0.0,
            )
        )
        all_issues.append(Issue(code="EMPTY_ROWS", severity=Severity.warning, message=msg))
    else:
        rules.append(
            QualityRuleResult(
                rule_name="no_empty_rows",
                category="completeness",
                status=RuleStatus.passed,
                severity=Severity.info,
                message="No completely empty rows detected.",
                metric_value=0.0,
                threshold=0.0,
            )
        )

    # 2. Duplicate rows check
    duplicate_rows = sum(
        count - 1
        for count in Counter(tuple(row[h] for h in headers) for row in rows).values()
        if count > 1
    )
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
                message="All data rows are unique.",
                metric_value=0.0,
                threshold=0.0,
            )
        )

    # 3. Completeness and missingness
    missing_cells = sum(col.null_count for col in columns)
    completeness_rate = (1.0 - (missing_cells / total_cells)) if total_cells > 0 else 1.0

    high_missing_cols = [col for col in columns if col.missing_percentage > 0.20]
    critical_missing_cols = [col for col in columns if col.missing_percentage > 0.80]

    if critical_missing_cols:
        col_names = ", ".join(c.source_name for c in critical_missing_cols)
        msg = f"Columns with critical missingness (>80%): {col_names}."
        rules.append(
            QualityRuleResult(
                rule_name="column_completeness",
                category="completeness",
                status=RuleStatus.failed,
                severity=Severity.blocking,
                message=msg,
                metric_value=round(completeness_rate, 4),
                threshold=0.80,
            )
        )
        all_issues.append(
            Issue(code="CRITICAL_MISSING_DATA", severity=Severity.blocking, message=msg, column=col_names)
        )
    elif high_missing_cols:
        col_names = ", ".join(c.source_name for c in high_missing_cols)
        msg = f"Columns with high missingness (>20%): {col_names}."
        rules.append(
            QualityRuleResult(
                rule_name="column_completeness",
                category="completeness",
                status=RuleStatus.warning,
                severity=Severity.warning,
                message=msg,
                metric_value=round(completeness_rate, 4),
                threshold=0.80,
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
                threshold=0.80,
            )
        )

    # 4. Constant or empty columns
    constant_cols = [col for col in columns if col.unique_count <= 1 and row_count > 1]
    if constant_cols:
        col_names = ", ".join(c.source_name for c in constant_cols)
        rules.append(
            QualityRuleResult(
                rule_name="column_variance",
                category="variance",
                status=RuleStatus.warning,
                severity=Severity.warning,
                message=f"Constant or empty columns detected: {col_names}.",
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
                message="All columns contain varied data values.",
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
                msg = f"Identifier column '{col.source_name}' contains {dup_ids} duplicate IDs."
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

    # 6. PII / Sensitive data detection
    pii_found: list[str] = []
    for col in columns:
        vals = [row[col.source_name] for row in rows if col.source_name in row]
        signals = detect_pii_signals(col.source_name, vals)
        if signals:
            pii_found.append(f"{col.source_name} ({', '.join(signals)})")
    if pii_found:
        msg = f"Potential sensitive/PII data detected in: {', '.join(pii_found)}."
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
                message="No direct unmasked PII patterns detected in analyzed sample.",
                metric_value=0.0,
                threshold=0.0,
            )
        )

    # 7. Domain validity checks
    for col in columns:
        vals = [row[col.source_name] for row in rows if col.source_name in row]
        findings = evaluate_domain_validity(col.source_name, col.normalized_name, vals)
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

    # Calculate clean rows count (rows without any missing or blank values)
    clean_row_count = sum(
        1 for row in rows if all(row.get(h, "").strip() != "" for h in headers)
    )
    clean_row_rate = (clean_row_count / row_count) if row_count > 0 else 0.0

    # Metrics summary
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
    # Completeness: 40 pts, Uniqueness: 20 pts, Clean rows: 20 pts, Integrity base: 20 pts
    base_score = (
        (completeness_rate * 40.0)
        + ((1.0 - duplicate_row_rate) * 20.0)
        + (clean_row_rate * 20.0)
        + 20.0
    )

    # Deductions
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
