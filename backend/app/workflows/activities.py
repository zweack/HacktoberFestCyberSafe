"""Temporal activities: all I/O for the follow-up workflow lives here."""

import logging

from pydantic import BaseModel
from temporalio import activity

from app import db, metrics
from app.config import get_settings
from app.logging_setup import redact
from app.notify import in_app, telegram
from app.schemas import CaseStatus, Notification, NotificationChannel, NotificationStatus, utcnow
from app.workflows import case_ops, messages

log = logging.getLogger(__name__)


class SendNotificationInput(BaseModel):
    notification_id: str
    case_id: str | None
    channel: NotificationChannel
    recipient: str  # person name / "coordinator" for in_app, chat id for telegram
    message: str
    checkin: bool = False  # attach the Done / Not yet / Need help buttons


class UpdateCaseInput(BaseModel):
    case_id: str
    op_id: str | None = None  # idempotency key: a retried activity applies its change once
    status: CaseStatus | None = None
    checkins_sent: int | None = None  # absolute value from the workflow, never an increment
    unanswered_checkins: int | None = None
    mark_all_steps_done: bool = False
    event_kind: str | None = None
    event_message: str | None = None


class EscalateInput(BaseModel):
    case_id: str
    reason: str
    op_id: str | None = None


class EscalateResult(BaseModel):
    coordinator_chat_id: str | None = None
    trusted_contact_chat_id: str | None = None
    trusted_contact_message: str | None = None
    coordinator_message: str


@activity.defn
async def send_notification(inp: SendNotificationInput) -> str:
    """Create/update the Notification record; raise on failure so Temporal retries."""
    n = db.get("notifications", inp.notification_id, Notification) or Notification(
        id=inp.notification_id,
        case_id=inp.case_id,
        channel=inp.channel,
        recipient=inp.recipient,
        message=inp.message,
    )
    if n.status == NotificationStatus.sent:
        return n.status.value  # a retry after a lost completion: do not send twice
    n.attempts += 1
    try:
        if inp.channel == NotificationChannel.telegram:
            if not get_settings().telegram_bot_token:
                return "skipped"  # Telegram not configured: in-app only, not an error
            await telegram.send_message(inp.recipient, inp.message, case_id=inp.case_id, checkin=inp.checkin)
    except Exception as e:
        n.status, n.last_error = NotificationStatus.failed, redact(str(e))
        in_app.save(n)
        metrics.inc("cybersafe_notifications_total", channel=inp.channel.value, status="failed")
        log.warning("notification failed", extra={"case_id": inp.case_id, "attempt": n.attempts, "error": redact(str(e))})
        raise
    n.status = NotificationStatus.sent
    in_app.save(n)
    metrics.inc("cybersafe_notifications_total", channel=inp.channel.value, status="sent")
    return n.status.value


@activity.defn
async def update_case(inp: UpdateCaseInput) -> None:
    def fn(case):
        if inp.status is not None and not case_ops.set_status(case, inp.status) and inp.status == CaseStatus.resolved:
            return  # already resolved (e.g. by the coordinator API); no duplicate event
        if inp.checkins_sent is not None:
            case.checkins_sent = max(case.checkins_sent, inp.checkins_sent)
        if inp.unanswered_checkins is not None:
            case.unanswered_checkins = inp.unanswered_checkins
        if inp.mark_all_steps_done:
            for st in case.steps:
                if not st.done:
                    st.done, st.done_at = True, utcnow()
        if inp.event_kind:
            case_ops.event(case, inp.event_kind, inp.event_message or inp.event_kind)

    case_ops.mutate(inp.case_id, fn, once=inp.op_id)


@activity.defn
async def escalate_to_coordinator(inp: EscalateInput) -> EscalateResult:
    """Mark escalated, enqueue for coordinators, notify in-app. Returns Telegram targets for the workflow."""

    applied = []

    def fn(case):
        case_ops.set_status(case, CaseStatus.escalated)
        case_ops.event(case, "escalated", f"Sent to a human coordinator: {inp.reason}")
        applied.append(True)

    case = case_ops.mutate(inp.case_id, fn, once=inp.op_id)
    if applied:
        metrics.inc("cybersafe_escalations_total")
    # Stable ids from op_id: a retry rewrites the same in-app records instead of adding more.
    key = (inp.op_id or "").replace("-", "")[:12] or None
    alert = messages.coordinator_alert(case.id, case.person_name, inp.reason)
    in_app.notify(alert, recipient="coordinator", case_id=case.id, id=key and f"ntf_c{key}")
    in_app.notify(messages.escalated_to_person(case.person_name, case.language.value),
                  recipient=case.person_name, case_id=case.id, id=key and f"ntf_p{key}")
    res = EscalateResult(coordinator_message=alert,
                         coordinator_chat_id=get_settings().coordinator_telegram_chat_id or None)
    if case.trusted_contact_name or case.trusted_contact_telegram_chat_id:
        tmsg = messages.trusted_contact_alert(case.trusted_contact_name or "friend", case.person_name)
        in_app.notify(tmsg, recipient=case.trusted_contact_name or "trusted contact", case_id=case.id,
                      id=key and f"ntf_t{key}")
        res.trusted_contact_chat_id = case.trusted_contact_telegram_chat_id
        res.trusted_contact_message = tmsg
    return res


ALL_ACTIVITIES = [send_notification, update_case, escalate_to_coordinator]
