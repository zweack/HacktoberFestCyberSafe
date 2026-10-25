"""FastAPI entrypoint. Each router lives in app/api/<area>.py and is owned by one area."""

import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app import metrics
from app.api import analyze, cases, feed, health, ops
from app.auth import warn_if_disabled
from app.config import get_settings
from app.logging_setup import setup_logging

setup_logging("api")
warn_if_disabled()

app = FastAPI(title="Cyber Support Navigator", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in get_settings().cors_origins.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(analyze.router, prefix="/api")
app.include_router(feed.router, prefix="/api")
app.include_router(cases.router, prefix="/api")
app.include_router(cases.staff_router, prefix="/api")
app.include_router(ops.router)


_access_log = logging.getLogger("app.access")


@app.middleware("http")
async def request_context(request: Request, call_next):
    """Request id + one JSON access log line + HTTP metrics. Owner: ops."""
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:16]
    start = time.perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        route = request.scope.get("route")
        path_template = getattr(route, "path", None) or "unmatched"
        labels = {"method": request.method, "path_template": path_template}
        metrics.inc("cybersafe_http_requests_total", status=str(status), **labels)
        metrics.inc("cybersafe_http_request_duration_seconds_sum", duration_ms / 1000, **labels)
        metrics.inc("cybersafe_http_request_duration_seconds_count", **labels)
        _access_log.info(
            "request",
            extra={"method": request.method, "path": request.url.path, "status": status,
                   "duration_ms": round(duration_ms, 1), "request_id": request_id},
        )
