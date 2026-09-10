from __future__ import annotations

import csv


def test_local_analytics_emits_one_categorical_summary_per_mapped_field(tmp_path):
    from app.services.analytics import analyze_csv

    path = tmp_path / "employees.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Employee ID", "Department", "Attrition"])
        writer.writerow([1, "Engineering", "Yes"])
        writer.writerow([2, "Sales", "No"])
        writer.writerow([3, "Engineering", "No"])

    result = analyze_csv(
        path,
        {
            "Employee ID": "employee_id",
            "Department": "department",
            "Attrition": "attrition",
        },
    )

    summaries = result["categorical_summary"]
    assert [item["field"] for item in summaries] == ["attrition", "department"]
    assert sum(item["field"] == "attrition" for item in summaries) == 1
    assert next(item for item in summaries if item["field"] == "attrition")["count"] == 3
