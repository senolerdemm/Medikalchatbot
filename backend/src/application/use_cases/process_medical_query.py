from __future__ import annotations

from uuid import uuid4

from application.orchestrator.agent_orchestrator import AgentOrchestrator
from domain.entities.health_query import HealthQuery
from domain.ports.repositories.user_history_repository import UserHistoryRepository


class ProcessMedicalQueryUseCase:
    def __init__(
        self,
        orchestrator: AgentOrchestrator,
        user_history_repository: UserHistoryRepository,
    ):
        self.orchestrator = orchestrator
        self.user_history_repository = user_history_repository

    async def execute(
        self,
        *,
        user_id: str,
        message: str,
        conversation_id: str | None = None,
    ) -> dict[str, object]:
        conversation_id = await self.user_history_repository.ensure_conversation(
            patient_id=user_id,
            conversation_id=conversation_id or str(uuid4()),
            title=message[:80],
        )
        query = HealthQuery(
            patient_id=user_id,
            text=message,
            conversation_id=conversation_id,
        )
        result = await self.orchestrator.process_query(query)
        await self.user_history_repository.save_interaction(
            user_id,
            query,
            str(result["message"]),
            conversation_id,
        )
        result["conversation_id"] = conversation_id
        return result
