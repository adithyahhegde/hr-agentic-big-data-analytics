from pathlib import Path

import pytest

from app.services.automl_engine import run_automl


def test_automl_rejects_invalid_budget_before_optional_dependency(tmp_path: Path):
    path = tmp_path / "hr.csv"
    path.write_text("age,attrition\n30,No\n31,Yes\n", encoding="utf-8")
    with pytest.raises(ValueError, match="time_budget"):
        run_automl(
            path,
            {"age": "age", "attrition": "attrition"},
            "attrition_classification",
            "attrition",
            ["age"],
            time_budget=0,
        )


def test_automl_rejects_missing_target_before_optional_dependency(tmp_path: Path):
    path = tmp_path / "hr.csv"
    path.write_text("age,attrition\n30,No\n31,Yes\n", encoding="utf-8")
    with pytest.raises(ValueError, match="not mapped"):
        run_automl(
            path,
            {"age": "age"},
            "attrition_classification",
            "attrition",
            ["age"],
        )
