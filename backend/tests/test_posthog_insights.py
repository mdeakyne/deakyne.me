import asyncio
import json
from typing import Any

import pytest

from backend import posthog_insights


class MockResponse:
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code

    def json(self):
        return self._json

    def raise_for_status(self):
        if not (200 <= self.status_code < 300):
            raise RuntimeError("HTTP error")


class MockAsyncClient:
    def __init__(self, response: MockResponse):
        self.response = response
        self.requests: list[dict[str, Any]] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, headers=None, json=None):
        self.requests.append({"url": url, "headers": headers, "json": json})
        return self.response


@pytest.mark.asyncio
async def test_fetch_usage_timeline_without_config(monkeypatch):
    monkeypatch.delenv("POSTHOG_PROJECT_ID", raising=False)
    monkeypatch.delenv("POSTHOG_API_KEY", raising=False)

    result = await posthog_insights.fetch_usage_timeline()
    assert result == []


@pytest.mark.asyncio
async def test_fetch_usage_timeline_with_config(monkeypatch):
    monkeypatch.setenv("POSTHOG_PROJECT_ID", "123")
    monkeypatch.setenv("POSTHOG_API_KEY", "phx_test")
    monkeypatch.setenv("POSTHOG_HOST", "https://app.posthog.test")

    response = MockResponse(
        {
            "results": [
                {
                    "labels": ["2025-10-01", "2025-10-02"],
                    "data": [10, 15],
                }
            ]
        }
    )

    client = MockAsyncClient(response)

    async def fake_client_factory(*args, **kwargs):
        return client

    monkeypatch.setattr(posthog_insights.httpx, "AsyncClient", lambda *args, **kwargs: client)

    result = await posthog_insights.fetch_usage_timeline(2)

    assert result == [
        {"date": "2025-10-01", "value": 10},
        {"date": "2025-10-02", "value": 15},
    ]
    assert client.requests[0]["url"].startswith("https://app.posthog.test/api/projects/123")


@pytest.mark.asyncio
async def test_fetch_endpoint_usage(monkeypatch):
    monkeypatch.setenv("POSTHOG_PROJECT_ID", "123")
    monkeypatch.setenv("POSTHOG_API_KEY", "phx_test")
    monkeypatch.setenv("POSTHOG_HOST", "https://app.posthog.test")

    response = MockResponse(
        {
            "results": [
                {"label": "/api/profile", "data": [2, 3]},
                {"label": "/api/books", "data": [5]},
            ]
        }
    )
    client = MockAsyncClient(response)
    monkeypatch.setattr(posthog_insights.httpx, "AsyncClient", lambda *args, **kwargs: client)

    result = await posthog_insights.fetch_endpoint_usage()
    assert result[0]["endpoint"] == "/api/books"
    assert result[0]["total"] == 5
    assert result[1]["total"] == 5


@pytest.mark.asyncio
async def test_fetch_active_users(monkeypatch):
    monkeypatch.setenv("POSTHOG_PROJECT_ID", "123")
    monkeypatch.setenv("POSTHOG_API_KEY", "phx_test")
    monkeypatch.setenv("POSTHOG_HOST", "https://app.posthog.test")

    response = MockResponse(
        {
            "results": [
                {"labels": ["2025-10-01"], "data": [3]},
            ]
        }
    )
    client = MockAsyncClient(response)
    monkeypatch.setattr(posthog_insights.httpx, "AsyncClient", lambda *args, **kwargs: client)

    result = await posthog_insights.fetch_active_users()
    assert result["daily_active_users"][0]["active_users"] == 3
