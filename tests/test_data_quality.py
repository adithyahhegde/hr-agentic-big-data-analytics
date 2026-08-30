from __future__ import annotations

from app.models import ColumnProfile, Severity, RuleStatus
from app.services.data_quality import (
    DataQualityConfig,
    DatasetSummaryStats,
    compute_numeric_stats,
    detect_pii_signals,
    evaluate_domain_validity,
    generate_data_quality_report,
    generate_data_quality_report_for_rows,
    summarize_in_memory_dataset,
)
from app.services.profiling import profile_dataset


def test_compute_numeric_stats_valid():
    values = ["10.5", "-5.0", "0", "100.5", ""]
    stats = compute_numeric_stats(values)
    assert stats is not None
    assert stats.min == -5.0
    assert stats.max == 100.5
    assert stats.mean == 26.5
    assert stats.zeros_count == 1
    assert stats.negatives_count == 1


def test_compute_numeric_stats_non_numeric():
    values = ["10.5", "abc", "20"]
    stats = compute_numeric_stats(values)
    assert stats is None


def test_detect_pii_signals():
    emails = ["john.doe@company.com", "jane@hr.org", "test@domain.co.uk"]
    assert "email_address" in detect_pii_signals("contact_email", emails)

    phones = ["+1-555-123-4567", "(555) 987-6543", "555-111-2222"]
    assert "phone_number" in detect_pii_signals("phone_number", phones)

    ssns = ["123-45-6789", "987-65-4321"]
    assert "national_id_or_ssn" in detect_pii_signals("ssn", ssns)

    clean_roles = ["Software Engineer", "HR Specialist", "Accountant"]
    assert detect_pii_signals("job_role", clean_roles) == []


def test_sampled_pii_semantics_and_no_raw_exposure():
    # Verify no raw PII is exposed in messages and that sample semantics are explicit
    headers = ["emp_id", "email"]
    rows = [{"emp_id": "1", "email": "confidential_ceo@enterprise.org"}]
    profile = profile_dataset(headers, rows)
    assert profile.data_quality is not None
    pii_rule = next(r for r in profile.data_quality.rules if r.rule_name == "pii_detection")
    assert pii_rule.status == RuleStatus.warning
    # Ensure confidential value itself is not in message
    assert "confidential_ceo@enterprise.org" not in pii_rule.message
    assert "email_address" in pii_rule.message
    assert "sampled" in pii_rule.message.lower()

    # Clean dataset explicitly notes sampling limitation
    clean_headers = ["emp_id", "job_role"]
    clean_rows = [{"emp_id": "1", "job_role": "Analyst"}]
    clean_profile = profile_dataset(clean_headers, clean_rows)
    clean_pii_rule = next(r for r in clean_profile.data_quality.rules if r.rule_name == "pii_detection")
    assert clean_pii_rule.status == RuleStatus.passed
    assert "does not guarantee absence" in clean_pii_rule.message.lower()


def test_evaluate_domain_validity_negative_salary():
    findings = evaluate_domain_validity("salary", "salary", ["50000", "-1000", "60000"])
    assert len(findings) == 1
    sev, code, msg = findings[0]
    assert sev == Severity.blocking
    assert code == "NEGATIVE_COMPENSATION"


def test_evaluate_domain_validity_age_out_of_range():
    findings = evaluate_domain_validity("age", "age", ["25", "150", "30"])
    assert len(findings) == 1
    sev, code, msg = findings[0]
    assert sev == Severity.warning
    assert code == "AGE_OUT_OF_RANGE"

    findings_young = evaluate_domain_validity("age", "age", ["10", "30"])
    assert len(findings_young) == 1
    assert findings_young[0][1] == "AGE_OUT_OF_RANGE"


def test_evaluate_domain_validity_tenure():
    findings_neg = evaluate_domain_validity("tenure_years", "tenure_years", ["-2", "5"])
    assert len(findings_neg) == 1
    assert findings_neg[0][1] == "NEGATIVE_TENURE"

    findings_high = evaluate_domain_validity("tenure_years", "tenure_years", ["85", "5"])
    assert len(findings_high) == 1
    assert findings_high[0][1] == "HIGH_TENURE_OUTLIER"


def test_configurable_hr_thresholds():
    custom_config = DataQualityConfig(
        min_age_heuristic=21.0,
        max_age_heuristic=60.0,
        max_tenure_heuristic=35.0,
        allow_negative_salary=True,
    )
    # Age 62 is invalid under max_age_heuristic=60
    findings = evaluate_domain_validity("age", "age", ["62"], config=custom_config)
    assert len(findings) == 1
    assert findings[0][1] == "AGE_OUT_OF_RANGE"

    # Age 19 is invalid under min_age_heuristic=21
    findings_young = evaluate_domain_validity("age", "age", ["19"], config=custom_config)
    assert len(findings_young) == 1
    assert findings_young[0][1] == "AGE_OUT_OF_RANGE"

    # Negative salary permitted when configured
    findings_salary = evaluate_domain_validity("salary", "salary", ["-500"], config=custom_config)
    assert len(findings_salary) == 0


def test_data_quality_report_empty_rows():
    headers = ["emp_id", "dept", "salary"]
    rows = [
        {"emp_id": "E1", "dept": "HR", "salary": "50000"},
        {"emp_id": "", "dept": "", "salary": ""},
        {"emp_id": "E2", "dept": "Sales", "salary": "60000"},
    ]
    profile = profile_dataset(headers, rows)
    assert profile.data_quality is not None
    dq = profile.data_quality
    empty_rule = next((r for r in dq.rules if r.rule_name == "no_empty_rows"), None)
    assert empty_rule is not None
    assert empty_rule.status == RuleStatus.warning
    assert any(i.code == "EMPTY_ROWS" for i in profile.issues)


