from __future__ import annotations

import json
import os
import uuid
from typing import Any, Dict, List, AsyncIterator

import httpx
from html import escape
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


def _format_sse(event: str, data: str) -> bytes:
    return f"event: {event}\n" f"data: {data}\n\n".encode()


async def _proxy_backend_sse(session_id: str | None) -> AsyncIterator[bytes]:
    backend = _backend_url()
    api_key = _api_key()
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    params = {"session_id": session_id or ""}
    # pass through optional user prompt
    user_q = request.args.get("q")
    if user_q:
        params["q"] = user_q

    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream(
            "GET", f"{backend}/api/chat/stream", headers=headers, params=params
        ) as r:
            event = None
            data_lines: list[str] = []
            async for raw_line in r.aiter_lines():
                if raw_line == "":
                    # dispatch
                    if event:
                        data = "\n".join(data_lines)
                        if event == "token":
                            try:
                                payload = json.loads(data)
                                text = escape(str(payload.get("text", "")))
                                yield _format_sse("token", text)
                            except Exception:
                                yield _format_sse("token", escape(data))
                        elif event in {"done", "error"}:
                            yield _format_sse(event, data)
                    # reset
                    event = None
                    data_lines = []
                    continue
                if raw_line.startswith("event:"):
                    event = raw_line.split(":", 1)[1].strip()
                elif raw_line.startswith("data:"):
                    data_lines.append(raw_line.split(":", 1)[1].lstrip())


@app.get("/sse")
async def sse() -> Response:
    sid = request.cookies.get("session_id")
    gen = _proxy_backend_sse(sid)
    return Response(gen, mimetype="text/event-stream")


@app.post("/chat/start")
async def chat_start() -> Response:
    form = await request.form
    user_text = (form.get("user_input") or "").strip()
    try:
        messages: List[Dict[str, str]] = json.loads(form.get("messages") or "[]")
    except Exception:
        messages = []

    if user_text:
        messages.append({"role": "user", "content": user_text})

    # Render chat with streaming section for assistant response
    content = await render_template(
        "index.html",
        messages=messages,
        backend_url=_backend_url(),
        stream_query=user_text,
    )
    resp = await make_response(content)
    return _ensure_session_cookie(resp)


if __name__ == "__main__":  # pragma: no cover - manual run helper
    # Allows: uv run python -m src.frontend.app
    app.run()
