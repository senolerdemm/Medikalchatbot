from __future__ import annotations

from abc import ABC, abstractmethod

from domain.entities.health_query import HealthQuery
from domain.entities.patient import PatientHistoryEntry, PatientProfile


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
    ) -> None:
        raise NotImplementedError
