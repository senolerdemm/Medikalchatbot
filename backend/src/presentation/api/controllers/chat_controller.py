from __future__ import annotations

from fastapi import APIRouter, Depends

from application.use_cases.process_medical_query import ProcessMedicalQueryUseCase
from domain.entities.patient import PatientAccount
from presentation.api.schemas.requests import ChatRequest
from presentation.api.schemas.responses import ChatResponse, HealthResponse
from presentation.dependencies import (
    get_current_user,
    get_process_medical_query_use_case,
    get_vector_db,
)


router = APIRouter(prefix="/api/v1", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    current_user: PatientAccount = Depends(get_current_user),
    use_case: ProcessMedicalQueryUseCase = Depends(
        get_process_medical_query_use_case
    ),
) -> ChatResponse:
    result = await use_case.execute(
        user_id=current_user.patient_id,
        message=request.message,
        conversation_id=request.conversation_id,
    )
    return ChatResponse(**result)


@router.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check() -> HealthResponse:
    vector_status = get_vector_db().backend_status()
    vector_count = int(vector_status.get("document_count") or 0)
    return HealthResponse(
        status="ok",
        message=(
            "Türkçe Dil Tabanlı Akıllı Tıbbi Asistan backend'i çalışıyor. "
            f"RAG backend: {vector_status.get('active')}. "
            f"Vektör belge sayısı: {vector_count}"
        ),
    )
