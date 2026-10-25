"""Cases, check-ins, notifications, coordinator queue. Owner: followup (Temporal).

Case endpoints are reachable by anyone who knows the unguessable case id (the person's
own link). Listing cases and coordinator actions need the staff token (app/auth.py).
"""

import hashlib
import logging

from fastapi import APIRouter, Depends, Header, HTTPException

from app import db
from app.auth import require_staff
from app.detector.steps import recovery_case_steps
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
from app.workflows import case_ops, outbox
from app.workflows.followup import workflow_id

router = APIRouter(tags=["cases"])
staff_router = APIRouter(tags=["coordinator"], dependencies=[Depends(require_staff)])
log = logging.getLogger(__name__)


def _load(case_id: str) -> Case:
    try:
        return case_ops.load(case_id)
    except case_ops.CaseNotFound:
        raise HTTPException(404, f"Case {case_id} not found") from None


@router.post("/cases", response_model=Case)
async def create_case(body: CaseCreate, idempotency_key: str | None = Header(default=None)) -> Case:
    """Save the case, then start its follow-up. If Temporal is down the case is still
    returned (followup_pending=true) and the worker starts the follow-up when it can.
    Send the same Idempotency-Key header on a retry to get the same case back."""
    if body.analysis and body.analysis.steps:
        steps = [CaseStep(**s.model_dump()) for s in body.analysis.steps]
    else:
        steps = recovery_case_steps(body.language)
    case = Case(**body.model_dump(exclude={"analysis"}), analysis=body.analysis, steps=steps)
    if idempotency_key:
        # Same key -> same case id; a retried POST cannot create a second case.
        case.id = "case_" + hashlib.sha256(idempotency_key.encode()).hexdigest()[:20]
    case.workflow_id = workflow_id(case.id)
    case_ops.event(case, "created", "Case opened")
    case.updated_at = case.created_at
    if not db.insert_new("cases", case):
        return case_ops.load(case.id)
    await outbox.send(case.id, outbox.START)
    return case_ops.load(case.id)


@router.get("/cases/{case_id}", response_model=Case)
def get_case(case_id: str) -> Case:
    return _load(case_id)


@router.post("/cases/{case_id}/steps/{step_id}/done", response_model=Case)
async def step_done(case_id: str, step_id: str) -> Case:
    _load(case_id)
    try:
        case_ops.mark_step_done(case_id, step_id)
    except KeyError:
        raise HTTPException(404, f"Step {step_id} not found") from None
    await outbox.send(case_id, "step_done", step_id)
    return _load(case_id)


@router.post("/cases/{case_id}/checkin", response_model=Case)
async def checkin(case_id: str, body: CheckinResponse) -> Case:
    if _load(case_id).status == CaseStatus.resolved:
        raise HTTPException(409, "Case is already resolved")
    case_ops.record_checkin(case_id, body)
    await outbox.send(case_id, "checkin_response", body)
    return _load(case_id)


@router.get("/notifications", response_model=list[Notification])
def notifications(case_id: str | None = None, x_staff_token: str | None = Header(default=None)) -> list[Notification]:
    """One case's notifications by case id; the full list needs the staff token."""
    if case_id is None:
        require_staff(x_staff_token)
    return in_app.list_for(case_id)


@staff_router.get("/cases", response_model=list[Case])
def list_cases() -> list[Case]:
    return db.list_all("cases", Case)


@staff_router.get("/coordinator/queue", response_model=list[Case])
def coordinator_queue() -> list[Case]:
    return db.list_all("cases", Case, limit=1000,
                       where={"status": [CaseStatus.escalated.value, CaseStatus.claimed.value]})


@staff_router.post("/coordinator/cases/{case_id}/claim", response_model=Case)
async def claim(case_id: str, body: CoordinatorAction) -> Case:
    _load(case_id)
    try:
        case_ops.claim(case_id, body.coordinator, body.note)
    except ValueError:
        raise HTTPException(409, "Case is already resolved") from None
    await outbox.send(case_id, "coordinator_claim", body)
    return _load(case_id)


@staff_router.post("/coordinator/cases/{case_id}/resolve", response_model=Case)
async def resolve(case_id: str, body: CoordinatorAction) -> Case:
    _load(case_id)
    case_ops.resolve(case_id, body.coordinator, body.note)
    await outbox.send(case_id, "resolve", body)
    return _load(case_id)
