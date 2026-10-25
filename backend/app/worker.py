"""Temporal worker for case follow-ups (+ optional Telegram long-poll). Run: python -m app.worker"""

import asyncio
import logging

from temporalio.worker import Worker

from app.config import get_settings
from app.logging_setup import setup_logging
from app.notify import telegram
from app.schemas import CaseStatus, CheckinAnswer, CheckinResponse
from app.workflows import case_ops, outbox
from app.workflows.activities import ALL_ACTIVITIES
from app.workflows.client import get_client
from app.workflows.followup import CaseFollowUpWorkflow

log = logging.getLogger("app.worker")

OUTBOX_INTERVAL_SECONDS = 5
MAX_UPDATE_ATTEMPTS = 5

REPLIES = {"done": "Thank you! Well done.", "not_yet": "OK. Please do it soon. We will ask again.",
           "need_help": "Your request is in the helpers' queue. Please also call 1930 now."}


def _sender_matches(cq: dict, case) -> bool:
    """The button must be pressed by the person the case is bound to, in their own chat."""
    expected = (case.telegram_chat_id or "").strip()
    sender = str((cq.get("from") or {}).get("id", ""))
    chat = str(((cq.get("message") or {}).get("chat") or {}).get("id", ""))
    return bool(expected) and sender == expected and chat == expected


async def handle_update(upd: dict) -> None:
    """Handle one Telegram update. Raises on a temporary failure so the poller retries it.

    Safe to repeat: the check-in is recorded once per update_id, and the workflow signal
    goes through the outbox (queued and retried if Temporal is down)."""
    if cq := upd.get("callback_query"):
        parsed = telegram.parse_callback(cq.get("data", ""))
        reply = "Sorry, I did not understand that."
        if parsed:
            case_id, answer = parsed
            try:
                case = case_ops.load(case_id)
            except case_ops.CaseNotFound:
                case = None
            if case is None or not _sender_matches(cq, case):
                log.warning("telegram callback rejected", extra={"case_id": case_id, "reason": "sender mismatch"})
                reply = "This button is not for you."
            elif case.status == CaseStatus.resolved:
                reply = "This case is already closed. Thank you."
            else:
                resp = CheckinResponse(answer=CheckinAnswer(answer), note="via Telegram")
                case_ops.record_checkin(case_id, resp, once=f"tg:{upd.get('update_id')}")
                await outbox.send(case_id, "checkin_response", resp)
                reply = REPLIES[answer]
        try:
            await telegram.call("answerCallbackQuery", {"callback_query_id": cq["id"], "text": reply})
        except telegram.TelegramError:
            log.warning("answerCallbackQuery failed", extra={"update_id": upd.get("update_id")})
        return
    msg = upd.get("message") or {}
    if (msg.get("text") or "").startswith("/start"):
        chat_id = msg["chat"]["id"]
        await telegram.send_message(
            str(chat_id), f"Namaste! Your Telegram chat id is {chat_id}. Give this number to your helper "
                          "so we can send you reminders here.")


async def telegram_loop() -> None:
    """Long-poll. The offset only moves past an update once it was handled (or failed
    MAX_UPDATE_ATTEMPTS times), so a temporary failure does not lose the person's answer."""
    offset = 0
    failures: dict[int, int] = {}
    log.info("telegram long-poll started")
    while True:
        try:
            body = await telegram.call("getUpdates", {"offset": offset, "timeout": 25}, timeout=35)
        except Exception:  # noqa: BLE001
            log.exception("telegram getUpdates failed; retrying in 5s")
            await asyncio.sleep(5)
            continue
        for upd in body.get("result", []):
            uid = upd["update_id"]
            try:
                await handle_update(upd)
            except Exception:  # noqa: BLE001
                failures[uid] = failures.get(uid, 0) + 1
                log.exception("telegram update failed", extra={"update_id": uid, "attempt": failures[uid]})
                if failures[uid] < MAX_UPDATE_ATTEMPTS:
                    await asyncio.sleep(2)
                    break  # do not acknowledge; getUpdates returns it again
                log.error("telegram update dropped after retries", extra={"update_id": uid})
            failures.pop(uid, None)
            offset = max(offset, uid + 1)


async def outbox_loop(client) -> None:
    """Retry workflow starts/signals the API could not deliver (Temporal was down)."""
    try:
        queued = await outbox.reconcile_orphans(client)
        if queued:
            log.warning("queued follow-up start for orphaned cases", extra={"cases": queued})
    except Exception:  # noqa: BLE001
        log.exception("orphan reconcile failed")
    while True:
        try:
            await outbox.deliver(client)
        except Exception:  # noqa: BLE001
            log.exception("outbox delivery failed")
        await asyncio.sleep(OUTBOX_INTERVAL_SECONDS)


async def main() -> None:
    setup_logging("worker")
    s = get_settings()
    client = await get_client()
    worker = Worker(client, task_queue=s.temporal_task_queue, workflows=[CaseFollowUpWorkflow],
                    activities=ALL_ACTIVITIES)
    log.info("worker started", extra={"task_queue": s.temporal_task_queue, "temporal": s.temporal_address})
    tasks = [asyncio.create_task(worker.run()), asyncio.create_task(outbox_loop(client))]
    if s.telegram_bot_token:
        tasks.append(asyncio.create_task(telegram_loop()))
    else:
        log.info("TELEGRAM_BOT_TOKEN not set; Telegram disabled (in-app only)")
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
