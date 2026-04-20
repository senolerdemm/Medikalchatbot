from __future__ import annotations

from collections import defaultdict

from domain.entities.health_query import HealthQuery
from domain.entities.patient import PatientHistoryEntry, PatientProfile
from domain.ports.repositories.user_history_repository import (
    UserHistoryRepository,
)


class InMemoryUserHistoryRepository(UserHistoryRepository):
    def __init__(self) -> None:
        self._profiles: dict[str, PatientProfile] = {
            "user_001": PatientProfile(
                patient_id="user_001",
                full_name="Senol Erdem",
                age=24,
                chronic_conditions=["alerjik rinit"],
                medications=["gerektiginde antihistaminik"],
                notes="Son aylarda duzensiz uyku bildirimi var.",
            )
        }
        self._entries: dict[str, list[PatientHistoryEntry]] = defaultdict(list)
        self._entries["user_001"] = [
            PatientHistoryEntry(
                entry_type="lab",
                summary="Son kan tahlilinde temel degerler referans araliginda goruldu.",
            ),
            PatientHistoryEntry(
                entry_type="visit",
                summary="Gecen ay kulak burun bogaz polikliniginde alerji takibi yapildi.",
            ),
        ]

    async def get_patient_profile(self, patient_id: str) -> PatientProfile | None:
        return self._profiles.get(patient_id)

    async def list_history_entries(
        self,
        patient_id: str,
        *,
        limit: int = 5,
    ) -> list[PatientHistoryEntry]:
        return self._entries.get(patient_id, [])[:limit]

    async def save_interaction(
        self,
        patient_id: str,
        query: HealthQuery,
        response: str,
    ) -> None:
        self._entries[patient_id].insert(
            0,
            PatientHistoryEntry(
                entry_type="interaction",
                summary=f"Soru: {query.text} | Yanit: {response[:140]}",
            ),
        )
