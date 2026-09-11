from __future__ import annotations

import hashlib
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
        "master_kind": "spark",
        "target_fingerprint": "d" * 64,
        "runs": [
            {
                "rows": 100,
                "fixture_sha256": "b" * 64,
                "fixture_schema": ["age", "department"],
                "elapsed_seconds": 1.25,
                "rows_per_second": 80.0,
                "validation": {"row_count_matches_fixture": True, "distributed": True, "raw_rows_returned": False, "aggregates_match_local_baseline": True, "spark_version_present": True, "parallelism_positive": True, "application_id_present": True},
                "result": {"execution": {"spark_version": "3.5.8", "default_parallelism": 2, "application_id": "app-test-100", "input_mode": "driver_parallelized_csv"}},
            },
            {
                "rows": 1000,
                "fixture_sha256": "c" * 64,
                "fixture_schema": ["age", "department"],
                "elapsed_seconds": 2.5,
                "rows_per_second": 400.0,
                "validation": {"row_count_matches_fixture": True, "distributed": True, "raw_rows_returned": False, "aggregates_match_local_baseline": True, "spark_version_present": True, "parallelism_positive": True, "application_id_present": True},
                "result": {"execution": {"spark_version": "3.5.8", "default_parallelism": 2, "application_id": "app-test-1000", "input_mode": "driver_parallelized_csv"}},
            },
        ],
    }


def test_evidence_validator_accepts_complete_contract(tmp_path, monkeypatch):
    monkeypatch.delenv("GITHUB_SHA", raising=False)
    monkeypatch.delenv("HR_ANALYTICS_SPARK_MASTER", raising=False)
    monkeypatch.delenv("SPARK_VALIDATION_VERSION", raising=False)
    summary = validate_evidence(_write(tmp_path, _valid_payload()))
    assert summary["source_revision"] == "a" * 40
    assert summary["target_fingerprint"] == "d" * 64
    assert summary["run_count"] == 2
    assert summary["sizes"] == [100, 1000]


