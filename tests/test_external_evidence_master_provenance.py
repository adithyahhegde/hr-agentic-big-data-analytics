from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.validate_external_spark_evidence import validate_evidence


@pytest.fixture(autouse=True)
def _clean_validation_environment(monkeypatch):
    for name in ("GITHUB_SHA", "HR_ANALYTICS_SPARK_MASTER", "SPARK_VALIDATION_VERSION"):
        monkeypatch.delenv(name, raising=False)


def _payload() -> dict:
    execution = {
        "spark_version": "3.5.8",
        "default_parallelism": 2,
        "application_id": "app-1",
        "input_mode": "driver_parallelized_csv",
    }
    validation = {
        "row_count_matches_fixture": True,
        "distributed": True,
        "raw_rows_returned": False,
        "aggregates_match_local_baseline": True,
        "spark_version_present": True,
        "parallelism_positive": True,
        "application_id_present": True,
    }
    return {
        "protocol": "external_spark_scalability_v2",
        "seed": 42,
        "sizes": [10],
        "source_revision": "a" * 40,
        "runtime": {"python_version": "3.10.0", "platform": "Linux"},
        "master_kind": "spark",
        "target_fingerprint": "b" * 64,
        "runs": [
            {
                "rows": 10,
                "fixture_sha256": "c" * 64,
                "fixture_schema": ["employee_id", "salary"],
                "elapsed_seconds": 0.1,
                "rows_per_second": 100.0,
                "result": {"execution": execution},
                "validation": validation,
            }
        ],
        "scaling": {"adjacent_comparisons": []},
    }


def _write(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "external-spark.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_evidence_requires_spark_master_kind(tmp_path):
    payload = _payload()
    payload["master_kind"] = "local"
    with pytest.raises(ValueError, match="master_kind"):
        validate_evidence(_write(tmp_path, payload))


def test_evidence_accepts_spark_master_kind(tmp_path):
    summary = validate_evidence(_write(tmp_path, _payload()))
    assert summary["run_count"] == 1
    assert summary["sizes"] == [10]


def test_evidence_rejects_missing_master_kind(tmp_path):
    payload = _payload()
    payload.pop("master_kind")
    with pytest.raises(ValueError, match="master_kind"):
        validate_evidence(_write(tmp_path, payload))
