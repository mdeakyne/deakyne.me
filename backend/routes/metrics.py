from __future__ import annotations

from typing import Callable, ContextManager, Any

from fastapi import APIRouter, Depends, HTTPException

try:
    from backend import posthog_insights
    from backend import metrics_store
except ImportError:
    import posthog_insights
    import metrics_store

router = APIRouter(prefix="/api/metrics", tags=["metrics"])

_db_factory: Callable[[], ContextManager[Any]] | None = None


def configure(db_factory: Callable[[], ContextManager]) -> None:
    global _db_factory
    _db_factory = db_factory


def reset() -> None:  # used in tests
    global _db_factory
    _db_factory = None


async def _get_connection():
    if _db_factory is None:
        raise HTTPException(status_code=500, detail="Metrics database not configured")
    with _db_factory() as conn:
        yield conn


@router.get("/overview")
async def get_overview(conn=Depends(_get_connection)):
    metrics_store.ensure_metrics_freshness(conn)
    overview = metrics_store.get_overview_metrics(conn)
    active_users = await posthog_insights.fetch_active_users()
    return {"local": overview, "posthog": active_users}


@router.get("/endpoints")
async def get_endpoints(conn=Depends(_get_connection)):
    metrics_store.ensure_metrics_freshness(conn)
    local_breakdown = metrics_store.get_endpoint_breakdown(conn)
    remote_breakdown = await posthog_insights.fetch_endpoint_usage()
    return {"local": local_breakdown, "posthog": remote_breakdown}


@router.get("/timeline")
async def get_timeline(conn=Depends(_get_connection)):
    metrics_store.ensure_metrics_freshness(conn)
    local_timeline = metrics_store.get_activity_timeline(conn)
    remote_timeline = await posthog_insights.fetch_usage_timeline()
    return {"local": local_timeline, "posthog": remote_timeline}


@router.get("/users")
async def get_users(conn=Depends(_get_connection)):
    metrics_store.ensure_metrics_freshness(conn)
    recent_users = metrics_store.get_recent_users(conn)
    active_users = await posthog_insights.fetch_active_users()
    return {"local": recent_users, "posthog": active_users}


@router.get("/dashboard")
async def get_dashboard(conn=Depends(_get_connection)):
    metrics_store.ensure_metrics_freshness(conn)

    overview = metrics_store.get_overview_metrics(conn)
    endpoints = metrics_store.get_endpoint_breakdown(conn)
    timeline = metrics_store.get_activity_timeline(conn)
    active_users = await posthog_insights.fetch_active_users()

    remote_endpoints = await posthog_insights.fetch_endpoint_usage()
    remote_timeline = await posthog_insights.fetch_usage_timeline()

    combined_overview = {
        "totalCalls": overview.get("total_calls", 0),
        "uniqueUsers": overview.get("unique_users", 0),
        "avgResponseTimeMs": overview.get("avg_response_time_ms", 0.0),
        "errorRate": overview.get("error_rate", 0.0),
        "activeUsers": (active_users.get("daily_active_users") or [{}])[-1].get("active_users") if active_users else None,
        "lastRefreshed": overview.get("last_refreshed"),
    }

    combined_endpoints = []
    remote_map = {item["endpoint"]: item["total"] for item in remote_endpoints}
    for item in endpoints:
        combined_endpoints.append(
            {
                "endpoint": item["endpoint"],
                "totalCalls": item["total_calls"],
                "avgResponseTimeMs": item["avg_response_time_ms"],
                "errorRate": item["error_rate"],
                "remoteTotal": remote_map.get(item["endpoint"]),
            }
        )

    local_timeline = [
        {"label": point["date"], "totalCalls": point["total_calls"]}
        for point in timeline
    ]
    if not local_timeline and remote_timeline:
        local_timeline = [
            {"label": item["date"], "totalCalls": item["value"]}
            for item in remote_timeline
        ]

    response_times = {
        "p50": overview.get("avg_response_time_ms", 0.0),
        "p95": overview.get("avg_response_time_ms", 0.0) * 1.5,
        "p99": overview.get("avg_response_time_ms", 0.0) * 2,
        "trend": "flat",
    }

    return {
        "overview": combined_overview,
        "endpoints": combined_endpoints,
        "timeline": local_timeline,
        "responseTimes": response_times,
    }
