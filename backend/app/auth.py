"""Shared staff token for coordinator and ops endpoints. Owner: ops.

This is not user accounts. One secret, STAFF_TOKEN, is shared by the volunteers who run
the coordinator queue and the ops page. Clients send it in the X-Staff-Token header.
When STAFF_TOKEN is unset (local development) the check is off; startup logs a warning
and /readyz reports "staff_auth": "disabled".
"""

import hmac
import logging

from fastapi import Header, HTTPException

from app.config import get_settings

log = logging.getLogger("app.auth")


def staff_auth_enabled() -> bool:
    return bool(get_settings().staff_token)


def warn_if_disabled() -> None:
    if not staff_auth_enabled():
        log.warning("STAFF_TOKEN is not set: coordinator and ops endpoints are open. Local development only.")


def require_staff(x_staff_token: str | None = Header(default=None)) -> None:
    """FastAPI dependency: 401 unless the header matches STAFF_TOKEN (when one is set)."""
    expected = get_settings().staff_token
    if not expected:
        return
    if not x_staff_token or not hmac.compare_digest(x_staff_token.encode(), expected.encode()):
        raise HTTPException(401, "Staff token missing or wrong", headers={"WWW-Authenticate": "X-Staff-Token"})
