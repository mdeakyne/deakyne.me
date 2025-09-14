from __future__ import annotations

from typing import Any, Dict

from .settings import get_settings


class Analytics:
    def __init__(self) -> None:
        self._client = None
        s = get_settings()
        if s.posthog_key and s.posthog_host:
            try:
                import posthog  # type: ignore

                posthog.project_api_key = s.posthog_key
                posthog.host = s.posthog_host
                self._client = posthog
            except Exception:
                self._client = None

    def capture(self, distinct_id: str, event: str, properties: Dict[str, Any] | None = None) -> None:
        if not self._client:
            return
        try:
            self._client.capture(distinct_id=distinct_id, event=event, properties=properties or {})
        except Exception:
            # Best-effort analytics: never break requests
            pass

    def flush(self) -> None:
        if not self._client:
            return
        try:
            self._client.flush()
        except Exception:
            pass


analytics = Analytics()

