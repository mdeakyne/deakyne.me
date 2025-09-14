from __future__ import annotations

import asyncio
from typing import AsyncIterator, List, Dict, Any

from .base import LLMProvider, Message


class EchoProvider(LLMProvider):
    async def generate(self, messages: List[Message]) -> str:
        user = _last_user_content(messages)
        # Simple echo with a small prefix to simulate processing
        await asyncio.sleep(0)
        return f"You said: {user}"

    async def generate_stream(self, messages: List[Message]) -> AsyncIterator[str]:
        user = _last_user_content(messages)
        text = f"You said: {user}"
        # Chunk into small pieces to simulate token streaming
        chunk_size = 8
        for i in range(0, len(text), chunk_size):
            await asyncio.sleep(0)
            yield text[i : i + chunk_size]


def _last_user_content(messages: List[Dict[str, Any]]) -> str:
    for m in reversed(messages):
        if m.get("role") == "user":
            return str(m.get("content", "")).strip()
    return ""

