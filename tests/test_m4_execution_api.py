from fastapi.testclient import TestClient

import app.main as main


client = TestClient(main.app)


def test_execute_dataset_streams_to_store_and_returns_routing_metadata(monkeypatch):
    monkeypatch.setattr(main, "read_csv", lambda path, profile: object())
    response = client.post(
        "/api/datasets/execute",
        files={"file": ("workforce.csv", b"emp_no,dept\n1,Engineering\n2,Sales\n", "text/csv")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "EXECUTED"
    assert body["engine"] == "LOCAL"
    assert body["row_count"] == 2
    assert body["column_count"] == 2
    assert len(body["dataset_fingerprint"]) == 64


def test_execute_dataset_rejects_non_csv():
    response = client.post(
        "/api/datasets/execute",
        files={"file": ("workforce.txt", b"emp_no\n1\n", "text/plain")},
    )
    assert response.status_code == 415


def test_execute_dataset_returns_safe_error_when_engine_dependency_is_missing(monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("Spark execution was selected but pyspark is not installed.")

    monkeypatch.setattr(main, "read_csv", fail)
    response = client.post(
        "/api/datasets/execute",
        files={"file": ("workforce.csv", b"emp_no\n1\n", "text/csv")},
    )
    assert response.status_code == 503
    assert "pyspark" in response.json()["detail"]
