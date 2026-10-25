from fastapi.testclient import TestClient

from app import db
from app.main import app
from app.schemas import Case, Notification

client = TestClient(app)


def test_metrics_series():
    db.put("cases", Case(person_name="A", situation="victim", description="x", status="escalated"))
    db.put("notifications", Notification(channel="telegram", recipient="c", message="m", status="failed"))
    client.get("/healthz")
    text = client.get("/metrics").text
    assert 'cybersafe_cases{status="escalated"} 1' in text
    assert 'cybersafe_cases{status="open"} 0' in text
    assert 'cybersafe_notifications{status="failed"} 1' in text
    assert "cybersafe_build_info{" in text and "cybersafe_process_uptime_seconds" in text
    assert 'cybersafe_http_requests_total{method="GET",path_template="/healthz",status="200"}' in text
    assert "cybersafe_http_request_duration_seconds_count" in text


def test_chaos_get_put_and_validation():
    assert client.get("/api/ops/chaos").json()["llm_down"] is False
    r = client.put("/api/ops/chaos", json={"llm_down": True, "telegram_failure_rate": 0.7})
    assert r.status_code == 200 and r.json()["telegram_failure_rate"] == 0.7
    assert client.get("/api/ops/chaos").json()["llm_down"] is True
    assert client.put("/api/ops/chaos", json={"telegram_failure_rate": 2}).status_code == 422
    assert client.put("/api/ops/chaos", json={"slow_analyze_ms": -1}).status_code == 422


def test_request_id_header():
    assert client.get("/healthz").headers["x-request-id"]
    assert client.get("/healthz", headers={"X-Request-ID": "abc"}).headers["x-request-id"] == "abc"
