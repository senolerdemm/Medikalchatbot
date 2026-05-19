from __future__ import annotations

from typing import Any

from application.agents.appointment_agent import AppointmentAgent
from application.agents.information_agent import InformationAgent
from application.agents.personal_agent import PersonalAgent
from application.services.intent_classifier import IntentClassifier
from domain.entities.health_query import HealthQuery, QueryIntent


class AgentOrchestrator:
    def __init__(
        self,
        *,
        information_agent: InformationAgent,
        appointment_agent: AppointmentAgent,
        personal_agent: PersonalAgent,
        intent_classifier: IntentClassifier,
    ):
        self.information_agent = information_agent
        self.appointment_agent = appointment_agent
        self.personal_agent = personal_agent
        self.intent_classifier = intent_classifier

    async def process_query(self, query: HealthQuery) -> dict[str, Any]:
        intent = await self.intent_classifier.classify(query)
        query.intent = intent

        if intent is QueryIntent.APPOINTMENT:
            agent_result = await self.appointment_agent.handle_appointment_request(query)
            handled_by = "Randevu Ajanı"
        elif intent is QueryIntent.PERSONAL_HISTORY:
            agent_result = await self.personal_agent.handle_history_query(query)
            handled_by = "Kişisel Geçmiş Ajanı"
        else:
            agent_result = await self.information_agent.answer_medical_query(query)
            handled_by = "Bilgi Ajanı"

        return {
            "status": "success",
            "message": str(agent_result["message"]),
            "handled_by": handled_by,
            "detected_intent": intent.value,
            "risk_level": query.assess_risk().value,
            "sources": agent_result.get("sources", []),
            "ui_action": agent_result.get("ui_action", "none"),
            "payload": agent_result.get("payload", {}),
        }
