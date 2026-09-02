"""Optional local Ollama evidence provider for ambiguous schema mappings.

The provider is deliberately isolated from deterministic schema scoring. It only
helps rank already-generated candidates; it never invents canonical fields,
statistics, or source values. External network services are not used.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True)
class LLMDecision:
    canonical_field: str
    reason: str
    confidence_band: str


class LocalLLMError(RuntimeError):
    """Raised when the local provider cannot return a valid response."""


def _request_ollama(
    *,
    base_url: str,
    model: str,
    prompt: str,
    timeout_seconds: float,
) -> dict:
    payload = {
        "model": model,
        "stream": False,
        "format": "json",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a conservative HR schema interpretation assistant. "
                    "Choose only from the supplied candidate canonical fields. "
                    "Do not invent fields, values, or statistics. Return JSON only."
                ),
            },
            {"role": "user", "content": prompt},
        ],
    }
    request = urllib.request.Request(
        base_url.rstrip("/") + "/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise LocalLLMError("Local LLM provider is unavailable.") from exc

    try:
        envelope = json.loads(raw)
        content = envelope["message"]["content"]
        result = json.loads(content) if isinstance(content, str) else content
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise LocalLLMError("Local LLM returned an invalid structured response.") from exc

    if not isinstance(result, dict):
        raise LocalLLMError("Local LLM returned an invalid response object.")
    return result


def resolve_ambiguous_mapping(
    *,
    source_name: str,
    inferred_type: str,
    uniqueness_ratio: float,
    sample_values: list[str],
    candidates: list[str],
    base_url: str,
    model: str,
    timeout_seconds: float = 8.0,
) -> LLMDecision:
    """Ask Ollama to choose only among deterministic candidates."""
    if not candidates:
        raise LocalLLMError("No deterministic candidates were supplied.")

    # Samples are already bounded by the profiling contract. Keep the prompt
    # strictly structured and never include raw records beyond those samples.
    prompt = json.dumps(
        {
            "source_column": source_name,
            "inferred_type": inferred_type,
            "uniqueness_ratio": round(uniqueness_ratio, 4),
            "sample_values": sample_values[:5],
            "candidate_canonical_fields": candidates,
            "required_response": {
                "canonical_field": "one candidate exactly",
                "reason": "short evidence-based explanation",
                "confidence_band": "low | medium | high",
            },
        },
        ensure_ascii=False,
    )
    result = _request_ollama(
        base_url=base_url,
        model=model,
        prompt=prompt,
        timeout_seconds=timeout_seconds,
    )

    canonical = result.get("canonical_field")
    reason = result.get("reason")
    confidence_band = result.get("confidence_band")
    if canonical not in candidates:
        raise LocalLLMError("Local LLM selected a canonical field outside the candidate set.")
    if not isinstance(reason, str) or not reason.strip():
        raise LocalLLMError("Local LLM response omitted a valid reason.")
    if confidence_band not in {"low", "medium", "high"}:
        raise LocalLLMError("Local LLM response omitted a valid confidence band.")

    return LLMDecision(
        canonical_field=canonical,
        reason=reason.strip()[:500],
        confidence_band=confidence_band,
    )
