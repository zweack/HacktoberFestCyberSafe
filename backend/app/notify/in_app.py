"""In-app notifications are just records in the "notifications" collection."""

from app import db
from app.schemas import Notification, NotificationChannel, NotificationStatus


def save(n: Notification) -> Notification:
    db.put("notifications", n)
    return n


def notify(message: str, *, recipient: str, case_id: str | None = None) -> Notification:
    return save(
        Notification(
            case_id=case_id,
            channel=NotificationChannel.in_app,
            recipient=recipient,
            message=message,
            status=NotificationStatus.sent,
            attempts=1,
        )
    )


def list_for(case_id: str | None = None, limit: int = 200) -> list[Notification]:
    items = db.list_all("notifications", Notification, limit=1000 if case_id else limit)
    if case_id:
        items = [n for n in items if n.case_id == case_id][:limit]
    return items
