"""Cases, check-ins, notifications, coordinator queue. Owner: followup (Temporal)."""

import logging

from fastapi import APIRouter, HTTPException

from app import db
from app.config import get_settings
from app.notify import in_app
from app.schemas import (
    Case,
    CaseCreate,
    CaseStatus,
    CaseStep,
    CheckinResponse,
    CoordinatorAction,
    Notification,
)
from app.workflows import case_ops, client as temporal
from app.workflows.followup import CaseFollowUpWorkflow, FollowUpInput, workflow_id
from app.workflows.messages import default_steps

router = APIRouter(tags=["cases"])
log = logging.getLogger(__name__)


def _load(case_id: str) -> Case:
    try:
        return case_ops.load(case_id)
    except case_ops.CaseNotFound:
        raise HTTPException(404, f"Case {case_id} not found")


async def _signal(case_id: str, signal, arg) -> None:
    """Best effort: the DB is already updated; a lost signal is logged and shown in the timeline."""
    try:
        client = await temporal.get_client()
        await client.get_workflow_handle(workflow_id(case_id)).signal(signal, arg)
    except Exception as e:
        log.warning("signal failed", extra={"case_id": case_id, "error": str(e)})
        case_ops.mutate(case_id, lambda c: case_ops.event(c, "error", f"Could not reach follow-up service: {e}"))


@router.post("/cases", response_model=Case)
async def create_case(body: CaseCreate) -> Case:
    if body.analysis and body.analysis.steps:
        steps = [CaseStep(**s.model_dump()) for s in body.analysis.steps]
    else:
        steps = default_steps(body.language)
    case = Case(**body.model_dump(exclude={"analysis"}), analysis=body.analysis, steps=steps)
    case.workflow_id = workflow_id(case.id)
    case_ops.event(case, "created", "Case opened")
    case_ops.save(case)
    s = get_settings()
    try:
        client = await temporal.get_client()
        await client.start_workflow(
            CaseFollowUpWorkflow.run,
            FollowUpInput(case_id=case.id, person_name=case.person_name, language=case.language.value,
                          step_ids=[st.id for st in steps], step_titles=[st.title for st in steps],
                          telegram_chat_id=case.telegram_chat_id,
                          checkin_interval_seconds=s.checkin_interval_seconds,
                          max_unanswered_checkins=s.max_unanswered_checkins),
            id=case.workflow_id,
            task_queue=s.temporal_task_queue,
        )
    except Exception as e:
        temporal.reset_client()
        msg = f"Case saved, but follow-up could not start (Temporal at {s.temporal_address} unreachable: {e!r})"
        log.error("workflow start failed", extra={"case_id": case.id, "error": repr(e)})
        case_ops.mutate(case.id, lambda c: case_ops.event(c, "error", msg))
        raise HTTPException(503, detail={"message": msg, "case_id": case.id})
    return case_ops.load(case.id)


@router.get("/cases", response_model=list[Case])
def list_cases() -> list[Case]:
    return db.list_all("cases", Case)


@router.get("/cases/{case_id}", response_model=Case)
def get_case(case_id: str) -> Case:
    return _load(case_id)


@router.post("/cases/{case_id}/steps/{step_id}/done", response_model=Case)
async def step_done(case_id: str, step_id: str) -> Case:
    _load(case_id)
    try:
        case_ops.mark_step_done(case_id, step_id)
    except KeyError:
        raise HTTPException(404, f"Step {step_id} not found")
    await _signal(case_id, CaseFollowUpWorkflow.step_done, step_id)
    return _load(case_id)


@router.post("/cases/{case_id}/checkin", response_model=Case)
async def checkin(case_id: str, body: CheckinResponse) -> Case:
    _load(case_id)
    case_ops.record_checkin(case_id, body)
    await _signal(case_id, CaseFollowUpWorkflow.checkin_response, body)
    return _load(case_id)


@router.get("/notifications", response_model=list[Notification])
def notifications(case_id: str | None = None) -> list[Notification]:
    return in_app.list_for(case_id)


@router.get("/coordinator/queue", response_model=list[Case])
def coordinator_queue() -> list[Case]:
    return [c for c in db.list_all("cases", Case, limit=1000)
            if c.status in (CaseStatus.escalated, CaseStatus.claimed)]


@router.post("/coordinator/cases/{case_id}/claim", response_model=Case)
async def claim(case_id: str, body: CoordinatorAction) -> Case:
    if _load(case_id).status == CaseStatus.resolved:
        raise HTTPException(409, "Case is already resolved")
    case_ops.claim(case_id, body.coordinator, body.note)
    await _signal(case_id, CaseFollowUpWorkflow.coordinator_claim, body)
    return _load(case_id)


@router.post("/coordinator/cases/{case_id}/resolve", response_model=Case)
async def resolve(case_id: str, body: CoordinatorAction) -> Case:
    _load(case_id)
    case_ops.resolve(case_id, body.coordinator, body.note)
    await _signal(case_id, CaseFollowUpWorkflow.resolve, body)
    return _load(case_id)
