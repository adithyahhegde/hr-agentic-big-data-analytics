from __future__ import annotations

import pytest

import scripts.external_spark_validation as external_validation
from scripts.external_spark_validation import validate, validate_sizes


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
        return {"row_count": 10, "execution": {"distributed": True, "raw_rows_returned": False}}

    monkeypatch.setattr(external_validation, "analyze_spark", fake_analyze)
    result = validate(rows=10, master="  spark://example:7077  ")
    assert result["validation"]["distributed"] is True


def test_external_validation_protocol_has_bounded_defaults():
    import inspect

    signature = inspect.signature(validate)
    assert signature.parameters["rows"].default == 10_000
    assert signature.parameters["seed"].default == 42
    assert external_validation.DEFAULT_SIZES == (100, 1_000, 10_000)


def test_external_validation_rejects_invalid_sizes(monkeypatch):
    with pytest.raises(ValueError, match="positive integers"):
        validate_sizes(sizes=[0, 10], master="spark://example:7077")


def test_external_validation_normalizes_sizes_and_records_timings(monkeypatch):
    calls = []

    def fake_analyze(path, mappings, **kwargs):
        rows = int(path.stem.split("-")[-1])
        calls.append((rows, kwargs["master"]))
        return {"row_count": rows, "execution": {"distributed": True, "raw_rows_returned": False}}

    monkeypatch.setattr(external_validation, "analyze_spark", fake_analyze)
    result = validate_sizes(sizes=[1000, 100, 1000], seed=42, master="spark://example:7077")
    assert result["protocol"] == "external_spark_scalability_v1"
    assert result["sizes"] == [100, 1000]
    assert [run["rows"] for run in result["runs"]] == [100, 1000]
    assert all(run["elapsed_seconds"] >= 0 for run in result["runs"])
    assert all(run["rows_per_second"] is not None and run["rows_per_second"] > 0 for run in result["runs"])
    assert calls == [(100, "spark://example:7077"), (1000, "spark://example:7077")]


def test_external_validation_requires_distributed_and_non_raw_result(monkeypatch):
    def fake_analyze(*args, **kwargs):
        return {
            "row_count": 10,
            "execution": {"distributed": False, "raw_rows_returned": False},
        }

    monkeypatch.setattr(external_validation, "analyze_spark", fake_analyze)
    with pytest.raises(RuntimeError, match="distributed execution"):
        validate(rows=10, master="spark://example:7077")


def test_external_validation_rejects_raw_rows(monkeypatch):
    def fake_analyze(*args, **kwargs):
        return {
            "row_count": 10,
            "execution": {"distributed": True, "raw_rows_returned": True},
        }

    monkeypatch.setattr(external_validation, "analyze_spark", fake_analyze)
    with pytest.raises(RuntimeError, match="must not return raw rows"):
        validate(rows=10, master="spark://example:7077")


def test_external_validation_returns_verified_contract(monkeypatch):
    def fake_analyze(*args, **kwargs):
        return {
            "row_count": 10,
            "execution": {"distributed": True, "raw_rows_returned": False},
            "numeric_summary": {},
        }

    monkeypatch.setattr(external_validation, "analyze_spark", fake_analyze)
    result = validate(rows=10, seed=42, master="spark://example:7077")
    assert result["validation"]["distributed"] is True
    assert result["rows"] == 10
    assert result["elapsed_seconds"] >= 0
    assert result["rows_per_second"] > 0
