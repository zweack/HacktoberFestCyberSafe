"""DB updates for cases, shared by the API, activities and the Telegram poller.

Every change goes through mutate(), which is one SQLite transaction, so the API and the
worker process cannot overwrite each other's updates.
"""

from collections.abc import Callable

from app import db
from app.schemas import Case, CaseStatus, CheckinAnswer, CheckinResponse, TimelineEvent, utcnow

# Statuses a human coordinator owns; automation must not move a case out of them
# (only resolve may).
HUMAN_OWNED = (CaseStatus.escalated, CaseStatus.claimed)


class CaseNotFound(LookupError):
    pass


def load(case_id: str) -> Case:
    case = db.get("cases", case_id, Case)
    if case is None:
        raise CaseNotFound(case_id)
    return case


def save(case: Case) -> Case:
    """Insert or overwrite. Use only for new cases; changes go through mutate()."""
    case.updated_at = utcnow()
    db.put("cases", case)
    return case


def mutate(case_id: str, fn: Callable[[Case], None], *, once: str | None = None) -> Case:
    def apply(case: Case) -> None:
        fn(case)
        case.updated_at = utcnow()

    case = db.update("cases", case_id, Case, apply, once=once)
    if case is None:
        raise CaseNotFound(case_id)
    return case


def set_status(case: Case, status: CaseStatus) -> bool:
    """Apply a legal status change. Returns False (and changes nothing) if it is not allowed.

    resolved is final. checking_in only follows open, so a claim or escalation that arrives
    while the first message is being sent is never undone by the workflow catching up.
    """
    if case.status == CaseStatus.resolved or case.status == status:
        return False
    if status == CaseStatus.checking_in and case.status != CaseStatus.open:
        return False
    if status == CaseStatus.escalated and case.status == CaseStatus.claimed:
        return False
    case.status = status
    return True


def event(case: Case, kind: str, message: str) -> None:
    case.timeline.append(TimelineEvent(kind=kind, message=message))


def mark_step_done(case_id: str, step_id: str) -> Case:
    def fn(case: Case) -> None:
        for s in case.steps:
            if s.id == step_id and not s.done:
                s.done, s.done_at = True, utcnow()
                event(case, "step_done", f"Done: {s.title}")
                return
        if not any(s.id == step_id for s in case.steps):
            raise KeyError(step_id)

    return mutate(case_id, fn)


def record_checkin(case_id: str, resp: CheckinResponse, *, once: str | None = None) -> Case:
    def fn(case: Case) -> None:
        case.unanswered_checkins = 0
        msg = f"Answered: {resp.answer.value}" + (f" ({resp.note})" if resp.note else "")
        event(case, "checkin_answered", msg)
        if resp.answer == CheckinAnswer.need_help:
            set_status(case, CaseStatus.escalated)

    return mutate(case_id, fn, once=once)


def claim(case_id: str, coordinator: str, note: str | None) -> Case:
    def fn(case: Case) -> None:
        if case.status == CaseStatus.resolved:
            raise ValueError("resolved")
        case.status, case.coordinator = CaseStatus.claimed, coordinator
        event(case, "claimed", f"{coordinator} is handling this case" + (f": {note}" if note else ""))

    return mutate(case_id, fn)


def resolve(case_id: str, by: str, note: str | None) -> Case:
    def fn(case: Case) -> None:
        if set_status(case, CaseStatus.resolved):
            event(case, "resolved", f"Resolved by {by}" + (f": {note}" if note else ""))

    return mutate(case_id, fn)
