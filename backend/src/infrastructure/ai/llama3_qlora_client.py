from __future__ import annotations

from collections.abc import Sequence

from domain.entities.health_query import RetrievedDocument
from domain.ports.ai.llm_engine import LLMEngine


class Llama3QLoRAClient(LLMEngine):
    """
    Tez prototipinin bu asamasinda gercek model cagrisi yerine, ayni portu
    koruyan guvenli bir adapter iskeleti saglar. Daha sonra QLoRA ile
    egitilen model veya serving katmani buraya baglanabilir.
    """

    async def generate_response(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        context_documents: Sequence[RetrievedDocument] | None = None,
    ) -> str:
        if context_documents:
            best_doc = context_documents[0]
            return (
                f"Sorunuzu dogrulanmis baglama dayanarak yanitliyorum: "
                f"{best_doc.excerpt(220)} "
                f"Bu yanit tani yerine gecmez; belirtileriniz artarsa doktor "
                f"degerlendirmesi alin."
            )

        return (
            "Su an baglam bulunamadigi icin yalnizca genel yonlendirme verebiliyorum. "
            "Semptomlariniz siddetliyse veya ani gelistiyse profesyonel saglik "
            "destegi almaniz gerekir."
        )
