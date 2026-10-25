"""Temporal worker for case follow-ups (+ optional Telegram long-poll). Run: python -m app.worker"""

import asyncio
import logging

from temporalio.worker import Worker

from app.config import get_settings
from app.logging_setup import setup_logging
from app.notify import telegram
from app.schemas import CheckinAnswer, CheckinResponse
from app.workflows import case_ops
from app.workflows.activities import ALL_ACTIVITIES
from app.workflows.client import get_client
from app.workflows.followup import CaseFollowUpWorkflow, workflow_id

log = logging.getLogger("app.worker")


async def handle_update(client, upd: dict) -> None:
    if cq := upd.get("callback_query"):
        parsed = telegram.parse_callback(cq.get("data", ""))
        reply = "Sorry, I did not understand that."
        if parsed:
            case_id, answer = parsed
            try:
                resp = CheckinResponse(answer=CheckinAnswer(answer), note="via Telegram")
                case_ops.record_checkin(case_id, resp)
                await client.get_workflow_handle(workflow_id(case_id)).signal(
                    CaseFollowUpWorkflow.checkin_response, resp)
                reply = {"done": "Thank you! Well done.", "not_yet": "OK. Please do it soon. We will ask again.",
                         "need_help": "A helper will contact you soon."}[answer]
            except Exception:
                log.exception("telegram callback failed", extra={"case_id": case_id})
                reply = "Something went wrong. Please call 1930."
        await telegram.call("answerCallbackQuery", {"callback_query_id": cq["id"], "text": reply})
        return
    msg = upd.get("message") or {}
    if (msg.get("text") or "").startswith("/start"):
        chat_id = msg["chat"]["id"]
        await telegram.send_message(
            str(chat_id), f"Namaste! Your Telegram chat id is {chat_id}. Give this number to your helper "
                          "so we can send you reminders here.")


async def telegram_loop(client) -> None:
    offset = 0
    log.info("telegram long-poll started")
    while True:
        try:
            body = await telegram.call("getUpdates", {"offset": offset, "timeout": 25}, timeout=35)
            for upd in body.get("result", []):
                offset = max(offset, upd["update_id"] + 1)
                try:
                    await handle_update(client, upd)
                except Exception:
                    log.exception("telegram update failed", extra={"update_id": upd.get("update_id")})
        except Exception:
            log.exception("telegram getUpdates failed; retrying in 5s")
            await asyncio.sleep(5)


async def main() -> None:
    setup_logging("worker")
    s = get_settings()
    client = await get_client()
    worker = Worker(client, task_queue=s.temporal_task_queue, workflows=[CaseFollowUpWorkflow],
                    activities=ALL_ACTIVITIES)
    log.info("worker started", extra={"task_queue": s.temporal_task_queue, "temporal": s.temporal_address})
    tasks = [asyncio.create_task(worker.run())]
    if s.telegram_bot_token:
        tasks.append(asyncio.create_task(telegram_loop(client)))
    else:
        log.info("TELEGRAM_BOT_TOKEN not set; Telegram disabled (in-app only)")
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
