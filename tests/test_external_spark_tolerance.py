from __future__ import annotations

import pytest

from scripts.external_spark_validation import _aggregate_values_match, _validate_result


def test_aggregate_comparison_allows_small_float_drift():
    expected = {"mean": 123.456789}
    actual = {"mean": 123.4567891}
    assert _aggregate_values_match(actual, expected)


def test_aggregate_comparison_rejects_material_float_drift():
    expected = {"mean": 123.456789}
    actual = {"mean": 123.5}
    assert not _aggregate_values_match(actual, expected)


def test_validation_records_tolerant_aggregate_match():
    result = {
        "row_count": 2,
        "duplicate_row_count": 0,
        "numeric_summary": [{"field": "age", "count": 2, "min": 20.0, "max": 30.0, "mean": 25.0000001}],
        "categorical_summary": [],
        "missing_by_field": [],
        "execution": {"distributed": True, "raw_rows_returned": False},
    }
    expected = {
        "row_count": 2,
        "duplicate_row_count": 0,
        "numeric_summary": [{"field": "age", "count": 2, "min": 20.0, "max": 30.0, "mean": 25.0}],
        "categorical_summary": [],
        "missing_by_field": [],
    }
    validation = _validate_result(result, 2, expected)
    assert validation["aggregates_match_local_baseline"] is True


def test_validation_still_rejects_material_aggregate_drift():
    result = {
        "row_count": 2,
        "duplicate_row_count": 0,
        "numeric_summary": [{"field": "age", "count": 2, "min": 20.0, "max": 30.0, "mean": 31.0}],
        "categorical_summary": [],
        "missing_by_field": [],
        "execution": {"distributed": True, "raw_rows_returned": False},
    }
    expected = {
        "row_count": 2,
        "duplicate_row_count": 0,
        "numeric_summary": [{"field": "age", "count": 2, "min": 20.0, "max": 30.0, "mean": 25.0}],
        "categorical_summary": [],
        "missing_by_field": [],
    }
    with pytest.raises(RuntimeError, match="aggregates differ"):
        _validate_result(result, 2, expected)
