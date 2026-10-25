"""Durable delivery of workflow starts and signals (A transactional-outbox, kept small).

The API writes the case change first. If Temporal cannot be reached, the command is kept
in the "outbox" collection and the case is marked followup_pending. The worker drains the
outbox every few seconds; commands for one case are delivered in order. Delivery is
at-least-once: the signal handlers are written to tolerate a repeated command.
"""

import logging

from pydantic import BaseModel, Field
from temporalio.client import Client, WorkflowExecutionStatus
from temporalio.exceptions import WorkflowAlreadyStartedError
from temporalio.service import RPCError, RPCStatusCode

from app import db
from app.config import get_settings
from app.schemas import Case, CaseStatus, CheckinResponse, CoordinatorAction, new_id, utcnow
from app.workflows import case_ops
from app.workflows.followup import CaseFollowUpWorkflow, FollowUpInput, workflow_id

log = logging.getLogger(__name__)

_COLLECTION = "outbox"
START = "start"
SIGNALS = {
    "step_done": (CaseFollowUpWorkflow.step_done, None),
    "checkin_response": (CaseFollowUpWorkflow.checkin_response, CheckinResponse),
    "coordinator_claim": (CaseFollowUpWorkflow.coordinator_claim, CoordinatorAction),
    "resolve": (CaseFollowUpWorkflow.resolve, CoordinatorAction),
}


class OutboxItem(BaseModel):
    id: str = Field(default_factory=lambda: new_id("cmd"))
    created_at: str = Field(default_factory=lambda: utcnow().isoformat())
    case_id: str
    command: str  # "start" or a key of SIGNALS
    arg: dict | str | None = None
    attempts: int = 0
    last_error: str | None = None


def followup_input(case: Case) -> FollowUpInput:
    s = get_settings()
    return FollowUpInput(case_id=case.id, person_name=case.person_name, language=case.language.value,
                         step_ids=[st.id for st in case.steps], step_titles=[st.title for st in case.steps],
                         telegram_chat_id=case.telegram_chat_id,
                         checkin_interval_seconds=s.checkin_interval_seconds,
                         max_unanswered_checkins=s.max_unanswered_checkins)


def pending_for(case_id: str) -> list[OutboxItem]:
    return [i for i in db.list_all(_COLLECTION, OutboxItem, limit=10_000, oldest_first=True) if i.case_id == case_id]


async def _deliver(client: Client, item: OutboxItem) -> None:
    if item.command == START:
        case = case_ops.load(item.case_id)
        try:
            await client.start_workflow(CaseFollowUpWorkflow.run, followup_input(case), id=workflow_id(case.id),
                                        task_queue=get_settings().temporal_task_queue)
        except WorkflowAlreadyStartedError:
            pass  # an earlier, ambiguous attempt did start it
        return
    signal, model = SIGNALS[item.command]
    arg = model.model_validate(item.arg) if model else item.arg
    await client.get_workflow_handle(workflow_id(item.case_id)).signal(signal, arg)


def enqueue(case_id: str, command: str, arg: BaseModel | str | None = None, error: str | None = None) -> OutboxItem:
    item = OutboxItem(case_id=case_id, command=command,
                      arg=arg.model_dump(mode="json") if isinstance(arg, BaseModel) else arg, last_error=error)
    db.put(_COLLECTION, item)

    def mark(c: Case) -> None:
        c.followup_pending = True
        if error:
            case_ops.event(c, "error", "Could not reach the follow-up service. We will retry automatically.")

    case_ops.mutate(case_id, mark)
    return item


async def deliver(client: Client, case_id: str | None = None) -> int:
    """Deliver queued commands in order (one case, or all). Returns how many were delivered.

    A failure stops delivery for that case so later commands never overtake earlier ones.
    """
    items = db.list_all(_COLLECTION, OutboxItem, limit=10_000, oldest_first=True)
    blocked: set[str] = set()
    done = 0
    touched: set[str] = set()
    for item in items:
        if (case_id and item.case_id != case_id) or item.case_id in blocked:
            continue
        try:
            await _deliver(client, item)
        except case_ops.CaseNotFound:
            db.delete(_COLLECTION, item.id)
            continue
        except Exception as e:  # noqa: BLE001 - any failure: keep it queued and retry later
            blocked.add(item.case_id)
            item.attempts += 1
            item.last_error = repr(e)[:300]
            db.put(_COLLECTION, item)
            continue
        db.delete(_COLLECTION, item.id)
        touched.add(item.case_id)
        done += 1
    for cid in touched - blocked:
        if not pending_for(cid):
            try:
                case_ops.mutate(cid, lambda c: setattr(c, "followup_pending", False))
            except case_ops.CaseNotFound:
                pass
    if done:
        log.info("outbox delivered", extra={"delivered": done, "still_blocked": len(blocked)})
    return done


async def send(case_id: str, command: str, arg: BaseModel | str | None = None) -> None:
    """Deliver now if possible, else queue it. Never raises for a Temporal outage."""
    from app.workflows import client as temporal  # local: tests patch get_client

    if pending_for(case_id):  # keep order behind older queued commands
        enqueue(case_id, command, arg)
        try:
            await deliver(await temporal.get_client(), case_id)
        except Exception:  # noqa: BLE001
            temporal.reset_client()
        return
    try:
        await _deliver(await temporal.get_client(), OutboxItem(
            case_id=case_id, command=command,
            arg=arg.model_dump(mode="json") if isinstance(arg, BaseModel) else arg))
    except Exception as e:  # noqa: BLE001
        temporal.reset_client()
        log.warning("follow-up command queued", extra={"case_id": case_id, "command": command, "error": repr(e)})
        enqueue(case_id, command, arg, error=repr(e))


async def reconcile_orphans(client: Client) -> int:
    """Queue a start for open cases whose workflow never started (e.g. created before the outbox existed)."""
    queued = 0
    for case in db.list_all("cases", Case, limit=10_000, where={"status": [CaseStatus.open.value]}):
        if case.followup_pending:
            continue
        try:
            desc = await client.get_workflow_handle(workflow_id(case.id)).describe()
            if desc.status is not None and desc.status != WorkflowExecutionStatus.RUNNING:
                continue
        except RPCError as e:
            if e.status != RPCStatusCode.NOT_FOUND:
                raise
            enqueue(case.id, START)
            queued += 1
    return queued
