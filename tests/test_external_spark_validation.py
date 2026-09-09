from __future__ import annotations

from pathlib import Path

import pytest

import scripts.external_spark_validation as external_validation
from scripts.external_spark_validation import validate, validate_sizes

ROOT = Path(__file__).resolve().parents[1]
EXTERNAL_WORKFLOW = (ROOT / ".github" / "workflows" / "external-spark-validation.yml").read_text(encoding="utf-8")
EVALUATION_WORKFLOW = (ROOT / ".github" / "workflows" / "evaluation.yml").read_text(encoding="utf-8")


def test_external_validation_requires_explicit_master(monkeypatch):
    monkeypatch.delenv("HR_ANALYTICS_SPARK_MASTER", raising=False)
    with pytest.raises(ValueError, match="HR_ANALYTICS_SPARK_MASTER"):
        validate(rows=10)


def test_external_validation_rejects_local_master():
    with pytest.raises(ValueError, match="non-local Spark master"):
        validate(rows=10, master="local[*]")


@pytest.mark.parametrize("master", ["spark://localhost:7077", "spark://127.0.0.1:7077", "spark://[::1]:7077"])
def test_external_validation_rejects_loopback_master(master):
    with pytest.raises(ValueError, match="non-loopback Spark master"):
        validate(rows=10, master=master)


@pytest.mark.parametrize("master", ["spark://example", "http://example:7077", "spark://example:not-a-port"])
def test_external_validation_rejects_malformed_master(master):
    with pytest.raises(ValueError, match="spark://host:7077"):
        validate(rows=10, master=master)


def test_external_validation_rejects_whitespace_only_master(monkeypatch):
    monkeypatch.delenv("HR_ANALYTICS_SPARK_MASTER", raising=False)
    with pytest.raises(ValueError, match="HR_ANALYTICS_SPARK_MASTER"):
        validate(rows=10, master="   ")


def test_external_validation_strips_master_whitespace(monkeypatch):
    def fake_analyze(*args, **kwargs):
        assert kwargs["master"] == "spark://example:7077"
        assert kwargs["stop_session"] is True
        return {"row_count": 10, "execution": {"distributed": True, "raw_rows_returned": False}}

    monkeypatch.setattr(external_validation, "analyze_spark_csv_lines", fake_analyze)
    result = validate(rows=10, master="  spark://example:7077  ")
    assert result["validation"]["distributed"] is True


def test_external_validation_protocol_has_bounded_defaults():
    import inspect

    signature = inspect.signature(validate)
    assert signature.parameters["rows"].default == 10_000
    assert signature.parameters["seed"].default == 42
    assert external_validation.DEFAULT_SIZES == (100, 1_000, 10_000)
    assert external_validation.PROTOCOL_VERSION == "external_spark_scalability_v2"


def test_external_validation_rejects_invalid_sizes(monkeypatch):
    with pytest.raises(ValueError, match="positive integers"):
        validate_sizes(sizes=[0, 10], master="spark://example:7077")


def test_external_validation_normalizes_sizes_and_records_timings(monkeypatch):
    calls = []

    def fake_analyze(path_lines, mappings, **kwargs):
        rows = len(path_lines) - 1
        calls.append((rows, kwargs["master"], kwargs["stop_session"], path_lines[0]))
        return {"row_count": rows, "execution": {"distributed": True, "raw_rows_returned": False}}

    monkeypatch.setattr(external_validation, "analyze_spark_csv_lines", fake_analyze)
    result = validate_sizes(sizes=[1000, 100, 1000], seed=42, master="spark://example:7077")
    assert result["protocol"] == "external_spark_scalability_v2"
    assert result["sizes"] == [100, 1000]
    assert [run["rows"] for run in result["runs"]] == [100, 1000]
    assert all(run["elapsed_seconds"] >= 0 for run in result["runs"])
    assert all(run["rows_per_second"] is not None and run["rows_per_second"] > 0 for run in result["runs"])
    assert all(len(run["fixture_sha256"]) == 64 for run in result["runs"])
    assert result["started_at"].endswith("Z")
    assert calls[0][0] == 100
    assert calls[1][0] == 1000
    assert all(call[1] == "spark://example:7077" for call in calls)
    assert all(call[2] is True for call in calls)
    assert all(call[3].startswith("employee_id,") for call in calls)


