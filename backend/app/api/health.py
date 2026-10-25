"""Liveness and readiness probes. Owner: ops."""

import asyncio

from fastapi import APIRouter, Response

from app import db
from app.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@router.get("/readyz")
async def readyz(response: Response) -> dict:
    """Checks each dependency; 503 if a required one is down. LLM is optional."""
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
    checks["llm"] = "configured" if settings.llm_configured else "not_configured"
    ready = checks["database"] == "ok" and checks["temporal"] == "ok"
    response.status_code = 200 if ready else 503
    return {"status": "ready" if ready else "not_ready", "checks": checks}
