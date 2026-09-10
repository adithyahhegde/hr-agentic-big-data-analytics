from __future__ import annotations

import scripts.external_spark_validation as external_validation


def test_external_validation_records_reproducibility_metadata(monkeypatch):
    monkeypatch.setenv("GITHUB_SHA", "abc123")

    def fake_local(path, mappings):
        rows = len(path.read_text(encoding="utf-8").splitlines()) - 1
        return {
            "row_count": rows,
            "duplicate_row_count": 0,
            "numeric_summary": [],
            "categorical_summary": [],
            "missing_by_field": [],
        }

    def fake_spark(lines, mappings, **kwargs):
        rows = len(lines) - 1
        return {
            "row_count": rows,
            "duplicate_row_count": 0,
            "numeric_summary": [],
            "categorical_summary": [],
            "missing_by_field": [],
            "execution": {
                "distributed": True,
                "raw_rows_returned": False,
                "spark_version": "3.5.8",
                "default_parallelism": 2,
                "application_id": "app-test",
                "input_mode": "driver_parallelized_csv",
            },
        }

    monkeypatch.setattr(external_validation, "analyze_csv", fake_local)
    monkeypatch.setattr(external_validation, "analyze_spark_csv_lines", fake_spark)

    result = external_validation.validate_sizes(sizes=[100], seed=42, master="spark://example:7077")
    assert result["source_revision"] == "abc123"
    assert result["runtime"]["python_version"]
    assert result["runtime"]["platform"]


def test_external_validation_uses_explicit_source_revision_override(monkeypatch):
    monkeypatch.delenv("GITHUB_SHA", raising=False)
    monkeypatch.setenv("HR_ANALYTICS_SOURCE_REVISION", "manual-revision")

    monkeypatch.setattr(
        external_validation,
        "analyze_csv",
        lambda path, mappings: {
            "row_count": 1,
            "duplicate_row_count": 0,
            "numeric_summary": [],
            "categorical_summary": [],
            "missing_by_field": [],
        },
    )
    monkeypatch.setattr(
        external_validation,
        "analyze_spark_csv_lines",
        lambda lines, mappings, **kwargs: {
            "row_count": 1,
            "duplicate_row_count": 0,
            "numeric_summary": [],
            "categorical_summary": [],
            "missing_by_field": [],
            "execution": {
                "distributed": True,
                "raw_rows_returned": False,
                "spark_version": "3.5.8",
                "default_parallelism": 2,
                "application_id": "app-test",
                "input_mode": "driver_parallelized_csv",
            },
        },
    )

    result = external_validation.validate_sizes(sizes=[1], seed=42, master="spark://example:7077")
    assert result["source_revision"] == "manual-revision"
