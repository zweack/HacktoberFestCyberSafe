"""Runtime settings, read from environment variables (and an optional .env file).

LLM credentials live outside the repo, e.g. ~/.config/cybersafe/llm.env; point
CYBERSAFE_ENV_FILE at it or export the variables before starting.
"""

import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_ENV_FILES = (
    ".env",
    str(Path.home() / ".config" / "cybersafe" / "llm.env"),
    os.environ.get("CYBERSAFE_ENV_FILE", ""),
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[f for f in _DEFAULT_ENV_FILES if f],
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # OpenAI-compatible endpoint (Jarvislabs Token Factory or a vLLM box serving Gemma)
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    llm_timeout_seconds: float = 30.0
    # Gemma 4 on Jarvislabs thinks by default; "none" answers in ~0.5s. Empty string omits the field.
    llm_reasoning_effort: str = "none"
    llm_max_tokens: int = 700

    # Temporal
    temporal_address: str = "localhost:7233"
    temporal_namespace: str = "default"
    temporal_task_queue: str = "cybersafe-followups"

    # Follow-up timing. Real deployments use hours; demos compress it.
    checkin_interval_seconds: int = 60
    max_unanswered_checkins: int = 2

    # Notifications
    telegram_bot_token: str = ""
    coordinator_telegram_chat_id: str = ""

    # Storage
    database_path: str = "data/cybersafe.db"

    # CORS for the web app dev server
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def llm_configured(self) -> bool:
        return bool(self.llm_base_url and self.llm_model)


@lru_cache
def get_settings() -> Settings:
    return Settings()
