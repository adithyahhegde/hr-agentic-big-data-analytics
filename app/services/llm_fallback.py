"""Optional local LLM fallback for unresolved canonical HR schema mappings.

The deterministic schema engine remains authoritative. This adapter is intentionally
small and fail-closed: provider failures, malformed output, unknown canonical IDs,
and invalid confidence values never replace a valid deterministic mapping.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from app.models import ColumnProfile, MappingCandidate
from app.services.schema_engine import CANONICAL_FIELDS, canonical_field_names


class LocalLLMError(RuntimeError):
    """Raised when the optional local provider cannot produce a valid response."""


class LocalLLMClient(Protocol):
    def complete(self, prompt: str) -> str: ...


@dataclass(frozen=True)
class OllamaConfig:
    endpoint: str = "http://127.0.0.1:11434/api/generate"
    model: str = "llama3.2:3b"
    timeout_seconds: float = 20.0


class OllamaClient:
    def __init__(self, config: OllamaConfig | None = None) -> None:
        self.config = config or OllamaConfig()

    def complete(self, prompt: str) -> str:
        try:
            response = httpx.post(
                self.config.endpoint,
                json={"model": self.config.model, "prompt": prompt, "stream": False},
                timeout=self.config.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
            result = payload.get("response")
            if not isinstance(result, str) or not result.strip():
                raise LocalLLMError("Local LLM returned no response")
            return result
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise LocalLLMError("Local LLM provider unavailable or invalid") from exc


def _safe_metadata(column: ColumnProfile) -> dict[str, Any]:
    """Build a bounded metadata-only representation; never send raw samples."""
    return {
        "source_name": column.source_name,
        "normalized_name": column.normalized_name,
        "inferred_type": column.inferred_type,
        "non_null_count": column.non_null_count,
        "null_count": column.null_count,
        "uniqueness_ratio": round(column.uniqueness_ratio, 4),
        "sample_value_count": len(column.sample_values),
        "numeric_stats": column.numeric_stats.model_dump() if column.numeric_stats else None,
    }


def build_prompt(column: ColumnProfile, candidate_fields: list[str]) -> str:
    """Create a bounded prompt containing metadata only."""
    metadata = _safe_metadata(column)
    return (
        "Map one HR dataset column to zero or one canonical field. "
        "Return JSON only: {\"candidates\":[{\"canonical_field\":string,\"confidence\":number,"
        "\"evidence\":[string]}]}. Include UNKNOWN when evidence is insufficient. "
        "Do not invent canonical fields. This is a schema classification task, not an HR decision.\n"
        f"Allowed canonical fields: {json.dumps(candidate_fields)}\n"
        f"Column metadata: {json.dumps(metadata, separators=(',', ':'))}"
    )


def _extract_json(text: str) -> dict[str, Any]:
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LocalLLMError("Local LLM returned malformed JSON") from exc
    if not isinstance(value, dict):
        raise LocalLLMError("Local LLM response must be a JSON object")
    return value


def validate_response(payload: dict[str, Any], allowed_fields: set[str]) -> list[dict[str, Any]]:
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise LocalLLMError("Local LLM response has no candidates")
    validated: list[dict[str, Any]] = []
    for item in candidates[:3]:
        if not isinstance(item, dict):
            continue
        field_name = item.get("canonical_field")
        confidence = item.get("confidence")
        evidence = item.get("evidence", [])
        if field_name == "unknown":
            field_name = "unknown"
        if not isinstance(field_name, str) or field_name not in allowed_fields | {"unknown"}:
            continue
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= confidence <= 1:
            continue
        if not isinstance(evidence, list) or not all(isinstance(x, str) for x in evidence[:5]):
            continue
        validated.append({"canonical_field": field_name, "confidence": float(confidence), "evidence": evidence[:5]})
    if not validated:
        raise LocalLLMError("Local LLM response contained no valid canonical candidates")
    return validated


def fallback_mapping(column: ColumnProfile, client: LocalLLMClient) -> MappingCandidate:
    """Resolve an unresolved/ambiguous column without overriding deterministic certainty."""
    prompt = build_prompt(column, sorted(canonical_field_names()))
    raw = client.complete(prompt)
    candidates = validate_response(_extract_json(raw), set(CANONICAL_FIELDS))
    top = candidates[0]
    alternatives = [c["canonical_field"] for c in candidates[1:] if c["canonical_field"] != "unknown"]
    if top["canonical_field"] == "unknown":
        return MappingCandidate(
            canonical_field="unknown", confidence=0.0, decision="UNMAPPED",
            evidence=["local_llm_no_safe_mapping"], alternatives=alternatives,
        )
    return MappingCandidate(
        canonical_field=top["canonical_field"],
        confidence=top["confidence"],
        decision="NEEDS_REVIEW",
        evidence=["local_llm_fallback", *top["evidence"]],
        alternatives=alternatives,
    )
