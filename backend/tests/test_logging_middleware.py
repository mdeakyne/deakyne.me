import sqlite3
from contextlib import contextmanager

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from backend.logging_middleware import LoggingMiddleware


def create_schema(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS api_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            endpoint TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ip_address TEXT,
            response_time_ms INTEGER,
            status_code INTEGER,
            user_agent TEXT,
            request_id TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def db_factory(db_path: str):
    @contextmanager
    def _get_db():
        conn = sqlite3.connect(db_path)
        try:
            yield conn
        finally:
            conn.close()

    return _get_db


def test_logging_middleware_records_metadata(tmp_path, monkeypatch):
    db_path = tmp_path / "metrics.db"
    create_schema(str(db_path))

    app = FastAPI()
    app.add_middleware(LoggingMiddleware, db_factory=db_factory(str(db_path)))

    events = []

    async def fake_emit(self, payload):
        events.append(payload)

    monkeypatch.setattr(LoggingMiddleware, "_emit_posthog_event", fake_emit, raising=False)

    @app.get("/ping")
    async def ping(request: Request):
        request.state.auth_email = "tester@example.com"
        return {"ok": True}

    client = TestClient(app)
    response = client.get("/ping", headers={"User-Agent": "pytest"})

    assert response.status_code == 200
    request_id = response.headers.get("X-Request-ID")
    assert request_id

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT email, endpoint, response_time_ms, status_code, user_agent, request_id FROM api_logs"
        ).fetchone()

        assert row is not None
        email, endpoint, response_time_ms, status_code, user_agent, stored_request_id = row
        assert email == "tester@example.com"
        assert endpoint == "/ping"
        assert status_code == 200
        assert user_agent == "pytest"
        assert stored_request_id == request_id
        assert response_time_ms >= 0
    assert events
    assert events[0]["email"] == "tester@example.com"
    assert events[0]["endpoint"] == "/ping"


def test_logging_middleware_defaults_to_anonymous(tmp_path, monkeypatch):
    db_path = tmp_path / "metrics.db"
    create_schema(str(db_path))

    app = FastAPI()
    app.add_middleware(LoggingMiddleware, db_factory=db_factory(str(db_path)))

    async def fake_emit(self, payload):
        return None

    monkeypatch.setattr(LoggingMiddleware, "_emit_posthog_event", fake_emit, raising=False)

    @app.get("/public")
    async def public_endpoint():
        return {"status": "ok"}

    client = TestClient(app)
    response = client.get("/public")
    assert response.status_code == 200

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT email FROM api_logs WHERE endpoint = '/public'"
        ).fetchone()
        assert row is not None
        assert row[0] == "anonymous"
