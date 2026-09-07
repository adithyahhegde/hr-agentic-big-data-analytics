from pathlib import Path
from types import SimpleNamespace

from app.services.dataset_registry import DatasetRegistry
from app.services.run_history import RunHistory


def test_dataset_registry_round_trips_manifest_profile_and_mappings(tmp_path: Path):
    registry = DatasetRegistry(tmp_path / "registry.sqlite3")
    csv_path = tmp_path / "dataset.csv"
    csv_path.write_text("employee_id,salary\nE1,50000\n", encoding="utf-8")
    dataset = SimpleNamespace(
        dataset_id="ds-1",
        sha256="a" * 64,
        filename="dataset.csv",
        path=csv_path,
        size_bytes=32,
        row_count=1,
        column_count=2,
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
        dataset_id="ds-1",
        sha256="a" * 64,
        filename="dataset.csv",
        path=csv_path,
        size_bytes=32,
        row_count=1,
        column_count=2,
    )
    registry.register(dataset)
    registry.save_profile("ds-1", SimpleNamespace(model_dump=lambda mode="json": {"dataset_id": "ds-1", "schema_version": "2.0.0"}))
    registry.save_mappings("ds-1", {"employee_id": "employee_id", "salary": "salary"})

    refreshed = SimpleNamespace(
        dataset_id="ds-1",
        sha256="c" * 64,
        filename="renamed.csv",
        path=tmp_path / "renamed.csv",
        size_bytes=64,
        row_count=2,
        column_count=2,
    )
    registry.register(refreshed)

    manifest = registry.get("ds-1")
    assert manifest["fingerprint"] == "c" * 64
    assert manifest["filename"] == "renamed.csv"
    assert registry.get_profile("ds-1")["schema_version"] == "2.0.0"
    assert registry.get_mappings("ds-1") == {"employee_id": "employee_id", "salary": "salary"}


def test_run_history_failure_does_not_persist_exception_message(tmp_path: Path):
    history = RunHistory(tmp_path / "history.sqlite3")
    secret = "E1,Adithya,50000"
    history.record_failure("ds-1", "b" * 64, "ml", ValueError(secret), "LOCAL")

    latest = history.list("ds-1")[0]
    assert latest["status"] == "FAILED"
    assert secret not in str(latest)
    stored = history.latest("ds-1", "ml")
    assert stored is None


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
