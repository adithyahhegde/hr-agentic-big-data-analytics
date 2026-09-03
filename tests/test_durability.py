from pathlib import Path

from app.services.dataset_registry import DatasetRegistry
from app.services.run_history import RunHistory


class Dataset:
    dataset_id = "d1"
    sha256 = "abc"
    filename = "hr.csv"
    path = Path("data/datasets/d1.csv")
    size_bytes = 10
    row_count = 2
    column_count = 1


def test_registry_persists_profile_and_mappings(tmp_path):
    registry = DatasetRegistry(tmp_path / "state.sqlite3")
    registry.register(Dataset())
    profile = {"dataset_id": "d1", "row_count": 2}
    registry.save_profile("d1", type("Profile", (), {"model_dump": lambda self, mode=None: profile})())
    registry.save_mappings("d1", {"Employee ID": "employee_id"})
    reopened = DatasetRegistry(tmp_path / "state.sqlite3")
    assert reopened.get_profile("d1") == profile
    assert reopened.get_mappings("d1") == {"Employee ID": "employee_id"}


def test_run_history_latest_ignores_failed_runs(tmp_path):
    history = RunHistory(tmp_path / "state.sqlite3")
    history.record("d1", "abc", "analytics", "SUCCEEDED", {"metric": 1})
    history.record("d1", "abc", "analytics", "FAILED", {"error": "boom"})
    assert history.latest("d1", "analytics")["metric"] == 1
