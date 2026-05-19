from __future__ import annotations

from sqlalchemy import desc, select

from domain.entities.health_query import HealthQuery
from domain.entities.patient import ConversationMessage, PatientHistoryEntry, PatientProfile
from domain.ports.repositories.user_history_repository import UserHistoryRepository
from infrastructure.database.postgres.base import session_scope
from infrastructure.database.postgres.models import (
    ConversationModel,
    MessageModel,
    PatientHistoryEntryModel,
    PatientProfileModel,
    UserModel,
)


class PostgresUserHistoryRepository(UserHistoryRepository):
    async def get_patient_profile(self, patient_id: str) -> PatientProfile | None:
        with session_scope() as session:
            user = session.get(UserModel, patient_id)
            profile = session.get(PatientProfileModel, patient_id)
            if user is None:
                return None
            if profile is None:
                return PatientProfile(patient_id=user.id, full_name=user.full_name)
            return PatientProfile(
                patient_id=user.id,
                full_name=user.full_name,
                age=profile.age,
                chronic_conditions=list(profile.chronic_conditions or []),
                medications=list(profile.medications or []),
                notes=profile.notes,
                city=profile.city,
            )

    async def list_history_entries(
        self,
        patient_id: str,
        *,
        limit: int = 5,
    ) -> list[PatientHistoryEntry]:
        with session_scope() as session:
            rows = session.scalars(
                select(PatientHistoryEntryModel)
                .where(PatientHistoryEntryModel.user_id == patient_id)
                .order_by(desc(PatientHistoryEntryModel.recorded_at))
                .limit(limit)
            ).all()
            return [
                PatientHistoryEntry(
                    entry_type=row.entry_type,
                    summary=row.summary,
                    metadata={str(key): str(value) for key, value in (row.metadata_json or {}).items()},
                    recorded_at=row.recorded_at,
                    entry_id=row.id,
                )
                for row in rows
            ]

    async def ensure_conversation(
        self,
        *,
        patient_id: str,
        conversation_id: str | None = None,
        title: str | None = None,
    ) -> str:
        with session_scope() as session:
            if conversation_id:
                existing = session.get(ConversationModel, conversation_id)
                if existing is not None:
                    return existing.id
            conversation = ConversationModel(
                id=conversation_id,
                user_id=patient_id,
                title=title,
            )
            session.add(conversation)
            session.flush()
            return conversation.id

    async def list_recent_messages(
        self,
        *,
        conversation_id: str,
        limit: int = 6,
    ) -> list[ConversationMessage]:
        with session_scope() as session:
            rows = session.scalars(
                select(MessageModel)
                .where(MessageModel.conversation_id == conversation_id)
                .order_by(desc(MessageModel.created_at))
                .limit(limit)
            ).all()
            messages = [
                ConversationMessage(
                    role=row.role,
                    content=row.content,
                    created_at=row.created_at,
                    message_id=row.id,
                )
                for row in reversed(rows)
            ]
            return messages

    async def save_interaction(
        self,
        patient_id: str,
        query: HealthQuery,
        response: str,
        conversation_id: str,
    ) -> None:
        with session_scope() as session:
            conversation = session.get(ConversationModel, conversation_id)
            if conversation is None:
                conversation = ConversationModel(
                    id=conversation_id,
                    user_id=patient_id,
                    title=query.text[:80],
                )
                session.add(conversation)
                session.flush()
            session.add_all(
                [
                    MessageModel(
                        conversation_id=conversation.id,
                        role="user",
                        content=query.text,
                    ),
                    MessageModel(
                        conversation_id=conversation.id,
                        role="assistant",
                        content=response,
                    ),
                    PatientHistoryEntryModel(
                        user_id=patient_id,
                        entry_type="interaction",
                        summary=f"Soru: {query.text} | Yanit: {response[:180]}",
                        metadata_json={"conversation_id": conversation.id},
                    ),
                ]
            )
