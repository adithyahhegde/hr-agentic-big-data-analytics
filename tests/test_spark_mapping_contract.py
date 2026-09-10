from __future__ import annotations

import sys

import pytest

from app.services.spark_analytics import _canonicalize_dataframe, _number_columns, _spark_session


class FakeDataFrame:
    def __init__(self, columns):
        self.columns = list(columns)
        self.renames = []

    def withColumnRenamed(self, source, canonical):
        renamed = FakeDataFrame([canonical if column == source else column for column in self.columns])
        renamed.renames = [*self.renames, (source, canonical)]
        return renamed


def test_spark_mapping_normalizes_heterogeneous_headers_to_canonical_fields():
    frame = FakeDataFrame(["Employee ID", "Employee Age", "Dept", "Annual Pay"])
    normalized, fields = _canonicalize_dataframe(
        frame,
        {
            "Employee ID": "employee_id",
            "Employee Age": "age",
            "Dept": "department",
            "Annual Pay": "salary",
        },
    )

    assert normalized.columns == ["employee_id", "age", "department", "salary"]
    assert fields == ("age", "department", "employee_id", "salary")
    assert normalized.renames == [
        ("Employee ID", "employee_id"),
        ("Employee Age", "age"),
        ("Dept", "department"),
        ("Annual Pay", "salary"),
    ]


def test_spark_mapping_ignores_unknown_or_unmapped_source_columns():
    frame = FakeDataFrame(["Employee ID", "Department"])
    normalized, fields = _canonicalize_dataframe(
        frame,
        {"Employee ID": "employee_id", "Department": "department", "Missing": "salary", "Notes": "unknown"},
    )

    assert normalized.columns == ["employee_id", "department"]
    assert fields == ("department", "employee_id")


def test_spark_mapping_blocks_duplicate_canonical_targets():
    frame = FakeDataFrame(["Employee ID", "Worker ID"])
    with pytest.raises(ValueError, match="Multiple Spark source columns"):
        _canonicalize_dataframe(
            frame,
            {"Employee ID": "employee_id", "Worker ID": "employee_id"},
        )


def test_spark_mapping_blocks_collision_with_existing_canonical_column():
    frame = FakeDataFrame(["Employee ID", "employee_id"])
    with pytest.raises(ValueError, match="Spark mapping collision"):
        _canonicalize_dataframe(frame, {"Employee ID": "employee_id"})


def test_spark_numeric_contract_is_based_on_canonical_hr_field_not_inferred_dtype():
    frame = FakeDataFrame(["Annual Pay", "Employee Age"])
    normalized, fields = _canonicalize_dataframe(
        frame,
        {"Annual Pay": "salary", "Employee Age": "age"},
    )

    assert normalized.columns == ["salary", "age"]
    assert _number_columns(normalized, fields) == {"age": "age", "salary": "salary"}


class FakeBuilder:
    def __init__(self):
        self.calls = []

    def appName(self, value):
        self.calls.append(("appName", value))
        return self

    def master(self, value):
        self.calls.append(("master", value))
        return self

    def config(self, key, value):
        self.calls.append(("config", key, value))
        return self

    def getOrCreate(self):
        return self


def test_spark_session_applies_remote_driver_network_configuration(monkeypatch):
    builder = FakeBuilder()
    fake_spark_session = type("FakeSparkSession", (), {"builder": builder})
    fake_sql = type("FakeSql", (), {"SparkSession": fake_spark_session})

    monkeypatch.setitem(sys.modules, "pyspark.sql", fake_sql)
    monkeypatch.setenv("HR_ANALYTICS_SPARK_DRIVER_HOST", "host.docker.internal")
    monkeypatch.setenv("HR_ANALYTICS_SPARK_DRIVER_BIND_ADDRESS", "0.0.0.0")

    _spark_session("spark://127.0.0.1:7077")

    assert ("master", "spark://127.0.0.1:7077") in builder.calls
    assert ("config", "spark.driver.host", "host.docker.internal") in builder.calls
    assert ("config", "spark.driver.bindAddress", "0.0.0.0") in builder.calls


def test_spark_source_contains_categorical_normalization_before_grouping():
    from pathlib import Path

    source = (Path(__file__).parents[1] / "app" / "services" / "spark_analytics.py").read_text(encoding="utf-8")
    assert 'cleaned = F.trim(F.col(canonical).cast("string"))' in source
    assert 'non_missing_df.select(cleaned.alias("value"))' in source
    assert 'distinct = non_missing_df.select(cleaned.alias("value")).distinct().count()' in source
