from __future__ import annotations

import pytest

import scripts.external_spark_validation as external_validation
from scripts.external_spark_validation import validate


def test_external_validation_requires_explicit_master(monkeypatch):
    monkeypatch.delenv("HR_ANALYTICS_SPARK_MASTER", raising=False)
    with pytest.raises(ValueError, match="HR_ANALYTICS_SPARK_MASTER"):
        validate(rows=10)


def test_external_validation_rejects_local_master():
    with pytest.raises(ValueError, match="non-local Spark master"):
        validate(rows=10, master="local[*]")


def test_external_validation_protocol_has_bounded_defaults():
    import inspect

    signature = inspect.signature(validate)
    assert signature.parameters["rows"].default == 10_000
    assert signature.parameters["seed"].default == 42


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
    assert result["protocol"] == "external_spark_validation_v1"
    assert result["validation"] == {
        "row_count_matches_fixture": True,
        "raw_rows_returned": False,
        "distributed": True,
    }
