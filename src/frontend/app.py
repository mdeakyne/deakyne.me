from __future__ import annotations

import json
import os
import uuid
from typing import Any, Dict, List

import httpx
from quart import Quart, Response, render_template, request


def _backend_url() -> str:
    return os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")


def _api_key() -> str | None:
    return os.getenv("BACKEND_API_KEY") or os.getenv("API_KEY")


app = Quart(__name__, template_folder="templates", static_folder="static")


@app.before_request
async def ensure_session_id() -> None:  # pragma: no cover - simple cookie helper
    # Use a cookie to keep a stable session id for analytics/back-end correlation
    sid = request.cookies.get("session_id")
    if not sid:
        # Set a temporary value on request context; actual cookie set on first response
        request.ctx.new_session_id = uuid.uuid4().hex


@app.after_request
async def set_session_cookie(
    response: Response,
) -> Response:  # pragma: no cover - trivial
    sid = request.cookies.get("session_id")
    new_sid = getattr(request.ctx, "new_session_id", None)
    if not sid and new_sid:
        response.set_cookie("session_id", new_sid, httponly=False, samesite="Lax")
    return response


@app.get("/")
async def index() -> Response:
    messages: List[Dict[str, str]] = []
    return await render_template("index.html", messages=messages)


@app.post("/chat")
async def chat() -> Response:
    form = await request.form
    user_text = (form.get("user_input") or "").strip()
    if not user_text:
        # No change; re-render current page
        current = form.get("messages") or "[]"
        messages = json.loads(current)
        return await render_template("index.html", messages=messages)

    # Parse prior messages from hidden field
    try:
        messages: List[Dict[str, str]] = json.loads(form.get("messages") or "[]")
    except Exception:
        messages = []

    messages.append({"role": "user", "content": user_text})

    # Call backend synchronously
    api_key = _api_key()
    backend = _backend_url()
    payload: Dict[str, Any] = {
        "messages": messages,
        "session_id": request.cookies.get("session_id", ""),
    }

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(f"{backend}/api/chat", json=payload, headers=headers)
        if r.status_code != 200:
            assistant_text = f"[error {r.status_code}] {r.text}"
        else:
            data = r.json()
            assistant_text = str(data.get("message", ""))

    messages.append({"role": "assistant", "content": assistant_text})

    # Re-render the chat container with updated messages
    return await render_template("index.html", messages=messages)


if __name__ == "__main__":  # pragma: no cover - manual run helper
    # Allows: uv run python -m src.frontend.app
    app.run()
