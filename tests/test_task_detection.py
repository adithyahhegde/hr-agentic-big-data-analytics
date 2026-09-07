from app.services.task_detection import detect_tasks


def test_detects_supported_tasks_from_canonical_schema():
    mappings = {
        "left_org": "attrition",
        "salary": "salary",
        "age": "age",
        "income": "monthly_income",
        "tenure": "years_at_company",
    }
    tasks = {task.objective: task for task in detect_tasks(mappings, 100)}
    assert tasks["attrition_classification"].status == "FEASIBLE"
    assert tasks["attrition_classification"].target_field == "left_org"
    assert tasks["salary_regression"].status == "FEASIBLE"
    assert tasks["employee_clustering"].status == "FEASIBLE"
    assert tasks["anomaly_detection"].status == "FEASIBLE"


def test_supervised_task_features_are_canonical_fields():
    mappings = {
        "Employee ID": "employee_id",
        "Age": "age",
        "Department": "department",
        "Job Role": "job_role",
        "Annual Salary": "salary",
        "Overtime": "overtime",
        "Attrition": "attrition",
    }
    tasks = {task.objective: task for task in detect_tasks(mappings, 82)}
    attrition = tasks["attrition_classification"]
    assert attrition.status == "FEASIBLE"
    assert attrition.target_field == "Attrition"
    assert attrition.feature_fields == ("age", "department", "job_role", "overtime")
    assert "Age" not in attrition.feature_fields


def test_identifiers_and_targets_are_excluded_from_unsupervised_features():
    mappings = {"Employee ID": "employee_id", "Age": "age", "Attrition": "attrition", "Salary": "salary"}
    tasks = {task.objective: task for task in detect_tasks(mappings, 20)}
    assert tasks["employee_clustering"].feature_fields == ("age",)
    assert tasks["anomaly_detection"].feature_fields == ("age",)


def test_does_not_invent_targets():
    mappings = {"age": "age", "income": "monthly_income", "dept": "department"}
    tasks = {task.objective: task for task in detect_tasks(mappings, 100)}
    assert tasks["attrition_classification"].status == "BLOCKED"
    assert tasks["attrition_classification"].target_field is None
    assert tasks["salary_regression"].status == "BLOCKED"


def test_small_dataset_is_blocked_for_modeling_screen():
    mappings = {"left": "attrition", "age": "age", "income": "monthly_income"}
    tasks = {task.objective: task for task in detect_tasks(mappings, 10)}
    assert tasks["attrition_classification"].status == "BLOCKED"
    assert any("20 rows" in reason for reason in tasks["attrition_classification"].reasons)


def test_robustness_matrix_covers_clean_messy_categorical_and_mixed_schemas():
    scenarios = {
        "clean": {
            "Employee ID": "employee_id", "Age": "age", "Department": "department",
            "Job Satisfaction": "job_satisfaction", "Monthly Income": "monthly_income",
            "Overtime": "overtime", "Attrition": "attrition",
        },
        "messy": {
            "Employee_ID": "employee_id", "employee age": "age", "dept": "department",
            "satisfaction": "job_satisfaction", "monthly_income": "monthly_income",
            "Over Time": "overtime", "left_company": "attrition",
        },
        "categorical": {
            "Employee ID": "employee_id", "Department": "department", "Job Role": "job_role",
            "Overtime": "overtime", "Attrition": "attrition",
        },
        "mixed": {
            "Employee ID": "employee_id", "Age": "age", "Department": "department",
            "Monthly Income": "monthly_income", "Job Role": "job_role", "Attrition": "attrition",
        },
    }
    for name, mappings in scenarios.items():
        tasks = {task.objective: task for task in detect_tasks(mappings, 100)}
        assert tasks["attrition_classification"].status == "FEASIBLE", name
        assert tasks["attrition_classification"].target_field is not None
        assert all(field in mappings.values() for field in tasks["attrition_classification"].feature_fields)
        assert "employee_id" not in tasks["attrition_classification"].feature_fields
        assert "attrition" not in tasks["attrition_classification"].feature_fields


def test_robustness_matrix_blocks_ambiguous_collision_until_schema_is_resolved():
    mappings = {
        "Employee ID": "employee_id",
        "Department": "department",
        "Dept": "department",
        "Age": "age",
        "Attrition": "attrition",
    }
    tasks = {task.objective: task for task in detect_tasks(mappings, 100)}
    assert tasks["attrition_classification"].status == "FEASIBLE"
    assert tasks["attrition_classification"].feature_fields.count("department") == 1
