"""In-app notifications are just records in the "notifications" collection."""

from app import db
from app.schemas import Notification, NotificationChannel, NotificationStatus


def save(n: Notification) -> Notification:
    db.put("notifications", n)
    return n


def notify(message: str, *, recipient: str, case_id: str | None = None, id: str | None = None) -> Notification:
    n = Notification(case_id=case_id, channel=NotificationChannel.in_app, recipient=recipient, message=message,
                     status=NotificationStatus.sent, attempts=1)
    if id:
        n.id = id
    return save(n)


def list_for(case_id: str | None = None, limit: int = 200) -> list[Notification]:
    """Newest first. The case filter runs in SQL, so old cases still see their notes."""
    return db.list_all("notifications", Notification, limit=limit, where={"case_id": [case_id]} if case_id else None)
