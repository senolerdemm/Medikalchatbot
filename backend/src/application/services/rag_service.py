from __future__ import annotations

import re

from domain.entities.health_query import RetrievedDocument
from domain.ports.ai.vector_db_service import VectorDBService


class RAGService:
    def __init__(self, *, vector_db: VectorDBService, minimum_score: float = 0.50):
        self.vector_db = vector_db
        self.minimum_score = minimum_score

    async def retrieve(self, query: str, *, k: int = 3) -> list[RetrievedDocument]:
        documents = await self.vector_db.similarity_search(query, k=k)
        query_tokens = self._tokenize(query)
        reranked: list[RetrievedDocument] = []
        for document in documents:
            document_tokens = self._tokenize(f"{document.title} {document.content}")
            overlap = len(query_tokens & document_tokens) / max(len(query_tokens), 1)
            reranked_score = (document.score * 0.55) + (overlap * 0.45)
            reranked.append(
                RetrievedDocument(
                    document_id=document.document_id,
                    title=document.title,
                    content=document.content,
                    source=document.source,
                    metadata=document.metadata,
                    score=reranked_score,
                )
            )
        reranked.sort(key=lambda item: item.score, reverse=True)
        return [document for document in reranked if document.score >= self.minimum_score][:k]

    def _tokenize(self, text: str) -> set[str]:
        normalized = text.lower().translate(
            str.maketrans({"ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u"})
        )
        stopwords = {
            "neden",
            "nedir",
            "olur",
            "icin",
            "gibi",
            "olan",
            "veya",
            "hangi",
            "daha",
            "gore",
            "olanlar",
            "bunu",
            "ile",
            "ama",
            "bir",
            "iki",
            "var",
            "olabilir",
            "sonra",
        }
        base_tokens = {
            token
            for token in re.findall(r"[a-z0-9]{3,}", normalized)
            if len(token) > 2 and token not in stopwords
        }
        expanded_tokens = set(base_tokens)
        for token in base_tokens:
            expanded_tokens.update(self._token_variants(token))
        return expanded_tokens

    def _token_variants(self, token: str) -> set[str]:
        variants = {token}
        suffixes = (
            "imin",
            "im",
            "imda",
            "imde",
            "nin",
            "nun",
            "leri",
            "lari",
            "lar",
            "ler",
            "si",
            "su",
            "u",
            "i",
        )
        if token.startswith("agri"):
            variants.update({"agri", "agrisi"})
        if token.startswith("bulanti"):
            variants.update({"bulanti", "bulantisi"})
        if token.startswith("bas"):
            variants.update({"bas"})
        for suffix in suffixes:
            if token.endswith(suffix) and len(token) - len(suffix) >= 3:
                variants.add(token[: -len(suffix)])
        return {variant for variant in variants if len(variant) >= 3}
