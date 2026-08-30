from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    app_name: str = "HR Agentic Analytics"
    max_upload_bytes: int = 10 * 1024 * 1024
    max_profile_rows: int = 10_000
    max_columns: int = 500
    allow_local_llm: bool = False


def get_settings() -> Settings:
    return Settings(
        max_upload_bytes=int(os.getenv("HR_ANALYTICS_MAX_UPLOAD_BYTES", 10 * 1024 * 1024)),
        max_profile_rows=int(os.getenv("HR_ANALYTICS_MAX_PROFILE_ROWS", 10_000)),
        max_columns=int(os.getenv("HR_ANALYTICS_MAX_COLUMNS", 500)),
        allow_local_llm=os.getenv("HR_ANALYTICS_ALLOW_LOCAL_LLM", "false").lower() == "true",
    )
