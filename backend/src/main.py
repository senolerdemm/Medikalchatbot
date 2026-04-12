from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from presentation.dependencies import get_agent_orchestrator
from application.orchestrator.agent_orchestrator import AgentOrchestrator
from pydantic import BaseModel

# FastAPI uygulaması instance'ı
app = FastAPI(
    title="Turkish Medical AI Assistant API",
    description="Doğal dil tabanlı akıllı tıbbi asistanın LLaMA-3 QLoRA destekli Agent tabanlı Backend'i",
    version="1.0.0"
)

# CORS Ayarları (Frontend'in Backend'e erişebilmesi için gerekli)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Geliştirme ortamı için her yerden erişime izin veriyoruz.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# İstek ve Yanıt DTO'ları
class ChatRequest(BaseModel):
    user_id: str
    message: str

class ChatResponse(BaseModel):
    status: str
    message: str
    handled_by: str
    detected_intent: str

@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    orchestrator: AgentOrchestrator = Depends(get_agent_orchestrator)
):
    """
    Kullanıcının doğal dilde girdiği tıbbi sorguyu alır,
    Orchestrator (DI ile enjekte edilmiştir) üzerinden işler ve yanıt döner.
    """
    try:
        result = await orchestrator.process_query(request.message, request.user_id)
        return ChatResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    """Sistemin ayakta olup olmadığını kontrol eden endpoint."""
    return {"status": "ok", "message": "Turkish Medical AI Assistant Backend is running."}

# Uygulamayı başlatmak için (uvicorn src.main:app --reload)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
