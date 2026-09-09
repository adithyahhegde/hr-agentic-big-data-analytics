from __future__ import annotations

import pytest

from app.services.spark_analytics import _canonicalize_dataframe


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
