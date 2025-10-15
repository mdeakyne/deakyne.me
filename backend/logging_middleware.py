from __future__ import annotations

import asyncio
import os
from time import perf_counter
from typing import Callable, ContextManager, Optional
from uuid import uuid4

from fastapi import Request
from jose import jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Capture request/response metadata for analytics."""

    def __init__(
        self,
        app,
        db_factory: Callable[[], ContextManager],
    ):
        super().__init__(app)
        self.db_factory = db_factory

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or getattr(request.state, "request_id", None) or str(uuid4())
        request.state.request_id = request_id

        start_time = perf_counter()
        response: Optional[Response] = None
        try:
            response = await call_next(request)
        finally:
            duration_ms = int((perf_counter() - start_time) * 1000)
            status_code = response.status_code if response else 500
            await self._record_request(request, request_id, duration_ms, status_code)

        if response is None:
            response = Response(status_code=status_code)

        response.headers["X-Request-ID"] = request_id
        return response

    def _extract_email_from_token(self, request: Request) -> Optional[str]:
        """Extract email from JWT token in Authorization header."""
        authorization = request.headers.get("authorization")
        if not authorization:
            return None

        # Extract token from "Bearer <token>" format
        token = authorization[7:] if authorization.startswith("Bearer ") else authorization

        try:
            # Decode JWT without verification (already verified by auth dependency)
            # We just need to extract the email for logging
            jwt_secret = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
            jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")
            payload = jwt.decode(token, jwt_secret, algorithms=[jwt_algorithm])
            return payload.get("sub")
        except Exception:
            # If token is invalid or expired, return None and fall back to anonymous
            return None

    async def _record_request(
        self,
        request: Request,
        request_id: str,
        duration_ms: int,
        status_code: int,
    ) -> None:
        # Try to extract email from JWT token in Authorization header
        email = self._extract_email_from_token(request)
        if not email:
            # Fallback to request.state if set by auth dependency
            email = getattr(request.state, "auth_email", None) or "anonymous"

        endpoint = request.url.path
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        payload = (
            email,
            endpoint,
            ip_address,
            duration_ms,
            status_code,
            user_agent,
            request_id,
        )
        event_payload = {
            "email": email,
            "endpoint": endpoint,
            "ip_address": ip_address,
            "response_time_ms": duration_ms,
            "status_code": status_code,
            "user_agent": user_agent,
            "request_id": request_id,
            "method": request.method,
        }

        def write_log():
            with self.db_factory() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO api_logs (
                        email,
                        endpoint,
                        ip_address,
                        response_time_ms,
                        status_code,
                        user_agent,
                        request_id
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    payload,
                )
                conn.commit()

        await asyncio.to_thread(write_log)
        asyncio.create_task(self._emit_posthog_event(event_payload))

    async def _emit_posthog_event(self, event_payload):
        try:
            from backend.posthog_client import capture_api_call  # type: ignore
        except ImportError:  # pragma: no cover - fallback for local execution
            from posthog_client import capture_api_call  # type: ignore

        def send():
            try:
                capture_api_call(event_payload)
            except Exception:
                pass

        await asyncio.to_thread(send)
