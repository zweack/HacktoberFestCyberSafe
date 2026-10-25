"""L1: /readyz and /metrics report whether a worker is polling the follow-up task queue."""

import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api import health
from app.main import app
from app.workflows import client as temporal


def _client_with_pollers(*ages_seconds):
    pollers = [SimpleNamespace(last_access_time=SimpleNamespace(ToSeconds=lambda a=a: int(time.time() - a)))
               for a in ages_seconds]
    c = MagicMock()
    c.workflow_service.describe_task_queue = AsyncMock(return_value=SimpleNamespace(pollers=pollers))
    return c


@pytest.fixture
def temporal_up(monkeypatch):
    class W:
        def close(self): ...

    async def fake_open(host, port):
        return None, W()

    monkeypatch.setattr(health.asyncio, "open_connection", fake_open)


@pytest.mark.parametrize("ages,worker,status", [((5,), "ok", "ready"), ((300,), "no_pollers", "degraded"),
                                                ((), "no_pollers", "degraded")])
def test_readyz_worker_check(monkeypatch, temporal_up, ages, worker, status):
    c = _client_with_pollers(*ages)
    monkeypatch.setattr(temporal, "get_client", AsyncMock(return_value=c))
    r = TestClient(app).get("/readyz")
    assert r.status_code == 200  # the API itself still works
    assert r.json()["checks"]["worker"] == worker and r.json()["status"] == status
    req = c.workflow_service.describe_task_queue.await_args.args[0]
    assert req.task_queue.name == "cybersafe-followups"


def test_metrics_worker_pollers(monkeypatch):
    monkeypatch.setattr(temporal, "get_client", AsyncMock(return_value=_client_with_pollers(1, 2, 500)))
    assert "cybersafe_worker_pollers 2" in TestClient(app).get("/metrics").text
    monkeypatch.setattr(temporal, "get_client", AsyncMock(side_effect=ConnectionError("down")))
    assert "cybersafe_worker_pollers -1" in TestClient(app).get("/metrics").text
