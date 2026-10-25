"""Telegram Bot API client (sendMessage, answerCallbackQuery, getUpdates).

No token or no chat id means Telegram is skipped, not an error.
Chaos: get_chaos().telegram_failure_rate makes sends fail at random.
"""

import hashlib
import hmac
import random

import httpx

from app.chaos import get_chaos
from app.config import get_settings

API = "https://api.telegram.org/bot{token}/{method}"

CHECKIN_BUTTONS = (("✅ Done", "done"), ("⏳ Not yet", "not_yet"), ("🆘 Need help", "need_help"))


class TelegramError(RuntimeError):
    pass


def enabled(chat_id: str | None) -> bool:
    return bool(get_settings().telegram_bot_token and chat_id)


def _sign(case_id: str, answer: str) -> str:
    """Short HMAC so a forged callback payload cannot pick an arbitrary case or answer."""
    key = hashlib.sha256(b"cybersafe-callback:" + get_settings().telegram_bot_token.encode()).digest()
    return hmac.new(key, f"{case_id}:{answer}".encode(), hashlib.sha256).hexdigest()[:16]


def checkin_keyboard(case_id: str) -> dict:
    # callback_data is limited to 64 bytes: "ci:" + case id (17) + answer (<=9) + 16-char signature fits.
    return {
        "inline_keyboard": [
            [{"text": label, "callback_data": f"ci:{case_id}:{answer}:{_sign(case_id, answer)}"}
             for label, answer in CHECKIN_BUTTONS]
        ]
    }


def parse_callback(data: str) -> tuple[str, str] | None:
    """(case_id, answer) for a correctly signed check-in button, else None."""
    parts = (data or "").split(":")
    if (len(parts) == 4 and parts[0] == "ci" and parts[2] in {a for _, a in CHECKIN_BUTTONS}
            and hmac.compare_digest(parts[3], _sign(parts[1], parts[2]))):
        return parts[1], parts[2]
    return None


async def call(method: str, payload: dict, timeout: float = 15.0) -> dict:
    token = get_settings().telegram_bot_token
    if not token:
        raise TelegramError("TELEGRAM_BOT_TOKEN is not set")
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(API.format(token=token, method=method), json=payload)
    body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
    if resp.status_code != 200 or not body.get("ok"):
        raise TelegramError(f"telegram {method} failed: {resp.status_code} {body.get('description', resp.text[:200])}")
    return body


async def send_message(chat_id: str, text: str, *, case_id: str | None = None, checkin: bool = False) -> None:
    rate = get_chaos().telegram_failure_rate
    if rate > 0 and random.random() < rate:
        raise TelegramError(f"chaos: simulated Telegram failure (rate={rate})")
    payload: dict = {"chat_id": chat_id, "text": text}
    if checkin and case_id:
        payload["reply_markup"] = checkin_keyboard(case_id)
    await call("sendMessage", payload)
