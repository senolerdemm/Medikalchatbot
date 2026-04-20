from __future__ import annotations

from domain.entities.health_query import HealthQuery
from domain.ports.ai.llm_engine import LLMEngine
from domain.ports.ai.vector_db_service import VectorDBService


class InformationAgent:
    def __init__(self, vector_db: VectorDBService, llm_engine: LLMEngine):
        self.vector_db = vector_db
        self.llm_engine = llm_engine

    async def answer_medical_query(
        self,
        query: HealthQuery,
    ) -> dict[str, object]:
        context_docs = await self.vector_db.similarity_search(
            query.text,
            k=3,
        )
        system_prompt = (
            "Sen Turkce medikal bilgi asistanisin. "
            "Sadece verilen baglama dayan, tani koyma, ilac dozu uydurma ve "
            "gerektiginde doktora basvurma uyarisini ekle."
        )
        response = await self.llm_engine.generate_response(
            system_prompt=system_prompt,
            user_prompt=query.text,
            context_documents=context_docs,
        )
        return {
            "message": response,
            "sources": [
                {
                    "title": doc.title,
                    "source": doc.source,
                    "excerpt": doc.excerpt(),
                    "score": round(doc.score, 3),
                }
                for doc in context_docs
            ],
        }
