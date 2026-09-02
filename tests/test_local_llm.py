from app.services.local_llm import LocalLLMError, resolve_ambiguous_mapping


def test_local_llm_accepts_only_candidate(monkeypatch):
    def fake_request(**kwargs):
        return {
            "canonical_field": "promotion_status",
            "reason": "The binary Y/N values and candidate context support promotion status.",
            "confidence_band": "medium",
        }

    monkeypatch.setattr("app.services.local_llm._request_ollama", fake_request)

    decision = resolve_ambiguous_mapping(
        source_name="prm_st",
        inferred_type="boolean",
        uniqueness_ratio=0.1,
        sample_values=["Y", "N"],
        candidates=["promotion_status", "employment_status"],
        base_url="http://localhost:11434",
        model="test-model",
    )

    assert decision.canonical_field == "promotion_status"
    assert decision.confidence_band == "medium"


def test_local_llm_rejects_out_of_set_candidate(monkeypatch):
    def fake_request(**kwargs):
        return {
            "canonical_field": "salary",
            "reason": "Unsupported choice.",
            "confidence_band": "high",
        }

    monkeypatch.setattr("app.services.local_llm._request_ollama", fake_request)

    try:
        resolve_ambiguous_mapping(
            source_name="prm_st",
            inferred_type="boolean",
            uniqueness_ratio=0.1,
            sample_values=["Y", "N"],
            candidates=["promotion_status", "employment_status"],
            base_url="http://localhost:11434",
            model="test-model",
        )
    except LocalLLMError as exc:
        assert "outside the candidate set" in str(exc)
    else:
        raise AssertionError("Expected LocalLLMError")