def test_external_validation_fixture_fingerprint_is_reproducible(monkeypatch):
    def fake_analyze(*args, **kwargs):
        rows = len(args[0]) - 1
        return {"row_count": rows, "execution": {"distributed": True, "raw_rows_returned": False}}

    monkeypatch.setattr(external_validation, "analyze_spark_csv_lines", fake_analyze)
    first = validate_sizes(sizes=[100], seed=42, master="spark://example:7077")
    second = validate_sizes(sizes=[100], seed=42, master="spark://example:7077")
    assert first["runs"][0]["fixture_sha256"] == second["runs"][0]["fixture_sha256"]
    assert first["runs"][0]["fixture_schema"] == second["runs"][0]["fixture_schema"]


def test_external_validation_preserves_cluster_provenance(monkeypatch):
    def fake_analyze(*args, **kwargs):
        return {
            "row_count": 10,
            "execution": {
                "distributed": True,
                "raw_rows_returned": False,
                "spark_version": "4.0.0",
                "default_parallelism": 4,
                "application_id": "app-123",
                "input_mode": "driver_parallelized_csv",
            },
        }

    monkeypatch.setattr(external_validation, "analyze_spark_csv_lines", fake_analyze)
    result = validate(rows=10, master="spark://example:7077")
    execution = result["result"]["execution"]
    assert execution["spark_version"] == "4.0.0"
    assert execution["default_parallelism"] == 4
    assert execution["application_id"] == "app-123"
    assert execution["input_mode"] == "driver_parallelized_csv"


def test_external_validation_requires_distributed_and_non_raw_result(monkeypatch):
    def fake_analyze(*args, **kwargs):
        return {
            "row_count": 10,
            "execution": {"distributed": False, "raw_rows_returned": False},
        }

    monkeypatch.setattr(external_validation, "analyze_spark_csv_lines", fake_analyze)
    with pytest.raises(RuntimeError, match="distributed execution"):
        validate(rows=10, master="spark://example:7077")


def test_external_validation_rejects_raw_rows(monkeypatch):
    def fake_analyze(*args, **kwargs):
        return {
            "row_count": 10,
            "execution": {"distributed": True, "raw_rows_returned": True},
        }

    monkeypatch.setattr(external_validation, "analyze_spark_csv_lines", fake_analyze)
    with pytest.raises(RuntimeError, match="must not return raw rows"):
        validate(rows=10, master="spark://example:7077")


def test_external_validation_returns_verified_contract(monkeypatch):
    def fake_analyze(*args, **kwargs):
        return {
            "row_count": 10,
            "execution": {"distributed": True, "raw_rows_returned": False},
            "numeric_summary": {},
        }

    monkeypatch.setattr(external_validation, "analyze_spark_csv_lines", fake_analyze)
    result = validate(rows=10, seed=42, master="spark://example:7077")
    assert result["validation"]["distributed"] is True
    assert result["rows"] == 10
    assert result["elapsed_seconds"] >= 0
    assert result["rows_per_second"] > 0


def test_external_validation_rejects_aggregate_mismatch(monkeypatch):
    def fake_analyze(path_lines, mappings, **kwargs):
        rows = len(path_lines) - 1
        return {
            "row_count": rows,
            "duplicate_row_count": 0,
            "numeric_summary": [],
            "categorical_summary": [],
            "missing_by_field": [],
            "execution": {"distributed": True, "raw_rows_returned": False},
        }

    monkeypatch.setattr(external_validation, "analyze_spark_csv_lines", fake_analyze)
    with pytest.raises(RuntimeError, match="aggregates differ"):
        validate(rows=10, seed=42, master="spark://example:7077")


def test_external_validation_accepts_matching_aggregate_baseline(monkeypatch):
    result = external_validation._validate_result(
        {
            "row_count": 1,
            "duplicate_row_count": 0,
            "numeric_summary": [],
            "categorical_summary": [],
            "missing_by_field": [],
            "execution": {"distributed": True, "raw_rows_returned": False},
        },
        1,
        {"row_count": 1, "duplicate_row_count": 0, "numeric_summary": [], "categorical_summary": [], "missing_by_field": []},
    )
    assert result["aggregates_match_local_baseline"] is True


def test_external_workflows_validate_the_v2_artifact_contract():
    for workflow in (EXTERNAL_WORKFLOW, EVALUATION_WORKFLOW):
        assert "external_spark_scalability_v2" in workflow
        assert "result['protocol']" in workflow or "result[\"protocol\"]" in workflow
        assert "run['rows']" in workflow or "run[\"rows\"]" in workflow
        assert "validation['distributed']" in workflow or "validation[\"distributed\"]" in workflow
        assert "validation['raw_rows_returned']" in workflow or "validation[\"raw_rows_returned\"]" in workflow
        assert "aggregates_match_local_baseline" in workflow
        assert "rows_per_second" in workflow

    assert "protocol_version" not in EXTERNAL_WORKFLOW
    assert "measurements" not in EXTERNAL_WORKFLOW
