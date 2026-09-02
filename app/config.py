from dataclasses import dataclass
import os


@dataclass(frozen=True)
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
    )
