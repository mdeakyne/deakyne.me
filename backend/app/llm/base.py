from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator, List, Dict, Any


Message = Dict[str, Any]


class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, messages: List[Message]) -> str:
        ...

    @abstractmethod
    async def generate_stream(self, messages: List[Message]) -> AsyncIterator[str]:
        ...

