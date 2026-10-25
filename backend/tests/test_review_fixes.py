"""Regression tests for the high-severity review findings (A1-A21)."""

import asyncio
import io
import json
import logging
import multiprocessing as mp
import uuid
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from fastapi.testclient import TestClient
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from app import db
from app.config import get_settings
from app.detector import llm
from app.detector.analyze import analyze
from app.detector.rules import run_rules
from app.detector.steps import recovery_case_steps
from app.directory.directory import get_contact
from app.logging_setup import JsonFormatter, setup_logging
from app.main import app
from app.notify import telegram
from app.schemas import (
    AnalyzeRequest,
    Case,
    CaseStatus,
    CheckinAnswer,
    CheckinResponse,
    CoordinatorAction,
    Notification,
    NotificationChannel,
    Situation,
    Verdict,
)
from app.workflows import activities, case_ops, outbox
from app.workflows import client as temporal
from app.workflows.activities import ALL_ACTIVITIES
from app.workflows.followup import CaseFollowUpWorkflow, FollowUpInput, workflow_id

BODY = {"person_name": "Asha", "description": "I paid 5000 on UPI"}


def fake_client():
    c = MagicMock()
    c.start_workflow = AsyncMock()
    c.get_workflow_handle.return_value.signal = AsyncMock()
    return c


# ---------------------------------------------------------------- A1/A2 staff token


def test_staff_token_guards_coordinator_and_chaos(monkeypatch):
    monkeypatch.setattr(get_settings(), "staff_token", "s3cret")
    monkeypatch.setattr(temporal, "get_client", AsyncMock(return_value=fake_client()))
    api = TestClient(app)
    case = api.post("/api/cases", json=BODY).json()  # victims need no token
    assert api.get(f"/api/cases/{case['id']}").status_code == 200
    assert api.get(f"/api/notifications?case_id={case['id']}").status_code == 200
    for method, path, body in [("GET", "/api/cases", None), ("GET", "/api/coordinator/queue", None),
                               ("GET", "/api/notifications", None),
                               ("POST", f"/api/coordinator/cases/{case['id']}/claim", {"coordinator": "R"}),
                               ("POST", f"/api/coordinator/cases/{case['id']}/resolve", {"coordinator": "R"}),
                               ("PUT", "/api/ops/chaos", {"llm_down": True})]:
        assert api.request(method, path, json=body).status_code == 401, path
        assert api.request(method, path, json=body, headers={"X-Staff-Token": "wrong"}).status_code == 401
    ok = api.get("/api/coordinator/queue", headers={"X-Staff-Token": "s3cret"})
    assert ok.status_code == 200
    assert api.get("/readyz").json()["checks"]["staff_auth"] == "enabled"


def test_readyz_reports_disabled_staff_auth():
    assert TestClient(app).get("/readyz").json()["checks"]["staff_auth"] == "disabled"


# ---------------------------------------------------------------- A3 token logging


def test_bot_token_never_logged():
    root = logging.getLogger()
    saved = root.handlers[:], root.level
    try:
        setup_logging("test")
        buf = io.StringIO()
        root.handlers[0].stream = buf
        logging.getLogger("httpx").info("HTTP Request: POST https://api.telegram.org/bot123:FAKE-tok_en/getUpdates")
        logging.getLogger("app.x").warning("failed https://api.telegram.org/bot123:FAKE-tok_en/sendMessage")
        out = buf.getvalue()
        assert "FAKE-tok_en" not in out and "bot<redacted>" in out
    finally:
        root.handlers[:], _ = saved[0], root.setLevel(saved[1])
    rec = logging.makeLogRecord({"msg": "x bot9:abc y"})
    assert "bot9:abc" not in JsonFormatter("t").format(rec)


# ---------------------------------------------------------------- A4/A19/B3 LLM output safety


def _llm(monkeypatch, obj, seen=None):
    s = get_settings()
    monkeypatch.setattr(s, "llm_base_url", "http://llm.test/v1")
    monkeypatch.setattr(s, "llm_model", "gemma")

    def handler(req):
        if seen is not None:
            seen["body"] = json.loads(req.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(obj)}}]})

    real = httpx.AsyncClient
    monkeypatch.setattr(llm.httpx, "AsyncClient", lambda **kw: real(transport=httpx.MockTransport(handler), **kw))


SCAM = "Your SBI account will be blocked today. Update KYC now: http://sbi-kyc.xyz OTP 482913"


