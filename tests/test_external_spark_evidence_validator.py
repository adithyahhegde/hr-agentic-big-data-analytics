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
        "source_revision": "a" * 40,
        "runtime": {"python_version": "3.10.0", "platform": "test-platform"},
        "runs": [{"rows": 100}],
    }


def test_evidence_validator_accepts_complete_provenance(tmp_path):
    summary = validate_evidence(_write(tmp_path, _valid_payload()))
    assert summary["source_revision"] == "a" * 40
    assert summary["run_count"] == 1


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
