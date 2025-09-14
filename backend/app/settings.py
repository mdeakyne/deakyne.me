from __future__ import annotations

from functools import lru_cache
from typing import List, Dict

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


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
        validation_alias="API_KEYS_JSON",
    )

    # Oso policy (optional in MVP; falls back to simple scope checks)
    use_oso: bool = Field(default=False, validation_alias="USE_OSO")
    oso_policy_path: str | None = Field(
        default=None, validation_alias="OSO_POLICY_PATH"
    )

    # PostHog analytics
    posthog_key: str | None = Field(default=None, validation_alias="POSTHOG_KEY")
    posthog_host: str | None = Field(default=None, validation_alias="POSTHOG_HOST")

    @field_validator("cors_origins", mode="before")
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
