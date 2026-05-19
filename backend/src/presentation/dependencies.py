from functools import lru_cache

from application.agents.appointment_agent import AppointmentAgent
from application.agents.information_agent import InformationAgent
from application.agents.personal_agent import PersonalAgent
from application.orchestrator.agent_orchestrator import AgentOrchestrator
from application.services.appointment_service import AppointmentService
from application.services.auth_service import AuthService
from application.services.intent_classifier import IntentClassifier
from application.services.rag_service import RAGService
from application.services.symptom_guidance_service import SymptomGuidanceService
from application.use_cases.book_hospital_appointment import (
    BookHospitalAppointmentUseCase,
)
from application.use_cases.process_medical_query import ProcessMedicalQueryUseCase
from core.config import get_settings
from fastapi import Header, HTTPException, status
from infrastructure.database.postgres.appointment_db import PostgresAppointmentRepository
from infrastructure.database.postgres.auth_db import PostgresAuthRepository
from infrastructure.database.postgres.user_history_db import (
    PostgresUserHistoryRepository,
)
from infrastructure.ai.embedding_service import EmbeddingService
from infrastructure.ai.llama3_qlora_client import Llama3QLoRAClient
from infrastructure.database.vector.faiss_chroma_db import (
    ChromaVectorDBService,
)
from infrastructure.external_api.hospital_mock_api import HospitalMockAPI


@lru_cache()
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService(model_name=get_settings().embedding_model)


@lru_cache()
def get_llm_engine() -> Llama3QLoRAClient:
    return Llama3QLoRAClient()


@lru_cache()
def get_vector_db() -> ChromaVectorDBService:
    return ChromaVectorDBService(
        embedding_service=get_embedding_service(),
        persist_directory=get_settings().chroma_path,
    )


@lru_cache()
def get_rag_service() -> RAGService:
    return RAGService(vector_db=get_vector_db())


@lru_cache()
def get_symptom_guidance_service() -> SymptomGuidanceService:
    return SymptomGuidanceService()


@lru_cache()
def get_hospital_api() -> HospitalMockAPI:
    return HospitalMockAPI()


@lru_cache()
def get_user_history_repository() -> PostgresUserHistoryRepository:
    return PostgresUserHistoryRepository()


@lru_cache()
def get_auth_repository() -> PostgresAuthRepository:
    return PostgresAuthRepository()


@lru_cache()
def get_auth_service() -> AuthService:
    return AuthService(get_auth_repository())


@lru_cache()
def get_appointment_repository() -> PostgresAppointmentRepository:
    return PostgresAppointmentRepository()


@lru_cache()
def get_appointment_service() -> AppointmentService:
    return AppointmentService(
        hospital_api=get_hospital_api(),
        appointment_repository=get_appointment_repository(),
    )

@lru_cache()
def get_intent_classifier() -> IntentClassifier:
    return IntentClassifier(
        llm_engine=get_llm_engine(),
        user_history_repository=get_user_history_repository(),
    )


@lru_cache()
def get_book_hospital_appointment_use_case() -> BookHospitalAppointmentUseCase:
    return BookHospitalAppointmentUseCase(appointment_service=get_appointment_service())


@lru_cache()
def get_information_agent() -> InformationAgent:
    return InformationAgent(
        rag_service=get_rag_service(),
        llm_engine=get_llm_engine(),
        user_history_repository=get_user_history_repository(),
        symptom_guidance_service=get_symptom_guidance_service(),
    )


@lru_cache()
def get_appointment_agent() -> AppointmentAgent:
    return AppointmentAgent(
        appointment_service=get_appointment_service(),
        user_history_repository=get_user_history_repository(),
        llm_engine=get_llm_engine(),
        symptom_guidance_service=get_symptom_guidance_service(),
    )


@lru_cache()
def get_personal_agent() -> PersonalAgent:
    return PersonalAgent(
        user_history_repository=get_user_history_repository(),
        appointment_repository=get_appointment_repository(),
        llm_engine=get_llm_engine(),
    )


@lru_cache()
def get_agent_orchestrator() -> AgentOrchestrator:
    return AgentOrchestrator(
        information_agent=get_information_agent(),
        appointment_agent=get_appointment_agent(),
        personal_agent=get_personal_agent(),
        intent_classifier=get_intent_classifier(),
    )


@lru_cache()
def get_process_medical_query_use_case() -> ProcessMedicalQueryUseCase:
    return ProcessMedicalQueryUseCase(
        orchestrator=get_agent_orchestrator(),
        user_history_repository=get_user_history_repository(),
    )


async def get_current_user(authorization: str | None = Header(default=None)):
    token = (authorization or "").removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Oturum bulunamadı.",
        )
    user = await get_auth_service().get_current_user(token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz veya süresi dolmuş oturum.",
        )
    return user
