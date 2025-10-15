import importlib
import os
from types import SimpleNamespace

import pytest


def reload_module(module_name="backend.posthog_client"):
    module = importlib.import_module(module_name)
    return importlib.reload(module)


def test_capture_api_call_skips_without_key(monkeypatch):
    monkeypatch.delenv("POSTHOG_PROJECT_API_KEY", raising=False)
    monkeypatch.delenv("POSTHOG_HOST", raising=False)
    module = reload_module()
    module.reset_client()

    class Explode:
        def __init__(self, *args, **kwargs):
            raise AssertionError("Posthog should not be instantiated without API key")

    monkeypatch.setattr(module, "Posthog", Explode)
    module.capture_api_call({"endpoint": "/api/profile"})


def test_capture_api_call_sends_event(monkeypatch):
    monkeypatch.setenv("POSTHOG_PROJECT_API_KEY", "phc_test")
    monkeypatch.setenv("POSTHOG_HOST", "https://test.posthog.local")

    captured = {}

    class FakePosthog:
        def __init__(self, project_api_key, host, **kwargs):
            captured["init"] = {
                "project_api_key": project_api_key,
                "host": host,
                "kwargs": kwargs,
            }

        def capture(self, distinct_id, event, properties):
            captured["capture"] = {
                "distinct_id": distinct_id,
                "event": event,
                "properties": properties,
            }

        def close(self):
            captured["closed"] = True

    module = reload_module()
    module.reset_client()
    monkeypatch.setattr(module, "Posthog", FakePosthog)

    payload = {
        "email": "user@example.com",
        "endpoint": "/api/profile",
        "status_code": 200,
        "response_time_ms": 42,
        "request_id": "abc123",
    }

    module.capture_api_call(payload)

    assert captured["init"]["project_api_key"] == "phc_test"
    assert captured["init"]["host"] == "https://test.posthog.local"
    assert captured["capture"]["event"] == "api_request"
    assert captured["capture"]["distinct_id"] == "user@example.com"
    assert captured["capture"]["properties"]["endpoint"] == "/api/profile"
    assert captured["capture"]["properties"]["status_code"] == 200
    assert captured["capture"]["properties"]["$process_person_profile"] is False
