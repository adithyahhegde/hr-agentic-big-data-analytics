from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_reports_non_sensitive_service_configuration():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert "max_upload_bytes" not in response.json()


def test_profile_endpoint_returns_structured_profile():
    response = client.post(
        "/api/datasets/profile",
        files={"file": ("workforce.csv", b"emp_no,dept,left_org\n1,Engineering,Yes\n2,Sales,No\n", "text/csv")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["row_count"] == 2
    assert body["mappings"]["left_org"]["canonical_field"] == "attrition"


def test_profile_endpoint_rejects_non_csv_file():
    response = client.post("/api/datasets/profile", files={"file": ("workforce.txt", b"x", "text/plain")})
    assert response.status_code == 415


def test_accepted_schema_returns_explainable_capabilities():
    profile = client.post("/api/datasets/profile", files={"file": ("workforce.csv", b"emp_no,dept,left_org\n1,Engineering,Yes\n2,Sales,No\n3,Sales,No\n4,HR,Yes\n5,HR,No\n6,IT,No\n7,IT,Yes\n8,IT,No\n9,HR,No\n10,Sales,Yes\n", "text/csv")}).json()
    mappings = {source: candidate["canonical_field"] for source, candidate in profile["mappings"].items()}
    response = client.post(f"/api/datasets/{profile['dataset_id']}/schema", json={"mappings": mappings})
    assert response.status_code == 200
    capabilities = {item["objective"]: item for item in response.json()["capabilities"]}
    assert capabilities["attrition_classification"]["status"] == "FEASIBLE"
    assert capabilities["salary_regression"]["status"] == "BLOCKED"


def test_schema_acceptance_rejects_duplicate_canonical_fields():
    profile = client.post("/api/datasets/profile", files={"file": ("workforce.csv", b"emp_no,dept\n1,Engineering\n", "text/csv")}).json()
    response = client.post(f"/api/datasets/{profile['dataset_id']}/schema", json={"mappings": {"emp_no": "employee_id", "dept": "employee_id"}})
    assert response.status_code == 422
