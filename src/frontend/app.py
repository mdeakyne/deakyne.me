from __future__ import annotations

import json
import os
import uuid
from typing import Any, Dict, List

import httpx
from quart import Quart, Response, render_template, request, make_response


def _backend_url() -> str:
    return os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")


def _api_key() -> str | None:
    return os.getenv("BACKEND_API_KEY") or os.getenv("API_KEY")


app = Quart(__name__, template_folder="templates", static_folder="static")


def _ensure_session_cookie(response: Response) -> Response:
    if not request.cookies.get("session_id"):
        response.set_cookie(
            "session_id", uuid.uuid4().hex, httponly=False, samesite="Lax"
        )
    return response


@app.get("/")
async def index() -> Response:
    messages: List[Dict[str, str]] = []
    content = await render_template(
        "index.html", messages=messages, backend_url=_backend_url()
    )
    resp = await make_response(content)
    return _ensure_session_cookie(resp)


@app.post("/chat")
async def chat() -> Response:
    form = await request.form
    user_text = (form.get("user_input") or "").strip()
    if not user_text:
        # No change; re-render current page
        current = form.get("messages") or "[]"
        messages = json.loads(current)
        content = await render_template(
            "index.html", messages=messages, backend_url=_backend_url()
        )
        resp = await make_response(content)
        return _ensure_session_cookie(resp)

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
    content = await render_template(
        "index.html", messages=messages, backend_url=_backend_url()
    )
    resp = await make_response(content)
    return _ensure_session_cookie(resp)


if __name__ == "__main__":  # pragma: no cover - manual run helper
    # Allows: uv run python -m src.frontend.app
    app.run()
