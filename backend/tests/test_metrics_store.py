import sqlite3
from datetime import datetime, timedelta

import pytest

from backend import metrics_store


@pytest.fixture
def conn():
    connection = sqlite3.connect(":memory:")
    cursor = connection.cursor()
    cursor.execute(
        """
        CREATE TABLE api_logs (
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
        CREATE TABLE daily_metrics (
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
        CREATE TABLE endpoint_metrics (
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
    connection.commit()
    yield connection
    connection.close()


def seed_logs(connection):
    cursor = connection.cursor()
    base_time = datetime.utcnow().replace(microsecond=0)
    rows = [
        ("user1@example.com", "/api/profile", base_time - timedelta(days=1), 120, 200),
        ("user2@example.com", "/api/profile", base_time - timedelta(days=1), 80, 200),
        ("user1@example.com", "/api/books", base_time, 150, 500),
        ("user3@example.com", "/api/books", base_time, 90, 200),
    ]
    for email, endpoint, ts, response_time, status in rows:
        cursor.execute(
            """
            INSERT INTO api_logs (email, endpoint, timestamp, response_time_ms, status_code)
            VALUES (?, ?, ?, ?, ?)
            """,
            (email, endpoint, ts.isoformat(), response_time, status),
        )
    connection.commit()


def test_refresh_materialized_views_populates_tables(conn):
    seed_logs(conn)
    metrics_store.refresh_materialized_views(conn)

    daily = conn.execute("SELECT date, total_calls, unique_users, error_rate FROM daily_metrics ORDER BY date").fetchall()
    assert len(daily) == 2
    assert daily[0][1] == 2
    assert daily[1][2] == 2  # two unique users on most recent day

    endpoints = conn.execute("SELECT endpoint, total_calls, error_count FROM endpoint_metrics ORDER BY endpoint").fetchall()
    assert endpoints
    profile = next(row for row in endpoints if row[0] == "/api/profile")
    assert profile[1] == 2
    assert profile[2] == 0
    books = next(row for row in endpoints if row[0] == "/api/books")
    assert books[2] == 1  # one error (status 500)


def test_getters_return_expected_shapes(conn):
    seed_logs(conn)
    metrics_store.refresh_materialized_views(conn)

    overview = metrics_store.get_overview_metrics(conn)
    assert overview["total_calls"] == 4
    assert overview["unique_users"] == 3
    assert overview["error_rate"] > 0

    top_endpoints = metrics_store.get_endpoint_breakdown(conn)
    assert top_endpoints[0]["endpoint"] == "/api/books"

    timeline = metrics_store.get_activity_timeline(conn)
    assert len(timeline) == 2
    assert timeline[0]["total_calls"] == 2


def test_ensure_metrics_freshness_triggers_refresh(conn, monkeypatch):
    seed_logs(conn)
    metrics_store.refresh_materialized_views(conn)

    conn.execute("UPDATE daily_metrics SET refreshed_at = '2000-01-01T00:00:00Z'")
    conn.commit()

    called = []

    def fake_refresh(connection):
        called.append(True)

    monkeypatch.setattr(metrics_store, "refresh_materialized_views", fake_refresh)
    metrics_store.ensure_metrics_freshness(conn, max_age_minutes=15)

    assert called == [True]
