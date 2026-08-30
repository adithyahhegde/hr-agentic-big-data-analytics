from app.services.llm_fallback import LocalLLMError, build_prompt, fallback_mapping, validate_response
from app.models import ColumnProfile


def make_column(name: str = "mystery_field") -> ColumnProfile:
    return ColumnProfile(
        source_name=name,
        normalized_name=name,
        inferred_type="categorical",
        non_null_count=3,
        null_count=0,
        unique_count=3,
        uniqueness_ratio=1.0,
        sample_values=["redacted", "redacted", "redacted"],
    )


def test_prompt_contains_metadata_but_not_raw_sample_values():
    column = make_column()
    prompt = build_prompt(column, ["department"])
    assert "mystery_field" in prompt
    assert "redacted" not in prompt
    assert "department" in prompt


def test_validate_response_rejects_unknown_field():
    try:
        validate_response({"candidates": [{"canonical_field": "not_a_real_field", "confidence": 0.9, "evidence": []}]}, {"department"})
    except LocalLLMError:
        pass
    else:
        raise AssertionError("invalid canonical field should be rejected")


def test_validate_response_rejects_invalid_confidence():
    try:
        validate_response({"candidates": [{"canonical_field": "department", "confidence": 2, "evidence": []}]}, {"department"})
    except LocalLLMError:
        pass
    else:
        raise AssertionError("invalid confidence should be rejected")


def test_fallback_never_auto_maps():
    class Client:
        def complete(self, prompt: str) -> str:
            return '{"candidates":[{"canonical_field":"department","confidence":0.99,"evidence":["semantic_match"]}]}'

    result = fallback_mapping(make_column(), Client())
    assert result.canonical_field == "department"
    assert result.decision == "NEEDS_REVIEW"
    assert result.confidence == 0.99


def test_fallback_allows_unknown():
    class Client:
        def complete(self, prompt: str) -> str:
            return '{"candidates":[{"canonical_field":"unknown","confidence":0,"evidence":[]}]}'

    result = fallback_mapping(make_column(), Client())
    assert result.canonical_field == "unknown"
    assert result.decision == "UNMAPPED"
