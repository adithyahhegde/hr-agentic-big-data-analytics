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
