from __future__ import annotations

from fastapi import APIRouter, Depends

from application.use_cases.process_medical_query import ProcessMedicalQueryUseCase
from presentation.api.schemas.requests import ChatRequest
from presentation.api.schemas.responses import ChatResponse, HealthResponse
from presentation.dependencies import get_process_medical_query_use_case


router = APIRouter(prefix="/api/v1", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    use_case: ProcessMedicalQueryUseCase = Depends(
        get_process_medical_query_use_case
    ),
) -> ChatResponse:
    result = await use_case.execute(user_id=request.user_id, message=request.message)
    return ChatResponse(**result)


@router.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        message="Turkish Medical AI Assistant backend is running.",
    )
