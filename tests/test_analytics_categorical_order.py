from pathlib import Path

from app.services.analytics import analyze_csv


def test_categorical_top_values_break_equal_counts_by_value(tmp_path: Path) -> None:
    dataset = tmp_path / "hr.csv"
    dataset.write_text(
        "department\n"
        "zeta\n"
        "alpha\n"
        "zeta\n"
        "alpha\n"
        "beta\n",
        encoding="utf-8",
    )

    result = analyze_csv(dataset, {"department": "department"}, max_categories=3)
    top_values = result["categorical_summary"][0]["top_values"]

    assert [item["value"] for item in top_values] == ["alpha", "zeta", "beta"]
    assert [item["count"] for item in top_values] == [2, 2, 1]
