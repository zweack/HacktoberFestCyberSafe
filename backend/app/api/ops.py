"""/metrics and chaos switches for the ops team. Owner: ops."""

import json
import logging
import os
import platform
import time

from fastapi import APIRouter, Depends, Response

from app import chaos, db, metrics
from app.auth import require_staff
from app.schemas import ChaosSettings

router = APIRouter(tags=["ops"])

_STARTED = time.time()


def _status_counts(collection: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    with db._lock:
        rows = db._connect().execute(
            f"SELECT json_extract(data, '$.status'), COUNT(*) FROM {collection} GROUP BY 1"
        ).fetchall()
    for status, n in rows:
        counts[str(status)] = n
    return counts


def _gauges() -> str:
    lines = [
        "# TYPE cybersafe_build_info gauge",
        f'cybersafe_build_info{{version="0.1.0",git_sha="{os.environ.get("GIT_SHA", "unknown")}",'
        f'python="{platform.python_version()}"}} 1',
        "# TYPE cybersafe_process_uptime_seconds gauge",
        f"cybersafe_process_uptime_seconds {time.time() - _STARTED:.1f}",
    ]
    try:
        cases = _status_counts("cases")
        notes = _status_counts("notifications")
        lines.append("# TYPE cybersafe_cases gauge")
        for s in sorted({"open", "escalated", *cases}):
            lines.append(f'cybersafe_cases{{status="{s}"}} {cases.get(s, 0)}')
        lines.append("# TYPE cybersafe_notifications gauge")
        for s in sorted({"pending", "sent", "failed", *notes}):
            lines.append(f'cybersafe_notifications{{status="{s}"}} {notes.get(s, 0)}')
        lines.append("cybersafe_db_up 1")
    except Exception:  # noqa: BLE001
        lines.append("cybersafe_db_up 0")
    c = chaos.get_chaos() if _db_ok() else ChaosSettings()
    lines += [
        f"cybersafe_chaos_llm_down {int(c.llm_down)}",
        f"cybersafe_chaos_telegram_failure_rate {c.telegram_failure_rate}",
        f"cybersafe_chaos_slow_analyze_ms {c.slow_analyze_ms}",
    ]
    return "\n".join(lines) + "\n"


def _db_ok() -> bool:
    try:
        return db.ping()
    except Exception:  # noqa: BLE001
        return False


@router.get("/metrics")
def get_metrics() -> Response:
    return Response(metrics.render() + _gauges(), media_type="text/plain; version=0.0.4")


@router.get("/api/ops/chaos", response_model=ChaosSettings)
def get_chaos() -> ChaosSettings:
    return chaos.get_chaos()


@router.put("/api/ops/chaos", response_model=ChaosSettings, dependencies=[Depends(require_staff)])
def put_chaos(body: ChaosSettings) -> ChaosSettings:
    logging.getLogger("app.ops").warning("chaos updated", extra={"chaos": json.loads(body.model_dump_json())})
    return chaos.set_chaos(body)
