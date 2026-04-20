from pydantic import BaseModel, Field


class SourceDocumentResponse(BaseModel):
    title: str
    source: str
    excerpt: str
    score: float = Field(ge=0.0)


class ChatResponse(BaseModel):
    status: str
    message: str
    handled_by: str
    detected_intent: str
    risk_level: str
    sources: list[SourceDocumentResponse] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str
    message: str
