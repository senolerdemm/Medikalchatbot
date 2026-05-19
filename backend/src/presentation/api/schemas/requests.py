from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=2, max_length=2_000)
    conversation_id: str | None = Field(default=None)


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=128)
    password: str = Field(..., min_length=3, max_length=64)


class RegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=3, max_length=128)
    email: str = Field(..., min_length=5, max_length=128)
    password: str = Field(..., min_length=3, max_length=64)


class AppointmentSearchRequest(BaseModel):
    specialty: str = Field(..., min_length=3)
    city: str | None = None
    hospital_name: str | None = None
    physician_name: str | None = None
    preferred_date: str | None = None
