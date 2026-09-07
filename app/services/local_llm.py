"""Optional local Ollama evidence provider for bounded AI assistance.

The provider is deliberately isolated from deterministic scoring. It only ranks
already-generated candidates; it never invents canonical fields, values,
statistics, targets, or unsupported analytical objectives. External network
services are not used.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LLMDecision:
    canonical_field: str
    reason: str
    confidence_band: str


class LocalLLMError(RuntimeError):
    """Raised when the local provider cannot return a valid response."""


def _request_ollama(*, base_url: str, model: str, prompt: str, timeout_seconds: float) -> dict:
    payload = {
        "model": model,
        "stream": False,
        "format": "json",
        "messages": [
            {"role": "system", "content": "You are a conservative HR analytics planning assistant. Choose only from supplied candidates. Do not invent fields, values, statistics, objectives, or tools. Return JSON only."},
            {"role": "user", "content": prompt},
        ],
    }
    request = urllib.request.Request(base_url.rstrip("/") + "/api/chat", data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
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


def resolve_ambiguous_mapping(*, source_name: str, inferred_type: str, uniqueness_ratio: float, sample_values: list[str], candidates: list[str], base_url: str, model: str, timeout_seconds: float = 8.0) -> LLMDecision:
    if not candidates:
        raise LocalLLMError("No deterministic candidates were supplied.")
    prompt = json.dumps({"source_column": source_name, "inferred_type": inferred_type, "uniqueness_ratio": round(uniqueness_ratio, 4), "sample_values": sample_values[:5], "candidate_canonical_fields": candidates, "required_response": {"canonical_field": "one candidate exactly", "reason": "short evidence-based explanation", "confidence_band": "low | medium | high"}}, ensure_ascii=False)
    result = _request_ollama(base_url=base_url, model=model, prompt=prompt, timeout_seconds=timeout_seconds)
    canonical, reason, confidence_band = result.get("canonical_field"), result.get("reason"), result.get("confidence_band")
    if canonical not in candidates or not isinstance(reason, str) or not reason.strip() or confidence_band not in {"low", "medium", "high"}:
        raise LocalLLMError("Local LLM returned an invalid schema decision.")
    return LLMDecision(canonical_field=canonical, reason=reason.strip()[:500], confidence_band=confidence_band)


def plan_analytical_objectives(*, candidates: list[dict[str, Any]], base_url: str, model: str, timeout_seconds: float = 8.0) -> list[dict[str, Any]]:
    """Rank only feasible candidate objectives and return a validated plan."""
    if not candidates:
        raise LocalLLMError("No planning candidates were supplied.")
    prompt = json.dumps({
        "validated_candidates": candidates,
        "instructions": [
            "Rank the supplied feasible objectives by analytical usefulness for an HR decision-support investigation.",
            "Do not add or rename objectives.",
            "Do not change target_field or feature_fields.",
            "Return JSON with key plans containing one object per selected candidate.",
            "Each plan must contain objective, priority (HIGH|MEDIUM|LOW), reason, and steps (2-5 short strings).",
        ],
    }, ensure_ascii=False)
    result = _request_ollama(base_url=base_url, model=model, prompt=prompt, timeout_seconds=timeout_seconds)
    plans = result.get("plans")
    if not isinstance(plans, list):
        raise LocalLLMError("Local LLM omitted a valid planning list.")
    allowed = {item["objective"] for item in candidates}
    validated: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in plans:
        if not isinstance(item, dict):
            continue
        objective = item.get("objective")
        priority = item.get("priority")
        reason = item.get("reason")
        steps = item.get("steps")
        if objective not in allowed or objective in seen or priority not in {"HIGH", "MEDIUM", "LOW"} or not isinstance(reason, str) or not reason.strip() or not isinstance(steps, list):
            continue
        clean_steps = [str(step).strip()[:240] for step in steps[:5] if str(step).strip()]
        if len(clean_steps) < 2:
            continue
        validated.append({"objective": objective, "priority": priority, "reason": reason.strip()[:500], "steps": clean_steps})
        seen.add(objective)
    if not validated:
        raise LocalLLMError("Local LLM returned no valid candidate plans.")
    return validated