def test_data_quality_report_high_missingness():
    headers = ["emp_id", "notes"]
    rows = [
        {"emp_id": "E1", "notes": ""},
        {"emp_id": "E2", "notes": ""},
        {"emp_id": "E3", "notes": ""},
        {"emp_id": "E4", "notes": "Some note"},
    ]
    profile = profile_dataset(headers, rows)
    assert profile.data_quality is not None
    dq = profile.data_quality
    assert dq.metrics.missing_cells == 3
    assert dq.metrics.total_cells == 8
    assert dq.metrics.completeness_rate == 0.625
    assert any(i.code == "HIGH_MISSINGNESS" for i in profile.issues)


def test_data_quality_report_critical_missingness():
    headers = ["emp_id", "notes"]
    rows = [
        {"emp_id": "E1", "notes": ""},
        {"emp_id": "E2", "notes": ""},
        {"emp_id": "E3", "notes": ""},
        {"emp_id": "E4", "notes": ""},
        {"emp_id": "E5", "notes": ""},
        {"emp_id": "E6", "notes": ""},
        {"emp_id": "E7", "notes": ""},
        {"emp_id": "E8", "notes": ""},
        {"emp_id": "E9", "notes": ""},
        {"emp_id": "E10", "notes": "one note"},
    ]
    profile = profile_dataset(headers, rows)
    assert profile.data_quality is not None
    assert any(i.code == "CRITICAL_MISSING_DATA" for i in profile.issues)


def test_data_quality_report_duplicate_identifiers():
    headers = ["emp_id", "dept", "salary"]
    rows = [
        {"emp_id": "E1", "dept": "HR", "salary": "50000"},
        {"emp_id": "E1", "dept": "Sales", "salary": "60000"},
        {"emp_id": "E2", "dept": "Eng", "salary": "70000"},
    ]
    profile = profile_dataset(headers, rows)
    assert profile.data_quality is not None
    dq = profile.data_quality
    id_rule = next((r for r in dq.rules if r.rule_name == "identifier_uniqueness"), None)
    assert id_rule is not None
    assert id_rule.status == RuleStatus.failed
    assert any(i.code == "DUPLICATE_IDENTIFIERS" for i in profile.issues)


def test_clean_dataset_has_high_health_score():
    headers = ["emp_id", "department", "salary", "age", "attrition"]
    rows = [
        {"emp_id": f"E{i}", "department": "Engineering", "salary": f"{60000 + i * 1000}", "age": f"{25 + i}", "attrition": "No"}
        for i in range(15)
    ]
    profile = profile_dataset(headers, rows)
    assert profile.data_quality is not None
    assert profile.data_quality.health_score >= 95.0
    assert profile.data_quality.metrics.clean_row_rate == 1.0
    assert profile.data_quality.metrics.completeness_rate == 1.0
    assert profile.data_quality.metrics.duplicate_row_rate == 0.0


def test_empty_dataset_handling():
    summary_stats = DatasetSummaryStats(row_count=0, column_count=2)
    columns = [
        ColumnProfile(
            source_name="emp_id",
            normalized_name="emp_id",
            inferred_type="unknown",
            non_null_count=0,
            null_count=0,
            missing_percentage=0.0,
            unique_count=0,
            uniqueness_ratio=0.0,
        )
    ]
    report, issues = generate_data_quality_report(columns, summary_stats)
    assert report.health_score == 0.0
    assert any(i.code == "EMPTY_DATASET" for i in issues)


def test_single_row_dataset_handling():
    headers = ["emp_id", "department", "salary"]
    rows = [{"emp_id": "E1", "department": "Engineering", "salary": "75000"}]
    profile = profile_dataset(headers, rows)
    assert profile.row_count == 1
    assert profile.data_quality is not None
    assert profile.data_quality.health_score >= 80.0
    assert profile.data_quality.metrics.clean_row_count == 1


def test_all_null_column_and_constant_column():
    headers = ["emp_id", "empty_col", "constant_col"]
    rows = [
        {"emp_id": "1", "empty_col": "", "constant_col": "Same"},
        {"emp_id": "2", "empty_col": "", "constant_col": "Same"},
        {"emp_id": "3", "empty_col": "", "constant_col": "Same"},
    ]
    profile = profile_dataset(headers, rows)
    assert profile.data_quality is not None
    col_map = {c.source_name: c for c in profile.columns}
    assert col_map["empty_col"].missing_percentage == 1.0
    assert col_map["empty_col"].numeric_stats is None
    assert col_map["constant_col"].unique_count == 1
    assert profile.data_quality.metrics.constant_column_count >= 1


def test_large_synthetic_input_performance():
    headers = ["emp_id", "department", "salary", "age"]
    rows = [
        {
            "emp_id": f"EMP_{i}",
            "department": "Engineering" if i % 2 == 0 else "Sales",
            "salary": str(50000 + (i % 100) * 500),
            "age": str(22 + (i % 40)),
        }
        for i in range(2500)
    ]
    summary = summarize_in_memory_dataset(headers, rows)
    assert summary.row_count == 2500
    assert summary.clean_row_count == 2500
    assert summary.duplicate_row_count == 0
    profile = profile_dataset(headers, rows)
    assert profile.data_quality is not None
    assert profile.data_quality.health_score >= 95.0
