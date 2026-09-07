from pathlib import Path

import pytest

from app.services.heterogeneous_ml import _safe_model_failure, run_heterogeneous_ml


def test_candidate_failure_is_sanitized():
    secret = "employee E17 salary=999999"
    result = _safe_model_failure(ValueError(secret))
    assert result == {
        "status": "FAILED",
        "error_type": "ValueError",
        "reason": "Candidate model failed during fitting or evaluation.",
        "recoverable": "true",
    }
    assert secret not in str(result)


def test_insufficient_rows_abstains_before_model_training(tmp_path: Path):
    path = tmp_path / "hr.csv"
    path.write_text("age,left_org\n25,Yes\n26,No\n", encoding="utf-8")
    with pytest.raises(ValueError, match="At least 20 usable rows"):
        run_heterogeneous_ml(
            path,
            {"age": "age", "left_org": "attrition"},
            "attrition_classification",
            "attrition",
            ["age"],
        )
