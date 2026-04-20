from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    user_id: str = Field(..., examples=["user_001"])
    message: str = Field(..., min_length=2, max_length=2_000)
