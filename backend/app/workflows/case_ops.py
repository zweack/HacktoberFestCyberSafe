"""DB updates for cases, shared by the API, activities and the Telegram poller."""

from collections.abc import Callable

from app import db
from app.schemas import Case, CaseStatus, CheckinAnswer, CheckinResponse, TimelineEvent, utcnow


class CaseNotFound(LookupError):
    pass


def load(case_id: str) -> Case:
    case = db.get("cases", case_id, Case)
    if case is None:
        raise CaseNotFound(case_id)
    return case


def save(case: Case) -> Case:
    case.updated_at = utcnow()
    db.put("cases", case)
    if case.status in (CaseStatus.escalated, CaseStatus.claimed):
        db.put("coordinator_queue", case)
    else:
        db.delete("coordinator_queue", case.id)
    return case


def mutate(case_id: str, fn: Callable[[Case], None]) -> Case:
    case = load(case_id)
    fn(case)
    return save(case)


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


def record_checkin(case_id: str, resp: CheckinResponse) -> Case:
    def fn(case: Case) -> None:
        case.unanswered_checkins = 0
        msg = f"Answered: {resp.answer.value}" + (f" ({resp.note})" if resp.note else "")
        event(case, "checkin_answered", msg)
        if resp.answer == CheckinAnswer.need_help and case.status not in (CaseStatus.claimed, CaseStatus.resolved):
            case.status = CaseStatus.escalated

    return mutate(case_id, fn)


def claim(case_id: str, coordinator: str, note: str | None) -> Case:
    def fn(case: Case) -> None:
        case.status, case.coordinator = CaseStatus.claimed, coordinator
        event(case, "claimed", f"{coordinator} is handling this case" + (f": {note}" if note else ""))

    return mutate(case_id, fn)


def resolve(case_id: str, by: str, note: str | None) -> Case:
    def fn(case: Case) -> None:
        if case.status != CaseStatus.resolved:
            case.status = CaseStatus.resolved
            event(case, "resolved", f"Resolved by {by}" + (f": {note}" if note else ""))

    return mutate(case_id, fn)
