from app.services.profiling import profile_dataset


def test_profile_maps_known_hr_aliases_with_evidence():
    profile = profile_dataset(["emp_no", "dept", "left_org"], [{"emp_no": "1", "dept": "Engineering", "left_org": "Yes"}, {"emp_no": "2", "dept": "Sales", "left_org": "No"}])
    assert profile.mappings["emp_no"].canonical_field == "employee_id"
    assert profile.mappings["left_org"].confidence == 0.96
    assert "binary_value_pattern" in profile.mappings["left_org"].evidence


def test_profile_requires_review_for_mapping_collision():
    profile = profile_dataset(["emp_no", "employee_id"], [{"emp_no": "1", "employee_id": "1"}])
    assert profile.mappings["emp_no"].decision == "NEEDS_REVIEW"
    assert any(issue.code == "MAPPING_COLLISION" for issue in profile.issues)


def test_profile_enriches_column_metrics_and_numeric_stats():
    profile = profile_dataset(
        ["emp_no", "age", "salary", "notes"],
        [
            {"emp_no": "1", "age": "30", "salary": "50000", "notes": "Active"},
            {"emp_no": "2", "age": "40", "salary": "70000", "notes": ""},
        ],
    )
    col_map = {col.source_name: col for col in profile.columns}
    assert col_map["salary"].numeric_stats is not None
    assert col_map["salary"].numeric_stats.mean == 60000.0
    assert col_map["salary"].numeric_stats.min == 50000.0
    assert col_map["salary"].numeric_stats.max == 70000.0
    assert col_map["notes"].missing_percentage == 0.5
    assert col_map["emp_no"].uniqueness_ratio == 1.0

