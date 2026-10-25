"""Tiny SQLite document store shared by the API and the Temporal worker.

Each collection is a table of (id, created_at, data JSON). Both processes open the same
file. Read-modify-write goes through update(), which holds a SQLite write lock
(BEGIN IMMEDIATE) for the whole change, so two processes cannot lose each other's updates.
"""

import json
import sqlite3
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from app.config import get_settings

COLLECTIONS = ("cases", "notifications", "feed_messages", "kv", "outbox")

T = TypeVar("T", bound=BaseModel)

_lock = threading.RLock()
_conn: sqlite3.Connection | None = None


def _connect() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        path = Path(get_settings().database_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        # isolation_level=None: autocommit; multi-statement changes use explicit BEGIN IMMEDIATE.
        _conn = sqlite3.connect(path, check_same_thread=False, timeout=10, isolation_level=None)
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute("PRAGMA busy_timeout=10000")
        for name in COLLECTIONS:
            _conn.execute(
                f"CREATE TABLE IF NOT EXISTS {name} ("
                "id TEXT PRIMARY KEY, created_at TEXT NOT NULL, data TEXT NOT NULL)"
            )
        _conn.execute("CREATE INDEX IF NOT EXISTS cases_status ON cases (json_extract(data, '$.status'))")
        _conn.execute("CREATE INDEX IF NOT EXISTS notifications_case ON notifications (json_extract(data, '$.case_id'))")
    return _conn


@contextmanager
def transaction() -> Iterator[sqlite3.Connection]:
    """One write transaction, exclusive across threads and processes."""
    with _lock:
        conn = _connect()
        conn.execute("BEGIN IMMEDIATE")
        try:
            yield conn
        except BaseException:
            conn.execute("ROLLBACK")
            raise
        conn.execute("COMMIT")


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


def _key_created(obj: BaseModel, id: str | None) -> tuple[str, str]:
    key = id or obj.id  # type: ignore[attr-defined]
    created = str(getattr(obj, "created_at", getattr(obj, "received_at", "")))
    return key, created


def _put(conn: sqlite3.Connection, collection: str, obj: BaseModel, id: str | None = None) -> None:
    key, created = _key_created(obj, id)
    conn.execute(
        f"INSERT INTO {collection} (id, created_at, data) VALUES (?, ?, ?) "
        "ON CONFLICT(id) DO UPDATE SET data = excluded.data",
        (key, created, obj.model_dump_json()),
    )


def put(collection: str, obj: BaseModel, *, id: str | None = None) -> None:
    assert collection in COLLECTIONS, collection
    with _lock:
        _put(_connect(), collection, obj, id)


def insert_new(collection: str, obj: BaseModel, *, id: str | None = None) -> bool:
    """Insert unless the id exists. Returns False if it was already there."""
    assert collection in COLLECTIONS, collection
    key, created = _key_created(obj, id)
    with _lock:
        cur = _connect().execute(
            f"INSERT OR IGNORE INTO {collection} (id, created_at, data) VALUES (?, ?, ?)",
            (key, created, obj.model_dump_json()),
        )
    return cur.rowcount == 1


def get(collection: str, id: str, model: type[T]) -> T | None:
    assert collection in COLLECTIONS, collection
    with _lock:
        row = _connect().execute(f"SELECT data FROM {collection} WHERE id = ?", (id,)).fetchone()
    return model.model_validate_json(row[0]) if row else None


def update(collection: str, id: str, model: type[T], fn: Callable[[T], None], *,
           once: str | None = None) -> T | None:
    """Atomically load, change with fn, and save one document. None if it does not exist.

    once: an idempotency key. If a change with this key was already applied, fn is skipped,
    so a retried activity cannot apply the same increment or timeline event twice.
    """
    assert collection in COLLECTIONS, collection
    with transaction() as conn:
        row = conn.execute(f"SELECT data FROM {collection} WHERE id = ?", (id,)).fetchone()
        if row is None:
            return None
        obj = model.model_validate_json(row[0])
        if once is not None:
            cur = conn.execute("INSERT OR IGNORE INTO kv (id, created_at, data) VALUES (?, '', '{}')",
                               (f"once:{once}",))
            if cur.rowcount == 0:
                return obj
        fn(obj)
        _put(conn, collection, obj, id)
    return obj


def list_all(collection: str, model: type[T], *, limit: int = 200, where: dict[str, list[str]] | None = None,
             oldest_first: bool = False) -> list[T]:
    """Newest first (or oldest first). `where` filters JSON fields in SQL, before LIMIT:
    {"status": ["escalated", "claimed"]} keeps documents whose $.status is one of those."""
    assert collection in COLLECTIONS, collection
    clauses, args = [], []
    for field, values in (where or {}).items():
        assert field.isidentifier(), field
        clauses.append(f"json_extract(data, '$.{field}') IN ({','.join('?' * len(values))})")
        args.extend(values)
    sql = f"SELECT data FROM {collection}"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += f" ORDER BY created_at {'ASC' if oldest_first else 'DESC'} LIMIT ?"
    with _lock:
        rows = _connect().execute(sql, (*args, limit)).fetchall()
    return [model.model_validate_json(r[0]) for r in rows]


def delete(collection: str, id: str) -> None:
    assert collection in COLLECTIONS, collection
    with _lock:
        _connect().execute(f"DELETE FROM {collection} WHERE id = ?", (id,))


def get_json(key: str, default: dict | None = None) -> dict:
    with _lock:
        row = _connect().execute("SELECT data FROM kv WHERE id = ?", (key,)).fetchone()
    return json.loads(row[0]) if row else (default or {})


def put_json(key: str, value: dict) -> None:
    with _lock:
        _connect().execute(
            "INSERT INTO kv (id, created_at, data) VALUES (?, '', ?) "
            "ON CONFLICT(id) DO UPDATE SET data = excluded.data",
            (key, json.dumps(value)),
        )
