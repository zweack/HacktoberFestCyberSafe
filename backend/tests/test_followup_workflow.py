import asyncio
import uuid

import pytest
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from app import db
from app.notify import telegram
from app.schemas import (
    Case, CaseStatus, CheckinAnswer, CheckinResponse, CoordinatorAction, Notification, NotificationChannel,
    NotificationStatus, Situation,
)
from app.workflows import case_ops
from app.workflows.activities import ALL_ACTIVITIES
from app.workflows.followup import CaseFollowUpWorkflow, FollowUpInput, workflow_id
from app.detector.steps import recovery_case_steps

TQ = "test-followups"


@pytest.fixture
async def env():
    async with await WorkflowEnvironment.start_time_skipping(data_converter=pydantic_data_converter) as e:
        async with Worker(e.client, task_queue=TQ, workflows=[CaseFollowUpWorkflow], activities=ALL_ACTIVITIES):
            yield e


async def start(env, **case_kw):
    case = Case(person_name="Asha", situation=Situation.victim, description="paid via UPI",
                steps=recovery_case_steps("en"), **case_kw)
    case_ops.save(case)
    inp = FollowUpInput(case_id=case.id, person_name="Asha", step_ids=[s.id for s in case.steps],
                        step_titles=[s.title for s in case.steps], telegram_chat_id=case.telegram_chat_id,
                        checkin_interval_seconds=10, max_unanswered_checkins=2)
    h = await env.client.start_workflow(CaseFollowUpWorkflow.run, inp, id=workflow_id(case.id) + uuid.uuid4().hex[:4],
                                        task_queue=TQ)
    return case, h


def queue():
    from app.api.cases import coordinator_queue
    return coordinator_queue()


def kinds(case_id):
    return [e.kind for e in case_ops.load(case_id).timeline]


async def test_done_answer_resolves(env):
    case, h = await start(env)
    await h.signal(CaseFollowUpWorkflow.checkin_response, CheckinResponse(answer=CheckinAnswer.done))
    result = await h.result()
    assert result.status == CaseStatus.resolved
    assert case_ops.load(case.id).status == CaseStatus.resolved
    assert "escalated" not in kinds(case.id)


async def test_unanswered_checkins_escalate_then_claim_resolve(env):
    case, h = await start(env)
    await env.sleep(35)
    st = await h.query(CaseFollowUpWorkflow.state)
    assert st.status == CaseStatus.escalated and st.checkins_sent == 2
    c = case_ops.load(case.id)
    assert c.status == CaseStatus.escalated and c.checkins_sent == 2
    assert case.id in [c.id for c in queue()]
    await h.signal(CaseFollowUpWorkflow.coordinator_claim, CoordinatorAction(coordinator="Ravi"))
    assert (await h.query(CaseFollowUpWorkflow.state)).status == CaseStatus.claimed
    await h.signal(CaseFollowUpWorkflow.resolve, CoordinatorAction(coordinator="Ravi", note="bank refunded"))
    assert (await h.result()).status == CaseStatus.resolved
    assert case_ops.load(case.id).status == CaseStatus.resolved
    assert case.id not in [c.id for c in queue()]


async def test_need_help_escalates_immediately(env):
    case, h = await start(env)
    await h.signal(CaseFollowUpWorkflow.checkin_response, CheckinResponse(answer=CheckinAnswer.need_help))
    for _ in range(50):
        st = await h.query(CaseFollowUpWorkflow.state)
        if st.status == CaseStatus.escalated and "escalated" in kinds(case.id):
            break
        await asyncio.sleep(0.1)
    assert st.status == CaseStatus.escalated and st.checkins_sent == 0
    assert "escalated" in kinds(case.id)
    coord = [n for n in db.list_all("notifications", Notification) if n.recipient == "coordinator"]
    assert coord
    await h.signal(CaseFollowUpWorkflow.resolve, CoordinatorAction(coordinator="Ravi"))
    await h.result()


async def test_flaky_telegram_is_retried(env, monkeypatch):
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "telegram_bot_token", "test-token")
    calls = []

    async def flaky(chat_id, text, **kw):
        calls.append(text)
        if "do these steps" in text and calls.count(text) <= 2:
            raise telegram.TelegramError("simulated outage")

    monkeypatch.setattr(telegram, "send_message", flaky)
    case, h = await start(env, telegram_chat_id="12345")
    await h.signal(CaseFollowUpWorkflow.checkin_response, CheckinResponse(answer=CheckinAnswer.done))
    await h.result()
    tg = [n for n in db.list_all("notifications", Notification) if n.channel == NotificationChannel.telegram]
    first = next(n for n in tg if "do these steps" in n.message)
    assert first.attempts == 3 and first.status == NotificationStatus.sent and first.last_error == "simulated outage"
