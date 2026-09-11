from __future__ import annotations

import json

import pytest

from scripts.validate_external_spark_evidence import validate_evidence


def _write(tmp_path, payload):
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _valid_payload():
    return {
        "protocol": "external_spark_scalability_v2",
        "seed": 42,
        "sizes": [100, 1000],
        "source_revision": "a" * 40,
        "runtime": {"python_version": "3.10.0", "platform": "test-platform"},
        "runs": [
            {
                "rows": 100,
                "fixture_sha256": "b" * 64,
                "fixture_schema": ["age", "department"],
                "elapsed_seconds": 1.25,
                "rows_per_second": 80.0,
                "validation": {
                    "row_count_matches_fixture": True,
                    "distributed": True,
                    "raw_rows_returned": False,
                    "aggregates_match_local_baseline": True,
                    "spark_version_present": True,
                    "parallelism_positive": True,
                    "application_id_present": True,
                },
                "result": {
                    "execution": {
                        "spark_version": "3.5.8",
                        "default_parallelism": 2,
                        "application_id": "app-test-100",
                        "input_mode": "driver_parallelized_csv",
                    }
                },
            },
            {
                "rows": 1000,
                "fixture_sha256": "c" * 64,
                "fixture_schema": ["age", "department"],
                "elapsed_seconds": 2.5,
                "rows_per_second": 400.0,
                "validation": {
                    "row_count_matches_fixture": True,
                    "distributed": True,
                    "raw_rows_returned": False,
                    "aggregates_match_local_baseline": True,
                    "spark_version_present": True,
                    "parallelism_positive": True,
                    "application_id_present": True,
                },
                "result": {
                    "execution": {
                        "spark_version": "3.5.8",
                        "default_parallelism": 2,
                        "application_id": "app-test-1000",
                        "input_mode": "driver_parallelized_csv",
                    }
                },
            },
        ],
    }


def test_evidence_validator_accepts_complete_contract(tmp_path):
    summary = validate_evidence(_write(tmp_path, _valid_payload()))
    assert summary["source_revision"] == "a" * 40
    assert summary["run_count"] == 2
    assert summary["sizes"] == [100, 1000]


@pytest.mark.parametrize("revision", ["unknown", "", "A" * 40, "a" * 39, "a" * 41])
def test_evidence_validator_rejects_invalid_source_revision(tmp_path, revision):
    payload = _valid_payload()
    payload["source_revision"] = revision
    with pytest.raises(ValueError, match="40-character lowercase Git commit SHA"):
        validate_evidence(_write(tmp_path, payload))


@pytest.mark.parametrize("runtime", [None, {}, {"python_version": "3.10"}, {"platform": "linux"}])
def test_evidence_validator_requires_runtime_provenance(tmp_path, runtime):
    payload = _valid_payload()
    payload["runtime"] = runtime
    with pytest.raises(ValueError, match="runtime"):
        validate_evidence(_write(tmp_path, payload))


def test_evidence_validator_requires_runs(tmp_path):
    payload = _valid_payload()
    payload["runs"] = []
    with pytest.raises(ValueError, match="at least one run"):
        validate_evidence(_write(tmp_path, payload))


def test_evidence_validator_rejects_protocol_or_seed_drift(tmp_path):
    for field, value, message in [
        ("protocol", "other", "protocol"),
        ("seed", 7, "seed"),
    ]:
        payload = _valid_payload()
        payload[field] = value
        with pytest.raises(ValueError, match=message):
            validate_evidence(_write(tmp_path, payload))


def test_evidence_validator_rejects_unsorted_or_duplicate_sizes(tmp_path):
    for sizes in ([1000, 100], [100, 100], []):
        payload = _valid_payload()
        payload["sizes"] = sizes
        with pytest.raises(ValueError, match="sizes"):
            validate_evidence(_write(tmp_path, payload))


def test_evidence_validator_rejects_run_size_mismatch(tmp_path):
    payload = _valid_payload()
    payload["runs"][1]["rows"] = 2000
    with pytest.raises(ValueError, match="row counts"):
        validate_evidence(_write(tmp_path, payload))


def test_evidence_validator_rejects_invalid_fixture_provenance(tmp_path):
    payload = _valid_payload()
    payload["runs"][0]["fixture_sha256"] = "bad"
    with pytest.raises(ValueError, match="fixture_sha256"):
        validate_evidence(_write(tmp_path, payload))


def test_evidence_validator_rejects_failed_aggregate_or_raw_row_checks(tmp_path):
    for key, value, message in [
        ("aggregates_match_local_baseline", False, "aggregate"),
        ("raw_rows_returned", True, "raw rows"),
        ("distributed", False, "distributed"),
    ]:
        payload = _valid_payload()
        payload["runs"][0]["validation"][key] = value
        with pytest.raises(ValueError, match=message):
            validate_evidence(_write(tmp_path, payload))


def test_evidence_validator_requires_execution_contract(tmp_path):
    payload = _valid_payload()
    payload["runs"][0]["result"]["execution"]["input_mode"] = "shared_filesystem"
    with pytest.raises(ValueError, match="input_mode"):
        validate_evidence(_write(tmp_path, payload))
