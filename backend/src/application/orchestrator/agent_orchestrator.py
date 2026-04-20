from __future__ import annotations

from typing import Any

from application.agents.appointment_agent import AppointmentAgent
from application.agents.information_agent import InformationAgent
from application.agents.personal_agent import PersonalAgent
from domain.entities.health_query import HealthQuery, QueryIntent
from domain.ports.repositories.user_history_repository import (
    UserHistoryRepository,
)


class AgentOrchestrator:
    def __init__(
        self,
        *,
        information_agent: InformationAgent,
        appointment_agent: AppointmentAgent,
        personal_agent: PersonalAgent,
        user_history_repository: UserHistoryRepository,
    ):
        self.information_agent = information_agent
        self.appointment_agent = appointment_agent
        self.personal_agent = personal_agent
        self.user_history_repository = user_history_repository

    async def process_query(self, query: HealthQuery) -> dict[str, Any]:
        intent = self._analyze_intent(query)
        query.intent = intent

        if intent is QueryIntent.APPOINTMENT:
            agent_result = await self.appointment_agent.handle_appointment_request(query)
            handled_by = "Appointment Agent"
        elif intent is QueryIntent.PERSONAL_HISTORY:
            agent_result = await self.personal_agent.handle_history_query(query)
            handled_by = "Personal Agent"
        else:
            agent_result = await self.information_agent.answer_medical_query(query)
            handled_by = "Information Agent"

        response_text = str(agent_result["message"])
        await self.user_history_repository.save_interaction(
            query.patient_id,
            query,
            response_text,
        )
        return {
            "status": "success",
            "message": response_text,
            "handled_by": handled_by,
            "detected_intent": intent.value,
            "risk_level": query.assess_risk().value,
            "sources": agent_result.get("sources", []),
        }

    def _analyze_intent(self, query: HealthQuery) -> QueryIntent:
        text = query.normalized_text()
        if any(
            keyword in text
            for keyword in ("randevu", "muayene", "doktor", "slot", "tarih")
        ):
            return QueryIntent.APPOINTMENT
        if any(
            keyword in text
            for keyword in ("gecmis", "gecmiste", "tahlil", "sonuc", "benim", "kaydim")
        ):
            return QueryIntent.PERSONAL_HISTORY
        return QueryIntent.INFORMATION
