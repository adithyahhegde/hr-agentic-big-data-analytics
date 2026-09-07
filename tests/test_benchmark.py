import csv
from pathlib import Path

import pytest

from scripts.benchmark import MAPPINGS, SCHEMA_SCENARIOS, make_fixture, run, run_matrix


def test_benchmark_fixture_is_reproducible(tmp_path: Path):
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    make_fixture(first, rows=25, seed=42)
    make_fixture(second, rows=25, seed=42)
    assert first.read_bytes() == second.read_bytes()


def test_benchmark_fixture_contains_only_aggregate_safe_columns(tmp_path: Path):
    path = tmp_path / "fixture.csv"
    make_fixture(path, rows=5, seed=7)
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    assert tuple(rows[0]) == tuple(MAPPINGS)
    assert len(rows) == 6
    assert rows[1][0] == "1"


def test_benchmark_run_is_reproducible_at_metadata_level():
    first = run(rows=10, seed=123)
    second = run(rows=10, seed=123)
    assert first["fixture"] == second["fixture"]
    assert first["routing"] == second["routing"]
    assert first["local"]["rows"] == second["local"]["rows"] == 10
    assert first["local"]["duplicate_rows"] == second["local"]["duplicate_rows"] == 0
    assert "spark" in first


def test_benchmark_rejects_invalid_size_and_scenario():
    with pytest.raises(ValueError, match="positive"):
        run(rows=0, seed=1)
    with pytest.raises(ValueError, match="unknown scenario"):
        run(rows=10, seed=1, scenario="unknown")


def test_benchmark_matrix_is_reproducible_and_covers_all_scenarios():
    result = run_matrix(sizes=(5, 10), seed=7)
    assert result["seed"] == 7
    assert result["sizes"] == [5, 10]
    assert result["scenarios"] == list(SCHEMA_SCENARIOS)
    assert len(result["results"]) == 2 * len(SCHEMA_SCENARIOS)
    assert all("task_detection" in item for item in result["results"])


def test_data_quality_scenarios_exercise_distinct_fixture_behaviour(tmp_path: Path):
    missing = tmp_path / "missing.csv"
    duplicate = tmp_path / "duplicate.csv"
    high_cardinality = tmp_path / "high_cardinality.csv"
    outlier = tmp_path / "outlier.csv"
    make_fixture(missing, rows=20, seed=42, scenario="missing_heavy")
    make_fixture(duplicate, rows=20, seed=42, scenario="duplicate_heavy")
    make_fixture(high_cardinality, rows=20, seed=42, scenario="high_cardinality")
    make_fixture(outlier, rows=20, seed=42, scenario="outlier_heavy")

    assert len(missing.read_text(encoding="utf-8").splitlines()) == 21
    with duplicate.open(newline="", encoding="utf-8") as handle:
        duplicate_rows = list(csv.reader(handle))[1:]
    assert len(set(tuple(row) for row in duplicate_rows)) < len(duplicate_rows)
    with high_cardinality.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))[1:]
    assert len({row[2] for row in rows}) == 20
    with outlier.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))[1:]
    assert any(row[3] == "2000000" for row in rows)


def test_data_quality_scenarios_remain_analytically_runnable():
    for scenario in ("missing_heavy", "duplicate_heavy", "high_cardinality", "outlier_heavy"):
        result = run(rows=20, seed=42, scenario=scenario)
        assert result["schema_gate"] == "ACCEPTABLE"
        assert result["local"]["rows"] == 20
        assert result["local"]["duplicate_rows"] >= 0
