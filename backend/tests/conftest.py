import pytest

from app import db
from app.config import get_settings


@pytest.fixture(autouse=True)
def fresh_db(tmp_path):
    db.reset_for_tests(str(tmp_path / "test.db"))
    yield


@pytest.fixture(autouse=True)
def no_real_services(monkeypatch):
    """Tests never call the real LLM or Telegram, even if ~/.config/cybersafe/llm.env exists.

    Tests that exercise those paths set fake values themselves.
    """
    s = get_settings()
    for field in ("llm_base_url", "llm_api_key", "llm_model", "telegram_bot_token", "coordinator_telegram_chat_id"):
        monkeypatch.setattr(s, field, "")
