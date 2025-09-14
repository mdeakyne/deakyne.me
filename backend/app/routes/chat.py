from __future__ import annotations

import json
import time
from typing import AsyncIterator, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, validator
from starlette.responses import StreamingResponse
from starlette.status import HTTP_400_BAD_REQUEST

from ..analytics import analytics
from ..auth import Principal, require_scope
from ..llm.echo import EchoProvider


router = APIRouter(prefix="/api/chat", tags=["chat"])


class Message(BaseModel):
    role: str
    content: str

    @validator("role")
    def valid_role(cls, v: str) -> str:  # type: ignore[override]
        if v not in {"user", "assistant", "system"}:
            raise ValueError("role must be one of: user, assistant, system")
        return v


class ChatRequest(BaseModel):
    messages: List[Message] = Field(..., min_items=1)
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    id: str
    message: str
    latency_ms: int


provider = EchoProvider()


@router.post("", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    principal: Principal = Depends(require_scope("chat:write")),
):
    start = time.perf_counter()
    last_user = next((m.content for m in reversed(body.messages) if m.role == "user"), "").strip()
    if not last_user:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Last user message is empty")

    analytics.capture(body.session_id or principal.key, "chat_start", {"mode": "sync"})
    text = await provider.generate([m.dict() for m in body.messages])
    analytics.capture(body.session_id or principal.key, "chat_complete", {"mode": "sync"})
    latency_ms = int((time.perf_counter() - start) * 1000)
    return ChatResponse(id=body.session_id or "", message=text, latency_ms=latency_ms)


def _sse_event(event: str, data: str) -> bytes:
    return f"event: {event}\ndata: {data}\n\n".encode()


@router.get("/stream")
async def chat_stream(
    session_id: str = Query(""),
    principal: Principal = Depends(require_scope("chat:write")),
):
    # For MVP, stream an echo of a synthetic message noting the session
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": f"Stream session: {session_id or 'anonymous'}"},
    ]

    async def event_generator() -> AsyncIterator[bytes]:
        analytics.capture(session_id or principal.key, "chat_start", {"mode": "sse"})
        try:
            async for chunk in provider.generate_stream(messages):
                analytics.capture(session_id or principal.key, "chat_token", {"n": len(chunk)})
                yield _sse_event("token", json.dumps({"text": chunk}))
            analytics.capture(session_id or principal.key, "chat_complete", {"mode": "sse"})
            yield _sse_event("done", json.dumps({"ok": True}))
        except Exception as e:  # pragma: no cover - best effort
            yield _sse_event("error", json.dumps({"error": str(e)}))

    return StreamingResponse(event_generator(), media_type="text/event-stream")

