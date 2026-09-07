from app.services.insight_agent import synthesize


def test_synthesis_is_evidence_bound_and_non_decision_making():
    result = synthesize(
        {
            "insights": [
                {
                    "type": "DATA_QUALITY",
                    "severity": "WARNING",
                    "title": "High missingness in salary",
                    "evidence": "20 of 100 rows are missing salary.",
                }
            ]
        },
        [],
    )
    assert result["raw_hr_records_accessed"] is False
    assert result["evidence"][0]["source"] == "descriptive_analytics"
    assert result["evidence"][0]["evidence_id"] == "evidence-1"
    assert result["recommendations"][0]["priority"] == "HIGH"
    assert result["recommendations"][0]["evidence_ids"] == ["evidence-1"]
    assert "employee-level decision" in result["recommendations"][0]["constraint"]
    assert any("causal" in limitation.lower() for limitation in result["limitations"])


def test_empty_evidence_does_not_invent_recommendations():
    result = synthesize({"insights": []}, [])
    assert result["evidence"] == []
    assert len(result["recommendations"]) == 1
    assert result["recommendations"][0]["priority"] == "LOW"
    assert result["recommendations"][0]["evidence_ids"] == []
    assert "No automated recommendation" in result["recommendations"][0]["constraint"]


def test_synthesis_rejects_unknown_or_cross_dataset_runs():
    result = synthesize(
        {"dataset_fingerprint": "current", "insights": []},
        [
            {"objective": "unsupported_future_task", "dataset_fingerprint": "current", "selected_model": "model-a"},
            {"objective": "attrition_classification", "dataset_fingerprint": "stale", "selected_model": "model-b"},
        ],
    )
    assert result["evidence"] == []
    assert len(result["recommendations"]) == 1
    assert "2 analytical run(s) were excluded" in result["limitations"][-1]


def test_synthesis_rejects_invalid_anomaly_share():
    result = synthesize(
        {"dataset_fingerprint": "current", "insights": []},
        [{"objective": "anomaly_detection", "dataset_fingerprint": "current", "anomaly_share": 1.5}],
    )
    assert result["evidence"] == []
    assert "1 analytical run(s) were excluded" in result["limitations"][-1]


def test_synthesis_bounds_and_truncates_descriptive_evidence():
    insights = [
        {"type": "SYSTEM", "severity": "INFO", "title": f"title-{i}", "evidence": "x" * 1000}
        for i in range(75)
    ]
    result = synthesize({"insights": insights}, [])
    assert len(result["evidence"]) == 50
    assert len(result["evidence"][0]["evidence"]) == 500
    assert result["evidence"][-1]["evidence_id"] == "evidence-50"
