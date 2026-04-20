from __future__ import annotations

from pathlib import Path
from collections.abc import Mapping

from domain.entities.health_query import RetrievedDocument
from domain.ports.ai.vector_db_service import VectorDBService
from infrastructure.ai.embedding_service import EmbeddingService


class ChromaVectorDBService(VectorDBService):
    """
    Gercek ingestion tamamlandiginda Chroma collection'ini kullanir. Collection
    henuz yoksa gelistirme akisini durdurmamak icin ornek dokumanlarla fallback
    retrieval sunar.
    """

    def __init__(
        self,
        *,
        embedding_service: EmbeddingService,
        persist_directory: str | None = None,
        collection_name: str = "medical_articles",
    ) -> None:
        self.embedding_service = embedding_service
        default_directory = (
            Path(__file__).resolve().parents[4] / "data" / "rag" / "chroma"
        )
        self.persist_directory = Path(persist_directory or default_directory)
        self.collection_name = collection_name
        self._bootstrap_documents = [
            RetrievedDocument(
                document_id="doc-001",
                title="Bas agrisi icin genel hasta bilgilendirmesi",
                source="verified-hospital-content",
                content=(
                    "Bas agrisi sivi kaybi, stres, uyku duzensizligi veya enfeksiyon "
                    "gibi nedenlerle ortaya cikabilir. Ani ve siddetli bas agrisi "
                    "yasaniyorsa acil degerlendirme gerekir."
                ),
            ),
            RetrievedDocument(
                document_id="doc-002",
                title="Dahiliye randevusu hangi durumlarda uygundur",
                source="verified-hospital-content",
                content=(
                    "Ates, halsizlik, sindirim sistemi sikayetleri ve genel ic hastaliklari "
                    "belirtilerinde ilk basamak olarak dahiliye poliklinigi tercih edilebilir."
                ),
            ),
            RetrievedDocument(
                document_id="doc-003",
                title="Alerjik rinit hasta bilgilendirmesi",
                source="verified-hospital-content",
                content=(
                    "Alerjik rinitte burun akintisi, hapsirma ve kasinti gorulebilir. "
                    "Tetikleyicilerden kacınma ve doktorun onerdigi tedavi plani onemlidir."
                ),
            ),
        ]

    async def similarity_search(
        self,
        query: str,
        *,
        k: int = 3,
        filters: Mapping[str, str] | None = None,
    ) -> list[RetrievedDocument]:
        collection = self._get_collection()
        if collection is None or collection.count() == 0:
            return self._fallback_search(query=query, k=k, filters=filters)

        query_embedding = self.embedding_service.embed_text(query)
        chroma_filters = dict(filters) if filters else None
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            where=chroma_filters,
            include=["documents", "metadatas", "distances"],
        )
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]
        ids = results.get("ids", [[]])[0]

        retrieved: list[RetrievedDocument] = []
        for document_id, content, metadata, distance in zip(
            ids,
            documents,
            metadatas,
            distances,
        ):
            metadata = metadata or {}
            score = 1 / (1 + float(distance))
            retrieved.append(
                RetrievedDocument(
                    document_id=str(document_id),
                    title=str(metadata.get("title", "Untitled Medical Article")),
                    content=str(content),
                    source=str(metadata.get("source", self.collection_name)),
                    metadata={str(key): str(value) for key, value in metadata.items()},
                    score=score,
                )
            )
        return retrieved

    def _get_collection(self):
        try:
            import chromadb

            self.persist_directory.mkdir(parents=True, exist_ok=True)
            client = chromadb.PersistentClient(path=str(self.persist_directory))
            return client.get_or_create_collection(name=self.collection_name)
        except Exception:
            return None

    def _fallback_search(
        self,
        *,
        query: str,
        k: int,
        filters: Mapping[str, str] | None,
    ) -> list[RetrievedDocument]:
        query_embedding = self.embedding_service.embed_text(query)
        scored_documents: list[RetrievedDocument] = []
        for document in self._bootstrap_documents:
            if filters and any(
                document.metadata.get(key) != value for key, value in filters.items()
            ):
                continue
            doc_embedding = self.embedding_service.embed_text(
                f"{document.title}\n{document.content}"
            )
            score = self._cosine_similarity(query_embedding, doc_embedding)
            scored_documents.append(
                RetrievedDocument(
                    document_id=document.document_id,
                    title=document.title,
                    content=document.content,
                    source=document.source,
                    metadata=document.metadata,
                    score=score,
                )
            )
        scored_documents.sort(key=lambda item: item.score, reverse=True)
        return scored_documents[:k]

    def _cosine_similarity(
        self,
        left: list[float],
        right: list[float],
    ) -> float:
        numerator = sum(l * r for l, r in zip(left, right))
        left_norm = sum(l * l for l in left) ** 0.5
        right_norm = sum(r * r for r in right) ** 0.5
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return numerator / (left_norm * right_norm)
