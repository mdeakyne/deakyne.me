from __future__ import annotations

import atexit
import logging
import os
import threading
from typing import Any, Dict, Optional

from posthog import Posthog

logger = logging.getLogger(__name__)

_client_lock = threading.Lock()
_client: Optional[Posthog] = None


def reset_client() -> None:
    """Reset the cached PostHog client (primarily for tests)."""
    global _client
    with _client_lock:
        if _client is not None:
            try:
                _client.close()
            except Exception:  # pragma: no cover - defensive
                pass
        _client = None


def get_posthog_client() -> Optional[Posthog]:
    """Return a cached PostHog client if configured."""
    api_key = os.getenv("POSTHOG_PROJECT_API_KEY")
    if not api_key:
        return None

    host = os.getenv("POSTHOG_HOST", "https://us.i.posthog.com")

    global _client
    with _client_lock:
        if _client is None:
            _client = Posthog(
                project_api_key=api_key,
                host=host,
                disable_geoip=True,
                compress=False,
                max_request_retries=1,
            )
    return _client


def capture_api_call(payload: Dict[str, Any]) -> bool:
    """Send an API call event to PostHog if configured."""
    client = get_posthog_client()
    if client is None:
        return False

    if payload is None:
        payload = {}

    properties = dict(payload)
    event_name = properties.pop("event", "api_request")
    distinct_id = properties.pop("distinct_id", None) or properties.get("email") or properties.get("request_id") or "anonymous"

    properties["$process_person_profile"] = False

    try:
        client.capture(distinct_id, event_name, properties)
        return True
    except Exception as exc:  # pragma: no cover - best effort
        logger.warning("PostHog capture failed: %s", exc)
        return False


def _shutdown() -> None:  # pragma: no cover - process shutdown
    global _client
    with _client_lock:
        if _client is not None:
            try:
                _client.close()
            except Exception:
                pass
            _client = None


atexit.register(_shutdown)
