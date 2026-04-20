from functools import lru_cache

from application.agents.appointment_agent import AppointmentAgent
from application.agents.information_agent import InformationAgent
from application.agents.personal_agent import PersonalAgent
from application.orchestrator.agent_orchestrator import AgentOrchestrator
from application.use_cases.book_hospital_appointment import (
    BookHospitalAppointmentUseCase,
)
from application.use_cases.process_medical_query import ProcessMedicalQueryUseCase
from infrastructure.ai.embedding_service import EmbeddingService
from infrastructure.ai.llama3_qlora_client import Llama3QLoRAClient
from infrastructure.database.postgres.user_history_db import (
    InMemoryUserHistoryRepository,
)
from infrastructure.database.vector.faiss_chroma_db import (
    ChromaVectorDBService,
)
from infrastructure.external_api.hospital_mock_api import HospitalMockAPI


@lru_cache()
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()


@lru_cache()
def get_llm_engine() -> Llama3QLoRAClient:
    return Llama3QLoRAClient()


@lru_cache()
def get_vector_db() -> ChromaVectorDBService:
    return ChromaVectorDBService(embedding_service=get_embedding_service())


@lru_cache()
def get_hospital_api() -> HospitalMockAPI:
    return HospitalMockAPI()


@lru_cache()
def get_user_history_repository() -> InMemoryUserHistoryRepository:
    return InMemoryUserHistoryRepository()


@lru_cache()
def get_book_hospital_appointment_use_case() -> BookHospitalAppointmentUseCase:
    return BookHospitalAppointmentUseCase(hospital_api=get_hospital_api())


@lru_cache()
def get_information_agent() -> InformationAgent:
    return InformationAgent(
        vector_db=get_vector_db(),
        llm_engine=get_llm_engine(),
    )


@lru_cache()
def get_appointment_agent() -> AppointmentAgent:
    return AppointmentAgent(
        book_appointment=get_book_hospital_appointment_use_case()
    )


@lru_cache()
def get_personal_agent() -> PersonalAgent:
    return PersonalAgent(
        user_history_repository=get_user_history_repository(),
        llm_engine=get_llm_engine(),
    )


@lru_cache()
def get_agent_orchestrator() -> AgentOrchestrator:
    return AgentOrchestrator(
        information_agent=get_information_agent(),
        appointment_agent=get_appointment_agent(),
        personal_agent=get_personal_agent(),
        user_history_repository=get_user_history_repository(),
    )


@lru_cache()
def get_process_medical_query_use_case() -> ProcessMedicalQueryUseCase:
    return ProcessMedicalQueryUseCase(orchestrator=get_agent_orchestrator())
