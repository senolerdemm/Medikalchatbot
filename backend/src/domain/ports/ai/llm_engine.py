from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

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
