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
    assert result["recommendations"][0]["priority"] == "HIGH"
    assert "employee-level decision" in result["recommendations"][0]["constraint"]
    assert any("causal" in limitation.lower() for limitation in result["limitations"])


def test_empty_evidence_does_not_invent_recommendations():
    result = synthesize({"insights": []}, [])
    assert result["evidence"] == []
    assert len(result["recommendations"]) == 1
    assert result["recommendations"][0]["priority"] == "LOW"
    assert "No automated recommendation" in result["recommendations"][0]["constraint"]
