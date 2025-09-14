from __future__ import annotations

import json
from typing import Dict

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app


def with_key(headers: Dict[str, str] | None = None) -> Dict[str, str]:
    base = {"Authorization": "Bearer test-key"}
    base.update(headers or {})
    return base


@pytest.fixture(autouse=True)
def _env_api_keys(monkeypatch):
    monkeypatch.setenv("API_KEYS_JSON", json.dumps({"test-key": ["chat:write", "chat:read"]}))


def test_healthz():
    c = TestClient(app)
    r = c.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_chat_sync_happy_path():
    c = TestClient(app)
    body = {
        "messages": [
            {"role": "user", "content": "Hello there"},
        ],
        "session_id": "dev-1",
    }
    r = c.post("/api/chat", json=body, headers=with_key())
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == "dev-1"
    assert "You said:" in data["message"]
    assert isinstance(data["latency_ms"], int)


def test_chat_sync_validation_and_auth():
    c = TestClient(app)
    # Missing key
    r = c.post("/api/chat", json={"messages": [{"role": "user", "content": "x"}]})
    assert r.status_code == 401
    # Empty last user content
    r2 = c.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": "   "}]},
        headers=with_key(),
    )
    assert r2.status_code == 400


def test_chat_stream_sse_tokens_and_done():
    c = TestClient(app)
    with c.stream("GET", "/api/chat/stream", headers=with_key()) as r:
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/event-stream")
        body = b"".join([chunk for chunk in r.iter_raw()])
    text = body.decode()
    # Expect at least one token event and then done
    assert "event: token" in text
    assert "event: done" in text

