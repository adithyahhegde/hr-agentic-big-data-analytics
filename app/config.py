from dataclasses import dataclass
import os
from pathlib import Path


@dataclass
class Settings:
    app_name: str = "HR Agentic Analytics"
    max_upload_bytes: int = 10 * 1024 * 1024
    max_execution_upload_bytes: int = 2 * 1024 * 1024 * 1024
    max_profile_rows: int = 10_000
    max_columns: int = 500
    allow_local_llm: bool = False
    local_llm_base_url: str = "http://localhost:11434"
    local_llm_model: str = "llama3.2:3b"
    local_llm_timeout_seconds: float = 8.0
    automl_time_budget_seconds: int = 30
    data_dir: Path = Path("data")
    api_key: str = ""
    api_keys: tuple[tuple[str, str], ...] = ()


def _parse_api_keys(raw: str) -> tuple[tuple[str, str], ...]:
    """Parse ``user=key;user2=key2`` without logging or exposing secrets."""
    entries: list[tuple[str, str]] = []
    for item in raw.split(";"):
        item = item.strip()
        if not item or "=" not in item:
            continue
        user_id, key = item.split("=", 1)
        user_id, key = user_id.strip(), key.strip()
        if user_id and key:
            entries.append((user_id, key))
    return tuple(entries)


def get_settings() -> Settings:
    return Settings(
        max_upload_bytes=int(os.getenv("HR_ANALYTICS_MAX_UPLOAD_BYTES", 10 * 1024 * 1024)),
        max_execution_upload_bytes=int(os.getenv("HR_ANALYTICS_MAX_EXECUTION_UPLOAD_BYTES", 2 * 1024 * 1024 * 1024)),
        max_profile_rows=int(os.getenv("HR_ANALYTICS_MAX_PROFILE_ROWS", 10_000)),
        max_columns=int(os.getenv("HR_ANALYTICS_MAX_COLUMNS", 500)),
        allow_local_llm=os.getenv("HR_ANALYTICS_ALLOW_LOCAL_LLM", "false").lower() == "true",
        local_llm_base_url=os.getenv("HR_ANALYTICS_LOCAL_LLM_BASE_URL", "http://localhost:11434"),
        local_llm_model=os.getenv("HR_ANALYTICS_LOCAL_LLM_MODEL", "llama3.2:3b"),
        local_llm_timeout_seconds=float(os.getenv("HR_ANALYTICS_LOCAL_LLM_TIMEOUT_SECONDS", 8.0)),
        automl_time_budget_seconds=max(1, min(600, int(os.getenv("HR_ANALYTICS_AUTOML_TIME_BUDGET_SECONDS", 30)))),
        data_dir=Path(os.getenv("HR_ANALYTICS_DATA_DIR", "data")),
        api_key=os.getenv("HR_ANALYTICS_API_KEY", ""),
        api_keys=_parse_api_keys(os.getenv("HR_ANALYTICS_API_KEYS", "")),
    )
