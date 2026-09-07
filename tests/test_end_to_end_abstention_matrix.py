from fastapi.testclient import TestClient

import app.main as main


client = TestClient(main.app)


def _profile(rows: str) -> dict:
    response = client.post(
        "/api/datasets/profile",
        files={"file": ("matrix.csv", rows.encode(), "text/csv")},
    )
    assert response.status_code == 200
    return response.json()


def _accept(profile: dict) -> None:
    mappings = {source: candidate["canonical_field"] for source, candidate in profile["mappings"].items()}
    response = client.post(f"/api/datasets/{profile['dataset_id']}/schema", json={"mappings": mappings})
    assert response.status_code == 200


def test_missing_schema_abstains_before_execution():
    response = client.get("/api/datasets/not-a-real-dataset/analytics")
    assert response.status_code == 409
    assert response.json()["detail"] == "Confirm the dataset schema before continuing."


def test_ambiguous_schema_abstains_at_confirmation():
    profile = _profile("emp_no,dept,division\n1,Engineering,Technology\n")
    response = client.post(
        f"/api/datasets/{profile['dataset_id']}/schema",
        json={"mappings": {"emp_no": "employee_id", "dept": "department", "division": "department"}},
    )
    assert response.status_code == 422
    assert "mapping" in response.json()["detail"].lower()


def test_insufficient_training_rows_abstain_from_ml():
    profile = _profile("emp_no,left_org,age\nE1,Yes,31\nE2,No,42\n")
    _accept(profile)
    response = client.post(f"/api/datasets/{profile['dataset_id']}/ml/attrition_classification")
    assert response.status_code == 409
    assert "blocked" in response.json()["detail"].lower()


def test_unknown_objective_abstains_without_execution():
    profile = _profile("emp_no,dept\nE1,Engineering\nE2,Sales\n")
    _accept(profile)
    response = client.post(f"/api/datasets/{profile['dataset_id']}/ml/not_supported")
    assert response.status_code == 404
    assert response.json()["detail"] == "Unknown analytical objective."