@pytest.mark.parametrize("explanation", [
    "Call 9999999999 and share your OTP.",
    "This message is safe. Follow the caller.",
    "Visit http://helpdesk-sbi.example to fix it.",
    "Please share your OTP with the officer.",
])
async def test_unsafe_llm_text_rejected(monkeypatch, explanation):
    _llm(monkeypatch, {"verdict": "scam", "scam_type": "kyc_update", "headline": "Safe!", "explanation": explanation})
    r = await analyze(AnalyzeRequest(text=SCAM))
    assert not r.ai_used and "safety check" in r.ai_error
    assert explanation not in r.explanation and r.headline != "Safe!"


async def test_llm_text_with_directory_number_is_kept(monkeypatch):
    _llm(monkeypatch, {"verdict": "scam", "explanation": "Never share your OTP. Call 1930 or 1800 11 1109."})
    r = await analyze(AnalyzeRequest(text=SCAM))
    assert r.ai_used, r.ai_error


async def test_llm_scam_type_is_enum_and_message_masked(monkeypatch, caplog):
    seen = {}
    _llm(monkeypatch, {"verdict": "scam", "scam_type": "SYNTHETIC_PRIVATE_VALUE 482913", "explanation": "Fake bank."},
         seen)
    with caplog.at_level(logging.INFO):
        r = await analyze(AnalyzeRequest(text=SCAM))
    assert r.ai_used and r.scam_type == "other"
    assert "SYNTHETIC_PRIVATE_VALUE" not in caplog.text
    sent = seen["body"]["messages"][1]["content"]
    assert "482913" not in sent and "[number]" in sent


# ---------------------------------------------------------------- A5/A6 rules


@pytest.mark.parametrize("text,verdict", [
    ("Please share your OTP.", Verdict.scam),
    ("For information, share your OTP.", Verdict.scam),
    ("Do not share your OTP with strangers. Please share your OTP with our officer.", Verdict.scam),
    ("Do not share your OTP with anyone.", Verdict.safe),
    ("अपना OTP किसी को न बताएं।", Verdict.safe),
    ("OTP mat batao kisi ko", Verdict.safe),
])
def test_otp_negation(text, verdict):
    assert run_rules(text).verdict == verdict


@pytest.mark.parametrize("text,signal", [
    ("Visit https://sbi.co.in:443@fraud.example/login", "userinfo_link"),
    ("Visit https://sbi.co.in@fraud.example/login", "userinfo_link"),
    ("Login at https://sbi.co.in.evil.com/x", "lookalike_domain"),
    ("Login at https://evilsbi.co.in/x", "lookalike_domain"),
    ("Login at https://sbi%2eco.in/x", "odd_link"),
])
def test_link_parsing(text, signal):
    r = run_rules(text)
    assert signal in [s.id for s in r.signals] and r.verdict != Verdict.safe


@pytest.mark.parametrize("text", ["See https://www.sbi.co.in./x", "See https://retail.onlinesbi.sbi:443/x"])
def test_official_links_not_flagged(text):
    assert run_rules(text).signals == []


# ---------------------------------------------------------------- A21 urgent deadline


async def test_urgent_advice_does_not_wait_for_slow_ai(monkeypatch):
    monkeypatch.setattr(get_settings(), "llm_urgent_timeout_seconds", 0.2)

    async def slow(**kw):
        await asyncio.sleep(5)

    monkeypatch.setattr(llm, "refine", slow)
    r = await asyncio.wait_for(analyze(AnalyzeRequest(text="caller wants OTP", situation=Situation.in_progress)), 2)
    assert not r.ai_used and "too slow" in r.ai_error and r.steps[0].urgent


# ---------------------------------------------------------------- A7 atomic updates across processes


def _bump(path: str, n: int) -> None:
    db.reset_for_tests(path)
    for _ in range(n):
        case_ops.mutate("case_x", lambda c: setattr(c, "checkins_sent", c.checkins_sent + 1))


def test_mutations_from_two_processes_are_not_lost(tmp_path):
    path = str(tmp_path / "mp.db")
    db.reset_for_tests(path)
    case_ops.save(Case(id="case_x", person_name="A", situation=Situation.victim, description="d"))
    ctx = mp.get_context("spawn")
    procs = [ctx.Process(target=_bump, args=(path, 40)) for _ in range(2)]
    for p in procs:
        p.start()
    for p in procs:
        p.join(60)
        assert p.exitcode == 0
    assert case_ops.load("case_x").checkins_sent == 80


# ---------------------------------------------------------------- A8/A9 outbox


