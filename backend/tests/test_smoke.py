from fastapi.testclient import TestClient

from app import db
from app.main import app
from app.schemas import Case, Situation


def test_healthz():
    assert TestClient(app).get("/healthz").json() == {"status": "ok"}


def test_db_roundtrip():
    case = Case(person_name="Asha", situation=Situation.victim, description="paid 5000 via UPI")
    db.put("cases", case)
    loaded = db.get("cases", case.id, Case)
    assert loaded is not None and loaded.person_name == "Asha"
    assert [c.id for c in db.list_all("cases", Case)] == [case.id]
