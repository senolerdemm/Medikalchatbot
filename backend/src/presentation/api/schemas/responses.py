from pydantic import BaseModel, Field


class SourceDocumentResponse(BaseModel):
    title: str
    source: str
    excerpt: str
    score: float = Field(ge=0.0)
    url: str | None = None


class ChatResponse(BaseModel):
    status: str
    message: str
    handled_by: str
    detected_intent: str
    risk_level: str
    ui_action: str
    payload: dict = Field(default_factory=dict)
    conversation_id: str
    sources: list[SourceDocumentResponse] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str
    message: str


class UserResponse(BaseModel):
    patient_id: str
    email: str
    full_name: str


class SessionResponse(BaseModel):
    token: str
    expires_at: str
    user: UserResponse


class AppointmentSlotResponse(BaseModel):
    slot_id: str
    hospital_name: str
    city: str
    physician_name: str
    specialty: str
    start_at: str
    is_available: bool


class AppointmentBookingResponse(BaseModel):
    booking_id: str
    status: str
    slot: AppointmentSlotResponse
