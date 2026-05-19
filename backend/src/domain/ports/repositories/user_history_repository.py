from __future__ import annotations

from abc import ABC, abstractmethod

from domain.entities.health_query import HealthQuery
from domain.entities.patient import ConversationMessage, PatientHistoryEntry, PatientProfile


class UserHistoryRepository(ABC):
    @abstractmethod
    async def get_patient_profile(self, patient_id: str) -> PatientProfile | None:
        raise NotImplementedError

    @abstractmethod
    async def list_history_entries(
        self,
        patient_id: str,
        *,
        limit: int = 5,
    ) -> list[PatientHistoryEntry]:
        raise NotImplementedError

    @abstractmethod
    async def save_interaction(
        self,
        patient_id: str,
        query: HealthQuery,
        response: str,
        conversation_id: str,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def list_recent_messages(
        self,
        *,
        conversation_id: str,
        limit: int = 6,
    ) -> list[ConversationMessage]:
        raise NotImplementedError

    @abstractmethod
    async def ensure_conversation(
        self,
        *,
        patient_id: str,
        conversation_id: str | None = None,
        title: str | None = None,
    ) -> str:
        raise NotImplementedError