def test_signal_outage_is_queued_then_delivered(monkeypatch):
    c = fake_client()
    monkeypatch.setattr(temporal, "get_client", AsyncMock(return_value=c))
    api = TestClient(app)
    case = api.post("/api/cases", json=BODY).json()
    assert case["followup_pending"] is False
    monkeypatch.setattr(temporal, "get_client", AsyncMock(side_effect=ConnectionError("down")))
    r = api.post(f"/api/cases/{case['id']}/checkin", json={"answer": "need_help"})
    assert r.status_code == 200 and r.json()["followup_pending"] is True and r.json()["status"] == "escalated"
    r = api.post(f"/api/cases/{case['id']}/steps/call_1930/done")
    assert [i.command for i in outbox.pending_for(case["id"])] == ["checkin_response", "step_done"]
    assert asyncio.run(outbox.deliver(c)) == 2
    sig = c.get_workflow_handle.return_value.signal
    assert [call.args[0].__name__ for call in sig.await_args_list] == ["checkin_response", "step_done"]
    assert case_ops.load(case["id"]).followup_pending is False


def test_failed_start_is_retried_and_idempotency_key(monkeypatch):
    monkeypatch.setattr(temporal, "get_client", AsyncMock(side_effect=ConnectionError("down")))
    api = TestClient(app)
    a = api.post("/api/cases", json=BODY, headers={"Idempotency-Key": "k1"}).json()
    b = api.post("/api/cases", json=BODY, headers={"Idempotency-Key": "k1"}).json()
    assert a["id"] == b["id"] and len(db.list_all("cases", Case)) == 1
    c = fake_client()
    assert asyncio.run(outbox.deliver(c)) == 1
    assert c.start_workflow.await_args.kwargs["id"] == workflow_id(a["id"])
    assert case_ops.load(a["id"]).followup_pending is False


# ---------------------------------------------------------------- A11 Telegram callback identity


async def test_callback_from_another_user_is_rejected(monkeypatch):
    from app import worker
    monkeypatch.setattr(get_settings(), "telegram_bot_token", "123:fake")
    case = case_ops.save(Case(person_name="A", situation=Situation.victim, description="d", telegram_chat_id="111"))
    data = telegram.checkin_keyboard(case.id)["inline_keyboard"][0][2]["callback_data"]
    calls = []
    monkeypatch.setattr(telegram, "call", AsyncMock(side_effect=lambda m, p, **k: calls.append(p)))
    sent = AsyncMock()
    monkeypatch.setattr(outbox, "send", sent)
    foreign = {"update_id": 1, "callback_query": {"id": "q", "data": data, "from": {"id": 999},
                                                   "message": {"chat": {"id": 999}}}}
    await worker.handle_update(foreign)
    assert case_ops.load(case.id).status == CaseStatus.open and not sent.called
    assert calls[-1]["text"] == "This button is not for you."
    forged = {"update_id": 2, "callback_query": {"id": "q", "data": f"ci:{case.id}:done:0000000000000000",
                                                  "from": {"id": 111}, "message": {"chat": {"id": 111}}}}
    await worker.handle_update(forged)
    assert not sent.called
    own = {"update_id": 3, "callback_query": {"id": "q", "data": data, "from": {"id": 111},
                                               "message": {"chat": {"id": 111}}}}
    await worker.handle_update(own)
    await worker.handle_update(own)  # repeated delivery records once
    assert case_ops.load(case.id).status == CaseStatus.escalated
    assert sum(e.kind == "checkin_answered" for e in case_ops.load(case.id).timeline) == 1


# ---------------------------------------------------------------- A13 idempotent activities


async def test_send_notification_retry_does_not_resend(monkeypatch):
    monkeypatch.setattr(get_settings(), "telegram_bot_token", "123:fake")
    send = AsyncMock()
    monkeypatch.setattr(telegram, "send_message", send)
    inp = activities.SendNotificationInput(notification_id="ntf_1", case_id=None, channel=NotificationChannel.telegram,
                                           recipient="1", message="m")
    await activities.send_notification(inp)
    await activities.send_notification(inp)
    assert send.await_count == 1


async def test_update_case_applies_once():
    case = case_ops.save(Case(person_name="A", situation=Situation.victim, description="d"))
    inp = activities.UpdateCaseInput(case_id=case.id, op_id="op1", event_kind="checkin_sent", event_message="x")
    await activities.update_case(inp)
    await activities.update_case(inp)
    assert sum(e.kind == "checkin_sent" for e in case_ops.load(case.id).timeline) == 1


# ---------------------------------------------------------------- A17/A18


