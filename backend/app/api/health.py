"""Liveness and readiness probes. Owner: ops."""

import asyncio
import time

from fastapi import APIRouter, Response

from app import db
from app.auth import staff_auth_enabled
from app.config import get_settings

router = APIRouter(tags=["health"])

POLLER_FRESH_SECONDS = 60


async def worker_pollers() -> int:
    """Workers polling the follow-up task queue in the last POLLER_FRESH_SECONDS (DescribeTaskQueue)."""
    from temporalio.api.enums.v1 import TaskQueueType
    from temporalio.api.taskqueue.v1 import TaskQueue
    from temporalio.api.workflowservice.v1 import DescribeTaskQueueRequest

    from app.workflows import client as temporal

    s = get_settings()
    client = await temporal.get_client()
    resp = await asyncio.wait_for(client.workflow_service.describe_task_queue(DescribeTaskQueueRequest(
        namespace=s.temporal_namespace, task_queue=TaskQueue(name=s.temporal_task_queue),
        task_queue_type=TaskQueueType.TASK_QUEUE_TYPE_WORKFLOW)), 2)
    now = time.time()
    return sum(1 for p in resp.pollers if now - p.last_access_time.ToSeconds() <= POLLER_FRESH_SECONDS)


@router.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@router.get("/readyz")
async def readyz(response: Response) -> dict:
    """Checks each dependency; 503 if the API itself cannot work (DB or Temporal down).

    No worker polling the task queue does not fail API readiness (the API still answers and
    saves cases), but status becomes "degraded" and checks.worker says "no_pollers":
    check-ins and escalations are not running until a worker is back. LLM is optional."""
    settings = get_settings()
    checks: dict[str, str] = {}
    try:
        db.ping()
        checks["database"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["database"] = f"error: {exc}"
    host, _, port = settings.temporal_address.partition(":")
    try:
        _, writer = await asyncio.wait_for(asyncio.open_connection(host, int(port or 7233)), 2)
        writer.close()
        checks["temporal"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["temporal"] = f"error: {exc!r}"
    checks["worker"] = "unknown"
    if checks["temporal"] == "ok":
        try:
            checks["worker"] = "ok" if await worker_pollers() > 0 else "no_pollers"
        except Exception as exc:  # noqa: BLE001
            checks["worker"] = f"error: {exc!r}"[:200]
    checks["llm"] = "configured" if settings.llm_configured else "not_configured"
    checks["staff_auth"] = "enabled" if staff_auth_enabled() else "disabled"
    ready = checks["database"] == "ok" and checks["temporal"] == "ok"
    response.status_code = 200 if ready else 503
    status = "not_ready" if not ready else "ready" if checks["worker"] == "ok" else "degraded"
    return {"status": status, "checks": checks}
