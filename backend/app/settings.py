from __future__ import annotations

from functools import lru_cache
from typing import List, Dict

from pydantic import BaseSettings, Field, validator


class Settings(BaseSettings):
    app_name: str = "deakyne-chat-backend"

    # CORS / Origins
    cors_origins: List[str] = Field(
        default_factory=lambda: [
            "https://deakyne.me",
            "http://localhost:3000",
            "http://localhost:5173",
        ]
    )

    # Auth / API keys
    api_keys_json: str = Field(
        default="{}",
        description="JSON mapping of apiKey -> [scopes]",
        env="API_KEYS_JSON",
    )

    # Oso policy (optional in MVP; falls back to simple scope checks)
    use_oso: bool = Field(default=False, env="USE_OSO")
    oso_policy_path: str | None = Field(default=None, env="OSO_POLICY_PATH")

    # PostHog analytics
    posthog_key: str | None = Field(default=None, env="POSTHOG_KEY")
    posthog_host: str | None = Field(default=None, env="POSTHOG_HOST")

    @validator("cors_origins", pre=True)
    def parse_origins(cls, v):  # type: ignore[override]
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v

    @property
    def api_keys(self) -> Dict[str, List[str]]:
        import json

        try:
            data = json.loads(self.api_keys_json or "{}")
            # Enforce list[str]
            return {k: list(v) for k, v in data.items()}
        except Exception:
            return {}


@lru_cache()
def get_settings() -> Settings:
    return Settings()

