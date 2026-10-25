from fastapi.testclient import TestClient

from app.api.feed import SCRIPT
from app.main import app


def test_analyze_route():
    c = TestClient(app)
    r = c.post("/api/analyze", json={"text": "Install AnyDesk now", "situation": "in_progress", "language": "hi"})
    assert r.status_code == 200
    body = r.json()
    assert body["verdict"] == "scam" and body["language"] == "hi" and body["ai_used"] is False
    assert c.post("/api/analyze", json={"text": ""}).status_code == 422


def test_directory_route_lang():
    c = TestClient(app)
    en = c.get("/api/directory").json()
    hi = c.get("/api/directory?lang=hi").json()
    assert len(en) == len(hi) >= 15
    assert en[0]["name"] != hi[0]["name"]


def test_feed_next_reset_and_mix():
    c = TestClient(app)
    assert c.get("/api/feed").json() == []
    verdicts = [c.post("/api/feed/next").json()["analysis"]["verdict"] for _ in SCRIPT]
    assert verdicts.count("safe") >= 3 and verdicts.count("scam") >= 6
    feed = c.get("/api/feed").json()
    assert len(feed) == len(SCRIPT)
    assert c.post("/api/feed/reset").json() == {"status": "ok"}
    assert c.get("/api/feed").json() == []
    assert c.post("/api/feed/next").json()["sender"] == SCRIPT[0][1]


async def test_feed_stream_emits_new_message():
    import asyncio

    from app.api import feed as feed_mod

    class FakeRequest:
        async def is_disconnected(self):
            return False

    resp = await feed_mod.stream(FakeRequest())
    it = resp.body_iterator
    assert (await it.__anext__()).startswith(": connected")
    await feed_mod.next_message()
    chunk = await asyncio.wait_for(it.__anext__(), timeout=5)
    assert chunk.startswith("event: message") and '"analysis"' in chunk
    await it.aclose()
