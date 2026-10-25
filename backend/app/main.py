"""FastAPI entrypoint. Each router lives in app/api/<area>.py and is owned by one area."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import analyze, cases, feed, health, ops
from app.config import get_settings
from app.logging_setup import setup_logging

setup_logging("api")

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
app.include_router(ops.router)
