from pathlib import Path

from app.services.ml_engine import run_ml


def test_ml_explainability_uses_bounded_shap_or_safe_fallback(tmp_path: Path):
    path = tmp_path / "hr.csv"
    rows = ["age,tenure,attrition"]
    for i in range(40):
        rows.append(f"{25 + (i % 20)},{1 + (i % 10)},{'Yes' if i % 3 == 0 else 'No'}")
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")

    result = run_ml(
        path,
        {"age": "age", "tenure": "tenure", "attrition": "attrition"},
        "attrition_classification",
        "attrition",
        ["age", "tenure"],
        seed=42,
    )

    explanation = result["explainability"]
    assert explanation["method"] in {"shap_global_mean_abs", "model_importance_or_permutation"}
    assert len(explanation["top_features"]) <= 10
    assert all(set(item) == {"feature", "importance"} for item in explanation["top_features"])
    if explanation["method"] == "shap_global_mean_abs":
        assert explanation["sample_rows"] <= 100
        assert explanation["bounded"] is True
        assert "not causal explanation" in explanation["limitations"]
