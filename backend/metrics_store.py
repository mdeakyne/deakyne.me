from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Sequence


UTC = timezone.utc
REFRESH_MAX_AGE_MINUTES = 15


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


def _serialize_timestamp(value: datetime) -> str:
    return value.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        if value.endswith("Z"):
            return datetime.fromisoformat(value[:-1]).replace(tzinfo=UTC)
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def refresh_materialized_views(conn) -> None:
    """Rebuild daily and endpoint metrics tables from api_logs."""
    now_iso = _serialize_timestamp(_utcnow())

    conn.execute("DELETE FROM daily_metrics")
    daily_rows = conn.execute(
        """
        SELECT
            DATE(timestamp) AS day,
            COUNT(*) AS total_calls,
            COUNT(DISTINCT email) AS unique_users,
            AVG(COALESCE(response_time_ms, 0)) AS avg_response_time_ms,
            SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END) AS error_count
        FROM api_logs
        GROUP BY day
        ORDER BY day
        """
    ).fetchall()

    for row in daily_rows:
        day, total_calls, unique_users, avg_response_time_ms, error_count = row
        total_calls = total_calls or 0
        unique_users = unique_users or 0
        avg_response_time_ms = float(avg_response_time_ms or 0.0)
        error_count = error_count or 0
        error_rate = (error_count / total_calls) if total_calls else 0.0
        conn.execute(
            """
            INSERT INTO daily_metrics (
                date,
                total_calls,
                unique_users,
                avg_response_time_ms,
                error_rate,
                refreshed_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (day, total_calls, unique_users, avg_response_time_ms, error_rate, now_iso),
        )

    conn.execute("DELETE FROM endpoint_metrics")
    endpoint_rows = conn.execute(
        """
        SELECT
            DATE(timestamp) AS day,
            endpoint,
            COUNT(*) AS total_calls,
            AVG(COALESCE(response_time_ms, 0)) AS avg_response_time_ms,
            SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END) AS error_count
        FROM api_logs
        GROUP BY day, endpoint
        ORDER BY day, endpoint
        """
    ).fetchall()

    for row in endpoint_rows:
        day, endpoint, total_calls, avg_response_time_ms, error_count = row
        total_calls = total_calls or 0
        avg_response_time_ms = float(avg_response_time_ms or 0.0)
        error_count = error_count or 0
        error_rate = (error_count / total_calls) if total_calls else 0.0
        conn.execute(
            """
            INSERT INTO endpoint_metrics (
                date,
                endpoint,
                total_calls,
                avg_response_time_ms,
                error_rate,
                error_count
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (day, endpoint, total_calls, avg_response_time_ms, error_rate, error_count),
        )

    conn.commit()


def ensure_metrics_freshness(conn, max_age_minutes: int = REFRESH_MAX_AGE_MINUTES) -> None:
    """Refresh metrics tables if the most recent refresh is stale."""
    row = conn.execute("SELECT MAX(refreshed_at) FROM daily_metrics").fetchone()
    last_refreshed = _parse_timestamp(row[0]) if row else None

    if (
        last_refreshed is None
        or _utcnow() - last_refreshed > timedelta(minutes=max_age_minutes)
    ):
        refresh_materialized_views(conn)


def get_last_refresh_timestamp(conn) -> str | None:
    row = conn.execute("SELECT MAX(refreshed_at) FROM daily_metrics").fetchone()
    return row[0] if row and row[0] else None


def get_overview_metrics(conn) -> Dict[str, Any]:
    row = conn.execute(
        """
        SELECT
            COUNT(*) AS total_calls,
            COUNT(DISTINCT email) AS unique_users,
            AVG(COALESCE(response_time_ms, 0)) AS avg_response_time_ms,
            SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END) AS error_count
        FROM api_logs
        """
    ).fetchone()

    total_calls = row[0] or 0
    unique_users = row[1] or 0
    avg_response_time_ms = float(row[2] or 0.0)
    error_count = row[3] or 0
    error_rate = (error_count / total_calls) if total_calls else 0.0

    return {
        "total_calls": total_calls,
        "unique_users": unique_users,
        "avg_response_time_ms": avg_response_time_ms,
        "error_rate": error_rate,
        "last_refreshed": get_last_refresh_timestamp(conn),
    }


def get_endpoint_breakdown(conn, limit: int = 10) -> List[Dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT
            endpoint,
            SUM(total_calls) AS total_calls,
            SUM(error_count) AS errors,
            AVG(avg_response_time_ms) AS avg_response_time_ms
        FROM endpoint_metrics
        GROUP BY endpoint
        ORDER BY total_calls DESC, endpoint ASC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()

    results: List[Dict[str, Any]] = []
    for endpoint, total_calls, errors, avg_response_time_ms in rows:
        total_calls = total_calls or 0
        errors = errors or 0
        avg_response_time_ms = float(avg_response_time_ms or 0.0)
        error_rate = (errors / total_calls) if total_calls else 0.0
        results.append(
            {
                "endpoint": endpoint,
                "total_calls": total_calls,
                "avg_response_time_ms": avg_response_time_ms,
                "error_rate": error_rate,
            }
        )
    return results


def get_activity_timeline(conn, days: int = 30) -> List[Dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT date, total_calls
        FROM daily_metrics
        ORDER BY date DESC
        LIMIT ?
        """,
        (days,),
    ).fetchall()

    timeline = [
        {"date": row[0], "total_calls": row[1] or 0}
        for row in rows
    ]
    return list(reversed(timeline))


def get_recent_users(conn, days: int = 7) -> List[Dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT
            email,
            COUNT(*) AS calls,
            MAX(timestamp) AS last_seen
        FROM api_logs
        WHERE timestamp >= DATE('now', ?)
        GROUP BY email
        ORDER BY calls DESC
        """,
        (f"-{days} days",),
    ).fetchall()

    return [
        {"email": row[0], "calls": row[1], "last_seen": row[2]}
        for row in rows
    ]