def test_evidence_validator_rejects_source_revision_drift_against_github_sha(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_SHA", "b" * 40)
    with pytest.raises(ValueError, match="source_revision.*GITHUB_SHA"):
        validate_evidence(_write(tmp_path, _valid_payload()))


def test_evidence_validator_accepts_matching_github_sha(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_SHA", "a" * 40)
    monkeypatch.delenv("HR_ANALYTICS_SPARK_MASTER", raising=False)
    validate_evidence(_write(tmp_path, _valid_payload()))


def test_evidence_validator_rejects_target_fingerprint_drift_against_master(tmp_path, monkeypatch):
    monkeypatch.setenv("HR_ANALYTICS_SPARK_MASTER", "spark://cluster.example:7077")
    with pytest.raises(ValueError, match="target_fingerprint.*HR_ANALYTICS_SPARK_MASTER"):
        validate_evidence(_write(tmp_path, _valid_payload()))


def test_evidence_validator_accepts_matching_target_fingerprint(tmp_path, monkeypatch):
    payload = _valid_payload()
    master = "spark://cluster.example:7077"
    payload["target_fingerprint"] = hashlib.sha256(master.encode()).hexdigest()
    monkeypatch.setenv("HR_ANALYTICS_SPARK_MASTER", master)
    monkeypatch.delenv("GITHUB_SHA", raising=False)
    validate_evidence(_write(tmp_path, payload))


def test_evidence_validator_rejects_inconsistent_spark_versions(tmp_path):
    payload = _valid_payload()
    payload["runs"][1]["result"]["execution"]["spark_version"] = "3.5.7"
    with pytest.raises(ValueError, match="same Spark version"):
        validate_evidence(_write(tmp_path, payload))


def test_evidence_validator_rejects_duplicate_application_ids(tmp_path):
    payload = _valid_payload()
    payload["runs"][1]["result"]["execution"]["application_id"] = "app-test-100"
    with pytest.raises(ValueError, match="application IDs must be unique"):
        validate_evidence(_write(tmp_path, payload))


def test_evidence_validator_rejects_zero_elapsed_time(tmp_path):
    payload = _valid_payload()
    payload["runs"][0]["elapsed_seconds"] = 0
    with pytest.raises(ValueError, match="positive elapsed_seconds"):
        validate_evidence(_write(tmp_path, payload))


@pytest.mark.parametrize("revision", ["unknown", "", "A" * 40, "a" * 39, "a" * 41])
def test_evidence_validator_rejects_invalid_source_revision(tmp_path, revision):
    payload = _valid_payload()
    payload["source_revision"] = revision
    with pytest.raises(ValueError, match="40-character lowercase Git commit SHA"):
        validate_evidence(_write(tmp_path, payload))


@pytest.mark.parametrize("target_fingerprint", ["", "unknown", "A" * 64, "d" * 63, "d" * 65])
def test_evidence_validator_rejects_invalid_target_fingerprint(tmp_path, target_fingerprint):
    payload = _valid_payload()
    payload["target_fingerprint"] = target_fingerprint
    with pytest.raises(ValueError, match="target_fingerprint"):
        validate_evidence(_write(tmp_path, payload))


@pytest.mark.parametrize("runtime", [None, {}, {"python_version": "3.10"}, {"platform": "linux"}])
def test_evidence_validator_requires_runtime_provenance(tmp_path, runtime):
    payload = _valid_payload()
    payload["runtime"] = runtime
    with pytest.raises(ValueError, match="runtime"):
        validate_evidence(_write(tmp_path, payload))


def test_evidence_validator_rejects_missing_or_wrong_master_kind(tmp_path):
    for value in [None, "", "http"]:
        payload = _valid_payload()
        if value is None:
            payload.pop("master_kind")
        else:
            payload["master_kind"] = value
        with pytest.raises(ValueError, match="master_kind"):
            validate_evidence(_write(tmp_path, payload))


def test_evidence_validator_requires_runs(tmp_path):
    payload = _valid_payload()
    payload["runs"] = []
    with pytest.raises(ValueError, match="at least one run"):
        validate_evidence(_write(tmp_path, payload))


def test_evidence_validator_rejects_protocol_or_seed_drift(tmp_path):
    for field, value, message in [("protocol", "other", "protocol"), ("seed", 7, "seed")]:
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
    for key, value, message in [("aggregates_match_local_baseline", False, "aggregate"), ("raw_rows_returned", True, "raw rows"), ("distributed", False, "distributed")]:
        payload = _valid_payload()
        payload["runs"][0]["validation"][key] = value
        with pytest.raises(ValueError, match=message):
            validate_evidence(_write(tmp_path, payload))


def test_evidence_validator_requires_execution_contract(tmp_path):
    payload = _valid_payload()
    payload["runs"][0]["result"]["execution"]["input_mode"] = "shared_filesystem"
    with pytest.raises(ValueError, match="input_mode"):
        validate_evidence(_write(tmp_path, payload))


@pytest.mark.parametrize("field", ["elapsed_seconds", "rows_per_second"])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_evidence_validator_rejects_non_finite_metrics(tmp_path, field, value):
    payload = _valid_payload()
    payload["runs"][0][field] = value
    with pytest.raises(ValueError, match="finite number"):
        validate_evidence(_write(tmp_path, payload))


def test_evidence_validator_rejects_boolean_parallelism(tmp_path):
    payload = _valid_payload()
    payload["runs"][0]["result"]["execution"]["default_parallelism"] = True
    with pytest.raises(ValueError, match="positive execution.default_parallelism"):
        validate_evidence(_write(tmp_path, payload))


def test_evidence_validator_rejects_spark_version_drift_against_workflow_input(tmp_path, monkeypatch):
    monkeypatch.setenv("SPARK_VALIDATION_VERSION", "3.5.8")
    payload = _valid_payload()
    payload["runs"][0]["result"]["execution"]["spark_version"] = "3.5.7"
    with pytest.raises(ValueError, match="Spark version does not match SPARK_VALIDATION_VERSION"):
        validate_evidence(_write(tmp_path, payload))


def test_evidence_validator_accepts_matching_spark_version_against_workflow_input(tmp_path, monkeypatch):
    monkeypatch.setenv("SPARK_VALIDATION_VERSION", "3.5.8")
    validate_evidence(_write(tmp_path, _valid_payload()))


@pytest.mark.parametrize("version", ["", "3.5 8", "x" * 65])
def test_evidence_validator_rejects_invalid_expected_spark_version(tmp_path, monkeypatch, version):
    monkeypatch.setenv("SPARK_VALIDATION_VERSION", version)
    with pytest.raises(ValueError, match="SPARK_VALIDATION_VERSION"):
        validate_evidence(_write(tmp_path, _valid_payload()))
