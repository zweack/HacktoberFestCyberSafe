from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app import db
from app.main import app
from app.schemas import Case, CaseStatus
from app.workflows import client as temporal

BODY = {"person_name": "Asha", "language": "hi", "description": "I paid 5000 on UPI"}


@pytest.fixture
def fake_temporal(monkeypatch):
    c = MagicMock()
    c.start_workflow = AsyncMock()
    handle = MagicMock()
    handle.signal = AsyncMock()
    c.get_workflow_handle.return_value = handle
    monkeypatch.setattr(temporal, "get_client", AsyncMock(return_value=c))
    return c


def test_case_crud_and_signals(fake_temporal):
    api = TestClient(app)
    r = api.post("/api/cases", json=BODY)
    assert r.status_code == 200, r.text
    case = r.json()
    assert case["workflow_id"] == f"case-{case['id']}"
    assert case["steps"][0]["id"] == "call_1930" and "1930" in case["steps"][0]["title"]
    fake_temporal.start_workflow.assert_awaited_once()
    assert api.get("/api/cases").json()[0]["id"] == case["id"]

    r = api.post(f"/api/cases/{case['id']}/steps/call_1930/done")
    assert r.json()["steps"][0]["done"] is True
    assert api.post(f"/api/cases/{case['id']}/steps/nope/done").status_code == 404

    r = api.post(f"/api/cases/{case['id']}/checkin", json={"answer": "need_help"})
    assert r.json()["status"] == "escalated"
    assert [c["id"] for c in api.get("/api/coordinator/queue").json()] == [case["id"]]

    r = api.post(f"/api/coordinator/cases/{case['id']}/claim", json={"coordinator": "Ravi"})
    assert r.json()["status"] == "claimed" and r.json()["coordinator"] == "Ravi"
    r = api.post(f"/api/coordinator/cases/{case['id']}/resolve", json={"coordinator": "Ravi"})
    assert r.json()["status"] == "resolved"
    assert api.get("/api/coordinator/queue").json() == []
    assert fake_temporal.get_workflow_handle.return_value.signal.await_count == 4
    assert api.get("/api/cases/nope").status_code == 404
    assert api.get(f"/api/notifications?case_id={case['id']}").json() == []


def test_analysis_steps_used(fake_temporal):
    analysis = {"verdict": "scam", "risk_score": 90, "situation": "victim", "headline": "h", "explanation": "e",
                "steps": [{"id": "x1", "title": "Do X", "detail": "d"}]}
    case = TestClient(app).post("/api/cases", json={**BODY, "analysis": analysis}).json()
    assert [s["id"] for s in case["steps"]] == ["x1"]


def test_temporal_down_returns_503_and_saves_case(monkeypatch):
    monkeypatch.setattr(temporal, "get_client", AsyncMock(side_effect=ConnectionError("refused")))
    r = TestClient(app).post("/api/cases", json=BODY)
    assert r.status_code == 503
    detail = r.json()["detail"]
    assert "follow-up could not start" in detail["message"]
    case = db.get("cases", detail["case_id"], Case)
    assert case.status == CaseStatus.open and case.timeline[-1].kind == "error"
