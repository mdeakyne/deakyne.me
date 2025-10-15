import sqlite3
from contextlib import contextmanager
from datetime import datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.routes import metrics as metrics_routes


def setup_database(db_path: str) -> None:
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
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS daily_metrics (
            date DATE PRIMARY KEY,
            total_calls INTEGER,
            unique_users INTEGER,
            avg_response_time_ms REAL,
            error_rate REAL,
            refreshed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS endpoint_metrics (
            date DATE,
            endpoint TEXT,
            total_calls INTEGER,
            avg_response_time_ms REAL,
            error_rate REAL,
            error_count INTEGER,
            PRIMARY KEY (date, endpoint)
        )
        """
    )

    now = datetime.utcnow().isoformat()
    rows = [
        ("user1@example.com", "/api/profile", now, 100, 200),
        ("user2@example.com", "/api/profile", now, 120, 200),
        ("user1@example.com", "/api/books", now, 200, 500),
    ]
    cursor.executemany(
        """
        INSERT INTO api_logs (email, endpoint, timestamp, response_time_ms, status_code)
        VALUES (?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()
    conn.close()


def make_db_factory(db_path: str):
    @contextmanager
    def _factory():
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    return _factory


@pytest.fixture
def metrics_app(tmp_path, monkeypatch):
    db_path = tmp_path / "metrics.db"
    setup_database(str(db_path))

    metrics_routes.reset()
    metrics_routes.configure(make_db_factory(str(db_path)))

    async def fake_fetch_active_users(days: int = 7):
        return {"daily_active_users": [{"date": "2025-10-01", "active_users": 3}]}

    async def fake_fetch_usage_timeline(days: int = 30):
        return [{"date": "2025-10-01", "value": 5}]

    async def fake_fetch_endpoint_usage(limit: int = 10, days: int = 30):
        return [{"endpoint": "/api/profile", "total": 2}]

    monkeypatch.setattr("backend.posthog_insights.fetch_active_users", fake_fetch_active_users)
    monkeypatch.setattr("backend.posthog_insights.fetch_usage_timeline", fake_fetch_usage_timeline)
    monkeypatch.setattr("backend.posthog_insights.fetch_endpoint_usage", fake_fetch_endpoint_usage)

    app = FastAPI()
    app.include_router(metrics_routes.router)
    yield TestClient(app)
    metrics_routes.reset()


def test_metrics_overview(metrics_app):
    response = metrics_app.get("/api/metrics/overview")
    assert response.status_code == 200
    data = response.json()
    assert data["local"]["total_calls"] == 3
    assert data["posthog"]["daily_active_users"][0]["active_users"] == 3


def test_metrics_endpoints(metrics_app):
    response = metrics_app.get("/api/metrics/endpoints")
    assert response.status_code == 200
    data = response.json()
    assert data["local"][0]["endpoint"] == "/api/profile"
    assert data["posthog"][0]["endpoint"] == "/api/profile"


def test_metrics_timeline(metrics_app):
    response = metrics_app.get("/api/metrics/timeline")
    assert response.status_code == 200
    data = response.json()
    assert data["local"]
    assert data["posthog"][0]["value"] == 5


def test_metrics_users(metrics_app):
    response = metrics_app.get("/api/metrics/users")
    assert response.status_code == 200
    data = response.json()
    assert data["local"][0]["email"] == "user1@example.com"
    assert data["posthog"]["daily_active_users"][0]["active_users"] == 3


def test_metrics_dashboard(metrics_app):
    response = metrics_app.get("/api/metrics/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert data["overview"]["totalCalls"] == 3
    assert data["endpoints"][0]["endpoint"] == "/api/profile"
    assert data["timeline"][0]["label"]
