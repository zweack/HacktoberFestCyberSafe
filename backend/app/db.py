"""Tiny SQLite document store shared by the API and the Temporal worker.

Each collection is a table of (id, created_at, data JSON). Both processes open
the same file; WAL mode keeps concurrent readers and one writer happy.
"""

import json
import sqlite3
import threading
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from app.config import get_settings

COLLECTIONS = ("cases", "notifications", "feed_messages", "coordinator_queue", "kv")

T = TypeVar("T", bound=BaseModel)

_lock = threading.Lock()
_conn: sqlite3.Connection | None = None


def _connect() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        path = Path(get_settings().database_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(path, check_same_thread=False, timeout=10)
        _conn.execute("PRAGMA journal_mode=WAL")
        for name in COLLECTIONS:
            _conn.execute(
                f"CREATE TABLE IF NOT EXISTS {name} ("
                "id TEXT PRIMARY KEY, created_at TEXT NOT NULL, data TEXT NOT NULL)"
            )
        _conn.commit()
    return _conn


def reset_for_tests(path: str) -> None:
    """Point the store at a fresh file. Tests only."""
    global _conn
    with _lock:
        if _conn is not None:
            _conn.close()
        _conn = None
        get_settings().database_path = path


def ping() -> bool:
    with _lock:
        _connect().execute("SELECT 1").fetchone()
    return True


def put(collection: str, obj: BaseModel, *, id: str | None = None) -> None:
    assert collection in COLLECTIONS, collection
    key = id or getattr(obj, "id")
    created = str(getattr(obj, "created_at", getattr(obj, "received_at", "")))
    with _lock:
        conn = _connect()
        conn.execute(
            f"INSERT INTO {collection} (id, created_at, data) VALUES (?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET data = excluded.data",
            (key, created, obj.model_dump_json()),
        )
        conn.commit()


def get(collection: str, id: str, model: type[T]) -> T | None:
    assert collection in COLLECTIONS, collection
    with _lock:
        row = _connect().execute(f"SELECT data FROM {collection} WHERE id = ?", (id,)).fetchone()
    return model.model_validate_json(row[0]) if row else None


def list_all(collection: str, model: type[T], *, limit: int = 200) -> list[T]:
    """Newest first."""
    assert collection in COLLECTIONS, collection
    with _lock:
        rows = _connect().execute(
            f"SELECT data FROM {collection} ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [model.model_validate_json(r[0]) for r in rows]


def delete(collection: str, id: str) -> None:
    assert collection in COLLECTIONS, collection
    with _lock:
        conn = _connect()
        conn.execute(f"DELETE FROM {collection} WHERE id = ?", (id,))
        conn.commit()


def get_json(key: str, default: dict | None = None) -> dict:
    with _lock:
        row = _connect().execute("SELECT data FROM kv WHERE id = ?", (key,)).fetchone()
    return json.loads(row[0]) if row else (default or {})


def put_json(key: str, value: dict) -> None:
    with _lock:
        conn = _connect()
        conn.execute(
            "INSERT INTO kv (id, created_at, data) VALUES (?, '', ?) "
            "ON CONFLICT(id) DO UPDATE SET data = excluded.data",
            (key, json.dumps(value)),
        )
        conn.commit()
