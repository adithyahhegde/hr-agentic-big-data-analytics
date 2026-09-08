from fastapi.testclient import TestClient

import app.main as main
from app.services.run_history import RunHistory


client = TestClient(main.app, raise_server_exceptions=False)


def _profile_and_accept(rows: str) -> dict:
    profile = client.post(
        "/api/datasets/profile",
        files={"file": ("failure-ledger.csv", rows.encode(), "text/csv")},
    ).json()
    mappings = {source: candidate["canonical_field"] for source, candidate in profile["mappings"].items()}
    response = client.post(f"/api/datasets/{profile['dataset_id']}/schema", json={"mappings": mappings})
    assert response.status_code == 200
    return profile


def test_execution_failure_is_persisted_without_leaking_dependency_details(monkeypatch, tmp_path):
    profile = _profile_and_accept(
        "emp_no,left_org,age\n"
        + "".join(f"E{i},{'Yes' if i % 2 else 'No'},{25 + i}\n" for i in range(20))
    )
    persisted = RunHistory(tmp_path / "history.sqlite3")
    monkeypatch.setattr(main, "history", persisted)
    monkeypatch.setattr(main, "analyze_csv", lambda *args: (_ for _ in ()).throw(RuntimeError("SECRET_EMPLOYEE_SALARY=/private/hr/secret.csv")))

    response = client.get(f"/api/datasets/{profile['dataset_id']}/analytics")

    assert response.status_code == 503
    assert response.json()["detail"] == "Execution dependency unavailable."
    assert "SECRET_EMPLOYEE_SALARY" not in response.text
    runs = persisted.list(profile["dataset_id"])
    assert len(runs) == 1
    assert runs[0]["status"] == "FAILED"
    assert runs[0]["operation"] == "api:analytics"


def test_unexpected_failure_is_persisted_and_response_is_generic(monkeypatch, tmp_path):
    profile = _profile_and_accept(
        "emp_no,left_org,age\n"
        + "".join(f"E{i},{'Yes' if i % 2 else 'No'},{25 + i}\n" for i in range(20))
    )
    persisted = RunHistory(tmp_path / "history.sqlite3")
    monkeypatch.setattr(main, "history", persisted)
    monkeypatch.setattr(main, "_require_state", lambda dataset_id: (_ for _ in ()).throw(RuntimeError("employee_id=E12345 salary=999999")))

    response = client.get(f"/api/datasets/{profile['dataset_id']}/analytics")

    assert response.status_code == 500
    assert response.json()["detail"] == "Internal server error. Check server logs for operational details."
    assert "E12345" not in response.text
    runs = persisted.list(profile["dataset_id"])
    assert len(runs) == 1
    assert runs[0]["status"] == "FAILED"
    assert runs[0]["operation"] == "api:analytics"