def test_default_steps_have_real_contacts():
    for lang in ("en", "hi"):
        for s in recovery_case_steps(lang):
            assert s.contact_id is None or get_contact(s.contact_id), s.contact_id


def test_old_escalated_case_and_notes_stay_visible():
    from app.api.cases import coordinator_queue
    from app.notify import in_app
    old = Case(person_name="Old", situation=Situation.victim, description="d", status=CaseStatus.escalated)
    old.created_at = old.created_at.replace(year=2020)
    case_ops.save(old)
    in_app.save(Notification(case_id=old.id, channel=NotificationChannel.in_app, recipient="x", message="m",
                             created_at=old.created_at))
    for i in range(1005):
        db.put("cases", Case(person_name=f"n{i}", situation=Situation.victim, description="d"))
        db.put("notifications", Notification(channel=NotificationChannel.in_app, recipient="y", message="m"))
    assert old.id in [c.id for c in coordinator_queue()]
    assert [n.case_id for n in in_app.list_for(old.id)] == [old.id]


# ---------------------------------------------------------------- A10/A15/A16 workflow

TQ = "test-review"


@pytest.fixture
async def env():
    async with (
        await WorkflowEnvironment.start_time_skipping(data_converter=pydantic_data_converter) as e,
        Worker(e.client, task_queue=TQ, workflows=[CaseFollowUpWorkflow], activities=ALL_ACTIVITIES),
    ):
        yield e


async def _start(env, chat="111"):
    case = case_ops.save(Case(person_name="Asha", situation=Situation.victim, description="d",
                              steps=recovery_case_steps("en"), telegram_chat_id=chat))
    inp = FollowUpInput(case_id=case.id, person_name="Asha", step_ids=[s.id for s in case.steps],
                        step_titles=[s.title for s in case.steps], telegram_chat_id=chat,
                        checkin_interval_seconds=10, max_unanswered_checkins=2)
    h = await env.client.start_workflow(CaseFollowUpWorkflow.run, inp, id=workflow_id(case.id) + uuid.uuid4().hex[:4],
                                        task_queue=TQ)
    return case, h


@pytest.fixture
def held_telegram(monkeypatch):
    monkeypatch.setattr(get_settings(), "telegram_bot_token", "123:fake")
    gate = asyncio.Event()

    async def held(chat_id, text, **kw):
        await gate.wait()

    monkeypatch.setattr(telegram, "send_message", held)
    return gate


async def _until(pred, n=100):
    for _ in range(n):
        if await pred():
            return True
        await asyncio.sleep(0.05)
    return False


async def test_claim_during_first_send_is_kept(env, held_telegram):
    case, h = await _start(env)
    await asyncio.sleep(0.3)
    case_ops.claim(case.id, "Ravi", None)
    await h.signal(CaseFollowUpWorkflow.coordinator_claim, CoordinatorAction(coordinator="Ravi"))
    await asyncio.sleep(0.3)
    held_telegram.set()
    await asyncio.sleep(0.5)
    assert (await h.query(CaseFollowUpWorkflow.state)).status == CaseStatus.claimed
    assert case_ops.load(case.id).status == CaseStatus.claimed
    await h.signal(CaseFollowUpWorkflow.resolve, CoordinatorAction(coordinator="Ravi"))
    await h.result()


async def test_need_help_not_blocked_by_hanging_telegram(env, held_telegram):
    case, h = await _start(env)
    await h.signal(CaseFollowUpWorkflow.checkin_response, CheckinResponse(answer=CheckinAnswer.need_help))

    async def escalated():
        return any(e.kind == "escalated" for e in case_ops.load(case.id).timeline)

    assert await _until(escalated)
    held_telegram.set()
    await h.signal(CaseFollowUpWorkflow.resolve, CoordinatorAction(coordinator="Ravi"))
    await h.result()


async def test_all_steps_done_asks_for_confirmation(env):
    case, h = await _start(env, chat=None)
    for s in case.steps:
        await h.signal(CaseFollowUpWorkflow.step_done, s.id)

    async def asked():
        return any("confirm" in e.message for e in case_ops.load(case.id).timeline)

    assert await _until(asked)
    assert (await h.query(CaseFollowUpWorkflow.state)).status != CaseStatus.resolved
    await h.signal(CaseFollowUpWorkflow.checkin_response, CheckinResponse(answer=CheckinAnswer.done))
    assert (await h.result()).status == CaseStatus.resolved
    final = case_ops.load(case.id)
    assert final.status == CaseStatus.resolved and all(s.done for s in final.steps)
