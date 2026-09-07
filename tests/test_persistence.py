import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace

from app.services.dataset_registry import DatasetRegistry
from app.services.run_history import RunHistory


def test_dataset_registry_round_trips_manifest_profile_and_mappings(tmp_path: Path):
    registry = DatasetRegistry(tmp_path / "registry.sqlite3")
    csv_path = tmp_path / "dataset.csv"
    csv_path.write_text("employee_id,salary\nE1,50000\n", encoding="utf-8")
    dataset = SimpleNamespace(
        dataset_id="ds-1", sha256="a" * 64, filename="dataset.csv", path=csv_path,
        size_bytes=32, row_count=1, column_count=2,
    )
    registry.register(dataset)
    registry.save_profile("ds-1", SimpleNamespace(model_dump=lambda mode="json": {"dataset_id": "ds-1", "schema_version": "2.0.0"}))
    registry.save_mappings("ds-1", {"employee_id": "employee_id", "salary": "salary"})

    manifest = registry.get("ds-1")
    assert manifest is not None
    assert manifest["fingerprint"] == "a" * 64
    assert registry.get_profile("ds-1")["schema_version"] == "2.0.0"
    assert registry.get_mappings("ds-1")["salary"] == "salary"


def test_dataset_registry_reregister_preserves_profile_and_mappings(tmp_path: Path):
    registry = DatasetRegistry(tmp_path / "registry.sqlite3")
    csv_path = tmp_path / "dataset.csv"
    csv_path.write_text("employee_id,salary\nE1,50000\n", encoding="utf-8")
    dataset = SimpleNamespace(
        dataset_id="ds-1", sha256="a" * 64, filename="dataset.csv", path=csv_path,
        size_bytes=32, row_count=1, column_count=2,
    )
    registry.register(dataset)
    registry.save_profile("ds-1", SimpleNamespace(model_dump=lambda mode="json": {"dataset_id": "ds-1", "schema_version": "2.0.0"}))
    registry.save_mappings("ds-1", {"employee_id": "employee_id", "salary": "salary"})

    refreshed = SimpleNamespace(
        dataset_id="ds-1", sha256="c" * 64, filename="renamed.csv", path=tmp_path / "renamed.csv",
        size_bytes=64, row_count=2, column_count=2,
    )
    registry.register(refreshed)

    manifest = registry.get("ds-1")
    assert manifest["fingerprint"] == "c" * 64
    assert manifest["filename"] == "renamed.csv"
    assert registry.get_profile("ds-1")["schema_version"] == "2.0.0"
    assert registry.get_mappings("ds-1") == {"employee_id": "employee_id", "salary": "salary"}


def test_run_history_failure_does_not_persist_exception_message(tmp_path: Path):
    db_path = tmp_path / "history.sqlite3"
    history = RunHistory(db_path)
    secret = "E1,Adithya,50000"
    history.record_failure("ds-1", "b" * 64, "ml", ValueError(secret), "LOCAL")

    with sqlite3.connect(db_path) as db:
        result_json = db.execute("SELECT result_json FROM runs WHERE dataset_id=?", ("ds-1",)).fetchone()[0]
    stored = json.loads(result_json)
    assert stored["error_type"] == "ValueError"
    assert stored["message"] != secret
    assert secret not in result_json
    assert history.latest("ds-1", "ml") is None


def test_run_history_persists_success_and_failure_provenance(tmp_path: Path):
    history = RunHistory(tmp_path / "history.sqlite3")
    success_id = history.record("ds-1", "b" * 64, "analytics", "SUCCEEDED", {"schema_version": "2.0.0", "value": 42}, "LOCAL")
    failure_id = history.record_failure("ds-1", "b" * 64, "ml", ValueError("bad target"), "LOCAL")

    assert success_id > 0
    assert failure_id > success_id
    latest = history.latest("ds-1", "analytics")
    assert latest["value"] == 42
    assert latest["provenance"]["dataset_fingerprint"] == "b" * 64
    runs = history.list("ds-1")
    assert {run["status"] for run in runs} == {"SUCCEEDED", "FAILED"}


def test_run_history_latest_matching_requires_current_fingerprint_and_schema(tmp_path: Path):
    history = RunHistory(tmp_path / "history.sqlite3")
    history.record(
        "ds-1", "b" * 64, "analytics", "SUCCEEDED",
        {"schema_version": "2.0.0", "value": 42}, "LOCAL",
    )

    assert history.latest_matching("ds-1", "analytics", "b" * 64, "2.0.0")["value"] == 42
    assert history.latest_matching("ds-1", "analytics", "c" * 64, "2.0.0") is None
    assert history.latest_matching("ds-1", "analytics", "b" * 64, "3.0.0") is None
    assert history.latest_matching("ds-1", "analytics", "b" * 64) is not None


def test_run_history_latest_matching_recovers_older_valid_run(tmp_path: Path):
    history = RunHistory(tmp_path / "history.sqlite3")
    history.record(
        "ds-1", "b" * 64, "analytics", "SUCCEEDED",
        {"schema_version": "2.0.0", "value": "valid"}, "LOCAL",
    )
    history.record(
        "ds-1", "c" * 64, "analytics", "SUCCEEDED",
        {"schema_version": "2.0.0", "value": "stale"}, "LOCAL",
    )

    recovered = history.latest_matching("ds-1", "analytics", "b" * 64, "2.0.0")
    assert recovered is not None
    assert recovered["value"] == "valid"


def test_run_history_latest_matching_skips_newer_schema_mismatch(tmp_path: Path):
    history = RunHistory(tmp_path / "history.sqlite3")
    history.record("ds-1", "b" * 64, "analytics", "SUCCEEDED", {"schema_version": "2.0.0", "value": "older-valid"}, "LOCAL")
    history.record("ds-1", "b" * 64, "analytics", "SUCCEEDED", {"schema_version": "3.0.0", "value": "newer-incompatible"}, "LOCAL")

    recovered = history.latest_matching("ds-1", "analytics", "b" * 64, "2.0.0")
    assert recovered is not None
    assert recovered["value"] == "older-valid"


def test_run_history_latest_matching_ignores_corrupt_success_payload(tmp_path: Path):
    db_path = tmp_path / "history.sqlite3"
    history = RunHistory(db_path)
    history.record("ds-1", "b" * 64, "analytics", "SUCCEEDED", {"schema_version": "2.0.0", "value": "valid"}, "LOCAL")
    with sqlite3.connect(db_path) as db:
        db.execute(
            "INSERT INTO runs(dataset_id,fingerprint,operation,engine,status,created_at,result_json) VALUES(?,?,?,?,?,?,?)",
            ("ds-1", "b" * 64, "analytics", "LOCAL", "SUCCEEDED", "2026-01-01T00:00:00+00:00", "{not-json"),
        )
        db.commit()

    recovered = history.latest_matching("ds-1", "analytics", "b" * 64, "2.0.0")
    assert recovered is not None
    assert recovered["value"] == "valid"
