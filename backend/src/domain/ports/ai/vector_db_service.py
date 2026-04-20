from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping

from domain.entities.health_query import RetrievedDocument


class VectorDBService(ABC):
    @abstractmethod
    async def similarity_search(
        self,
        query: str,
        *,
        k: int = 3,
        filters: Mapping[str, str] | None = None,
    ) -> list[RetrievedDocument]:
        raise NotImplementedError
