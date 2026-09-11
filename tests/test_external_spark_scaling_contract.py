from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.validate_external_spark_evidence import validate_evidence


@pytest.fixture(autouse=True)
def _clean_validation_environment(monkeypatch):
    for name in ("GITHUB_SHA", "HR_ANALYTICS_SPARK_MASTER", "SPARK_VALIDATION_VERSION"):
        monkeypatch.delenv(name, raising=False)


def _artifact(tmp_path: Path, **overrides):
    runs = [
        {"rows": 100, "fixture_sha256": "a" * 64, "fixture_schema": ["employee_id"], "elapsed_seconds": 1.0, "rows_per_second": 100.0, "validation": {"row_count_matches_fixture": True, "distributed": True, "raw_rows_returned": False, "aggregates_match_local_baseline": True, "spark_version_present": True, "parallelism_positive": True, "application_id_present": True}, "result": {"execution": {"spark_version": "3.5.8", "default_parallelism": 2, "application_id": "app-1", "input_mode": "driver_parallelized_csv"}}},
        {"rows": 1000, "fixture_sha256": "b" * 64, "fixture_schema": ["employee_id"], "elapsed_seconds": 2.0, "rows_per_second": 500.0, "validation": {"row_count_matches_fixture": True, "distributed": True, "raw_rows_returned": False, "aggregates_match_local_baseline": True, "spark_version_present": True, "parallelism_positive": True, "application_id_present": True}, "result": {"execution": {"spark_version": "3.5.8", "default_parallelism": 2, "application_id": "app-2", "input_mode": "driver_parallelized_csv"}}},
    ]
    data = {"protocol": "external_spark_scalability_v2", "seed": 42, "sizes": [100, 1000], "source_revision": "a" * 40, "runtime": {"python_version": "3.10", "platform": "test"}, "master_kind": "spark", "target_fingerprint": "c" * 64, "runs": runs, "scaling": {"adjacent_comparisons": [{"from_rows": 100, "to_rows": 1000, "row_growth_factor": 10.0, "elapsed_growth_factor": 2.0, "throughput_growth_factor": 5.0}], "largest_to_smallest_elapsed_ratio": 2.0, "largest_to_smallest_throughput_ratio": 5.0}}
    data.update(overrides)
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_validator_requires_scaling_summary(tmp_path):
    path = _artifact(tmp_path)
    data = json.loads(path.read_text())
    data.pop("scaling")
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="scaling summary is required"):
        validate_evidence(path)


def test_validator_accepts_scaling_summary(tmp_path):
    summary = validate_evidence(_artifact(tmp_path))
    assert summary["scaling_intervals"] == 1


def test_validator_rejects_inconsistent_adjacent_scaling(tmp_path):
    path = _artifact(tmp_path)
    data = json.loads(path.read_text())
    data["scaling"]["adjacent_comparisons"][0]["elapsed_growth_factor"] = 9.0
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="elapsed_growth_factor does not match benchmark runs"):
        validate_evidence(path)


def test_validator_rejects_inconsistent_overall_scaling(tmp_path):
    path = _artifact(tmp_path)
    data = json.loads(path.read_text())
    data["scaling"]["largest_to_smallest_throughput_ratio"] = 2.0
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="largest_to_smallest_throughput_ratio does not match benchmark runs"):
        validate_evidence(path)
