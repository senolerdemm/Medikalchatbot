from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any

from domain.entities.health_query import RetrievedDocument


class LLMEngine(ABC):
    @abstractmethod
    async def generate_response(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        context_documents: Sequence[RetrievedDocument] | None = None,
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    async def generate_structured_output(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema_hint: str,
        context_documents: Sequence[RetrievedDocument] | None = None,
    ) -> dict[str, Any] | None:
        raise NotImplementedError
