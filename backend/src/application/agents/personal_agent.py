from __future__ import annotations

from domain.entities.health_query import HealthQuery
from domain.ports.ai.llm_engine import LLMEngine
from domain.ports.repositories.user_history_repository import (
    UserHistoryRepository,
)


class PersonalAgent:
    def __init__(
        self,
        user_history_repository: UserHistoryRepository,
        llm_engine: LLMEngine,
    ):
        self.user_history_repository = user_history_repository
        self.llm_engine = llm_engine

    async def handle_history_query(
        self,
        query: HealthQuery,
    ) -> dict[str, object]:
        profile = await self.user_history_repository.get_patient_profile(
            query.patient_id
        )
        entries = await self.user_history_repository.list_history_entries(
            query.patient_id,
            limit=5,
        )
        history_context = "\n".join(
            f"- {entry.summary} ({entry.recorded_at.strftime('%d.%m.%Y')})"
            for entry in entries
        )
        user_prompt = (
            f"Hasta profili: {profile.summary() if profile else 'Kayit bulunamadi.'}\n"
            f"Son gecmis kayitlari:\n{history_context or '- Kayit bulunamadi.'}\n"
            f"Soru: {query.text}"
        )
        response = await self.llm_engine.generate_response(
            system_prompt=(
                "Sen hastanin kendi gecmisini ozetleyen, tani koymayan ve "
                "gerekirse doktor kontrolu oneren bir yardimci asistansin."
            ),
            user_prompt=user_prompt,
        )
        return {
            "message": response,
            "sources": [],
        }
