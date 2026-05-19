from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, status

from application.services.auth_service import AuthService
from domain.entities.patient import PatientAccount
from presentation.api.schemas.requests import LoginRequest, RegisterRequest
from presentation.api.schemas.responses import SessionResponse, UserResponse
from presentation.dependencies import get_auth_service, get_current_user


router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=SessionResponse)
async def login(
    request: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> SessionResponse:
    session = await auth_service.login(request.email, request.password)
    if session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Gecersiz e-posta veya sifre.")
    return SessionResponse(
        token=session.token,
        expires_at=session.expires_at.isoformat(),
        user=UserResponse(
            patient_id=session.patient.patient_id,
            email=session.patient.email,
            full_name=session.patient.full_name,
        ),
    )


@router.post("/register", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> SessionResponse:
    try:
        session = await auth_service.register(
            email=request.email,
            password=request.password,
            full_name=request.full_name,
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    return SessionResponse(
        token=session.token,
        expires_at=session.expires_at.isoformat(),
        user=UserResponse(
            patient_id=session.patient.patient_id,
            email=session.patient.email,
            full_name=session.patient.full_name,
        ),
    )


@router.post("/logout")
async def logout(
    authorization: str | None = Header(default=None),
    auth_service: AuthService = Depends(get_auth_service),
) -> dict[str, str]:
    token = (authorization or "").removeprefix("Bearer ").strip()
    if token:
        await auth_service.logout(token)
    return {"status": "success", "message": "Oturum kapatildi."}


@router.get("/me", response_model=UserResponse)
async def me(
    current_user: PatientAccount = Depends(get_current_user),
) -> UserResponse:
    return UserResponse(
        patient_id=current_user.patient_id,
        email=current_user.email,
        full_name=current_user.full_name,
    )
