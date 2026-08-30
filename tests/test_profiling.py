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
