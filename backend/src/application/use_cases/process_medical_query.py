from __future__ import annotations

from application.orchestrator.agent_orchestrator import AgentOrchestrator
from domain.entities.health_query import HealthQuery


class ProcessMedicalQueryUseCase:
    def __init__(self, orchestrator: AgentOrchestrator):
        self.orchestrator = orchestrator

    async def execute(self, *, user_id: str, message: str) -> dict[str, object]:
        query = HealthQuery(patient_id=user_id, text=message)
        return await self.orchestrator.process_query(query)
