from app.services.report_export import build_report, to_html


def test_report_contract_is_aggregate_only():
    report = build_report(
        "ds-1",
        "c" * 64,
        "2.0.0",
        {"row_count": 10, "insights": []},
        [],
        {"evidence": [], "recommendations": []},
    )
    assert report["privacy"]["raw_records_included"] is False
    assert report["privacy"]["employee_level_identifiers_included"] is False
    html = to_html(report)
    assert "HR Analytics Report" in html
    assert "ds-1" in html
