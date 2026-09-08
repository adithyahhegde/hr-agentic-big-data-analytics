from __future__ import annotations

import pytest

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
