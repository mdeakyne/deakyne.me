from __future__ import annotations

import os
from typing import Any, Dict, List

import httpx

HTTP_TIMEOUT = float(os.getenv("POSTHOG_HTTP_TIMEOUT", "10"))


def _is_configured() -> bool:
    return bool(_get_host() and _get_project_id() and _get_api_key())


def _get_host() -> str:
    return os.getenv("POSTHOG_HOST", "https://us.i.posthog.com")


def _get_project_id() -> str | None:
    return os.getenv("POSTHOG_PROJECT_ID")


def _get_api_key() -> str | None:
    return os.getenv("POSTHOG_API_KEY") or os.getenv("POSTHOG_PERSONAL_API_KEY")


def _authorization_headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {_get_api_key()}",
        "Content-Type": "application/json",
    }


def _query_endpoint() -> str:
    host = _get_host()
    project_id = _get_project_id()
    return f"{host.rstrip('/')}/api/projects/{project_id}/query/"


async def _posthog_query(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not _is_configured():
        return {}

    # PostHog Query API requires queries to be wrapped in a "query" field
    request_body = {"query": payload}

    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.post(
                _query_endpoint(),
                headers=_authorization_headers(),
                json=request_body,
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        # Log error but don't crash - gracefully degrade to no PostHog data
        import logging
        logging.warning(f"PostHog query failed: {e}")
        return {}


async def fetch_usage_timeline(days: int = 30) -> List[Dict[str, Any]]:
    """Return time-series data for API requests from PostHog."""
    payload = {
        "kind": "TrendsQuery",
        "interval": "day",
        "dateRange": {"date_from": f"-{days}d"},
        "series": [
            {
                "event": "api_request",
                "kind": "EventsNode",
                "name": "api_request",
            }
        ],
    }

    data = await _posthog_query(payload)
    if not data:
        return []

    results = data.get("results") or []
    if not results:
        return []

    first = results[0]
    labels = first.get("labels") or []
    values = first.get("data") or []
    return [
        {"date": labels[i], "value": values[i]}
        for i in range(min(len(labels), len(values)))
    ]


async def fetch_endpoint_usage(limit: int = 10, days: int = 30) -> List[Dict[str, Any]]:
    """Return per-endpoint usage from PostHog."""
    payload = {
        "kind": "TrendsQuery",
        "interval": "day",
        "dateRange": {"date_from": f"-{days}d"},
        "series": [
            {
                "event": "api_request",
                "kind": "EventsNode",
                "name": "api_request",
            }
        ],
        "breakdown": "endpoint",
        "breakdown_type": "event",
        "breakdown_limit": limit,
    }

    data = await _posthog_query(payload)
    if not data:
        return []

    results = data.get("results") or []
    breakdown = []
    for item in results:
        breakdown.append(
            {
                "endpoint": item.get("label"),
                "total": sum(item.get("data") or []),
            }
        )
    breakdown.sort(key=lambda row: (-row["total"], row["endpoint"]))
    return breakdown[:limit]


async def fetch_active_users(days: int = 7) -> Dict[str, Any]:
    """Return active user counts via unique user aggregation."""
    payload = {
        "kind": "TrendsQuery",
        "interval": "day",
        "dateRange": {"date_from": f"-{days}d"},
        "series": [
            {
                "event": "api_request",
                "kind": "EventsNode",
                "name": "api_request",
                "aggregation": "unique_users",
            }
        ],
    }

    data = await _posthog_query(payload)
    if not data:
        return {"daily_active_users": []}

    results = data.get("results") or []
    if not results:
        return {"daily_active_users": []}

    first = results[0]
    labels = first.get("labels") or []
    values = first.get("data") or []
    dau = [
        {"date": labels[i], "active_users": values[i]}
        for i in range(min(len(labels), len(values)))
    ]
    return {"daily_active_users": dau}
