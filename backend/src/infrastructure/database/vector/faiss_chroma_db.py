from __future__ import annotations

import re
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")

from core.config import get_settings
from domain.entities.health_query import RetrievedDocument
from domain.ports.ai.vector_db_service import VectorDBService
from infrastructure.ai.embedding_service import EmbeddingService


class ChromaVectorDBService(VectorDBService):
    """
    Raporla uyumlu RAG adapteri.

    Birincil yol, Turkish Hospital Medical Articles corpus'u uzerinde uretilmis
    FAISS IndexFlatIP + chunks.parquet artefactlerini kullanir. Chroma yalnizca
    eski demo verisi/cache ve development fallback olarak kalir.
    """

    def __init__(
        self,
        *,
        embedding_service: EmbeddingService,
        persist_directory: str | None = None,
        collection_name: str = "medical_articles",
    ) -> None:
        self.settings = get_settings()
        self.embedding_service = embedding_service
        default_directory = (
            Path(self.settings.chroma_path)
        )
        self.persist_directory = Path(persist_directory or default_directory)
        self.collection_name = collection_name
        self._attempted_external_import = False
        self._external_faiss_index = None
        self._external_chunks = None
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
                title="Reflü için genel hasta bilgilendirmesi",
                source="verified-hospital-content",
                content=(
                    "Reflü mide içeriğinin yemek borusuna geri kaçmasıyla ilişkilidir. "
                    "Mide yanması, ağza acı su gelmesi, ekşime ve yatınca artan yakınmalar "
                    "görülebilir. Yağlı yemekler, büyük porsiyonlar ve geç saatlerde yemek yemek "
                    "şikayetleri artırabilir."
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
            RetrievedDocument(
                document_id="doc-004",
                title="Diyabet için genel hasta bilgilendirmesi",
                source="verified-hospital-content",
                content=(
                    "Diyabette sık idrara çıkma, çok su içme, halsizlik ve kan şekeri "
                    "yüksekliği görülebilir. Düzenli takip, beslenme düzeni ve hekim "
                    "önerilerine uyum önemlidir."
                ),
            ),
            RetrievedDocument(
                document_id="doc-005",
                title="Anksiyete için genel hasta bilgilendirmesi",
                source="verified-hospital-content",
                content=(
                    "Anksiyete çarpıntı hissi, iç sıkıntısı, huzursuzluk ve uyku sorunları "
                    "ile kendini gösterebilir. Şikayetlerin şiddetine göre psikiyatrik değerlendirme "
                    "ve psikososyal destek gerekebilir."
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
        external_results = self._external_faiss_search(query=query, k=k, filters=filters)
        if external_results:
            if self._has_lexical_support(query=query, documents=external_results):
                return external_results
            keyword_results = self._external_keyword_search(
                query=query,
                k=k,
                filters=filters,
            )
            if keyword_results:
                return keyword_results

        collection = self._get_collection()
        if collection is None or collection.count() == 0:
            if self.settings.app_env == "development" and self.settings.allow_vector_fallback:
                return self._fallback_search(query=query, k=k, filters=filters)
            return []

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

    def backend_status(self) -> dict[str, Any]:
        index_path = self.settings.external_rag_index_path
        chunks_path = self.settings.external_rag_chunks_path
        index_file = Path(index_path) if index_path else None
        chunks_file = Path(chunks_path) if chunks_path else None
        status: dict[str, Any] = {
            "primary": "FAISS IndexFlatIP",
            "embedding_model": self.embedding_service.model_name,
            "embedding_dimension": self.embedding_service.dimension_hint(),
            "faiss_index_path": str(index_file) if index_file else None,
            "chunks_path": str(chunks_file) if chunks_file else None,
            "faiss_configured": bool(index_file and chunks_file),
            "faiss_files_exist": bool(
                index_file
                and chunks_file
                and index_file.exists()
                and chunks_file.exists()
            ),
        }
        if not status["faiss_files_exist"]:
            status["active"] = "Chroma/fallback"
            status["document_count"] = self._chroma_count()
            return status
        status["faiss_dimension"] = self.settings.external_rag_index_dimension
        status["document_count"] = self.settings.external_rag_document_count
        status["active"] = "FAISS IndexFlatIP"
        return status

    def _get_collection(self):
        try:
            import chromadb

            self.persist_directory.mkdir(parents=True, exist_ok=True)
            client = chromadb.PersistentClient(path=str(self.persist_directory))
            collection = client.get_or_create_collection(name=self.collection_name)
            if (
                collection.count() == 0
                and not self._attempted_external_import
                and self.settings.external_rag_chunks_path
                and Path(self.settings.external_rag_chunks_path).exists()
            ):
                self._attempted_external_import = True
                try:
                    self.import_chunks_from_parquet(
                        self.settings.external_rag_chunks_path,
                        reset=False,
                    )
                    collection = client.get_or_create_collection(name=self.collection_name)
                except Exception:
                    pass
            return collection
        except Exception:
            return None

    def _external_faiss_search(
        self,
        *,
        query: str,
        k: int,
        filters: Mapping[str, str] | None,
    ) -> list[RetrievedDocument]:
        index_path = self.settings.external_rag_index_path
        chunks_path = self.settings.external_rag_chunks_path
        if not index_path or not chunks_path:
            return []
        index_file = Path(index_path)
        chunks_file = Path(chunks_path)
        if not index_file.exists() or not chunks_file.exists():
            return []

        index_dimension_hint = self.settings.external_rag_index_dimension
        embedding_dimension_hint = self.embedding_service.dimension_hint()
        if (
            index_dimension_hint
            and embedding_dimension_hint
            and index_dimension_hint != embedding_dimension_hint
        ):
            return self._external_keyword_search(query=query, k=k, filters=filters)

        try:
            import faiss
            import numpy as np
            import pandas as pd
        except Exception:
            return []

        if not self.embedding_service.has_real_model():
            return self._external_keyword_search(query=query, k=k, filters=filters)

        if self._external_faiss_index is None:
            self._external_faiss_index = faiss.read_index(str(index_file))
        if self._external_chunks is None:
            self._external_chunks = pd.read_parquet(chunks_file)

        dataframe = self._external_chunks
        if dataframe is None or dataframe.empty:
            return []

        candidate_k = min(max(k * 4, 20), len(dataframe))
        query_vector = self.embedding_service.embed_text(query)
        index_dimension = int(getattr(self._external_faiss_index, "d", 0) or 0)
        if index_dimension and len(query_vector) != index_dimension:
            return self._external_keyword_search(query=query, k=k, filters=filters)

        query_array = np.array([query_vector], dtype="float32")
        distances, indices = self._external_faiss_index.search(query_array, candidate_k)

        retrieved: list[RetrievedDocument] = []
        for distance, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(dataframe):
                continue
            row = dataframe.iloc[int(idx)]
            metadata = self._metadata_from_row(row.to_dict())
            if filters and any(str(metadata.get(key, "")) != str(value) for key, value in filters.items()):
                continue
            score = 1 / (1 + float(distance)) if distance >= 0 else 0.0
            retrieved.append(
                RetrievedDocument(
                    document_id=str(row.get("chunk_id", idx)),
                    title=str(row.get("article_title", "Harici Tıbbi Makale")),
                    content=str(row.get("chunk_text", "")),
                    source=str(metadata.get("source", "external-rag")),
                    metadata=metadata,
                    score=score,
                )
            )
            if len(retrieved) >= k:
                break
        return retrieved

    def _chroma_count(self) -> int:
        collection = self._get_collection()
        if collection is None:
            return 0
        try:
            return int(collection.count())
        except Exception:
            return 0

    def _has_lexical_support(
        self,
        *,
        query: str,
        documents: list[RetrievedDocument],
    ) -> bool:
        tokens = self._query_tokens(query)
        if not tokens:
            return True
        searchable_tokens = tokens[:8]
        for document in documents:
            haystack = f"{document.title} {document.content}".casefold()
            if any(token.casefold() in haystack for token in searchable_tokens):
                return True
        return False

    def _external_keyword_search(
        self,
        *,
        query: str,
        k: int,
        filters: Mapping[str, str] | None,
    ) -> list[RetrievedDocument]:
        dataframe = self._external_chunks
        chunks_path = self.settings.external_rag_chunks_path
        if dataframe is None:
            if not chunks_path or not Path(chunks_path).exists():
                return []
            try:
                import pandas as pd

                dataframe = pd.read_parquet(chunks_path)
                self._external_chunks = dataframe
            except Exception:
                return []
        if dataframe is None or dataframe.empty:
            return []

        tokens = self._query_tokens(query)
        if not tokens:
            return []

        candidate_mask = None
        text_series = dataframe.get("chunk_text")
        title_series = dataframe.get("article_title")
        if text_series is None:
            return []

        searchable = text_series.fillna("").astype(str)
        if title_series is not None:
            searchable = (
                title_series.fillna("").astype(str)
                + " "
                + searchable
            )
        searchable = searchable.str.casefold()

        for token in tokens[:8]:
            token_mask = searchable.str.contains(re.escape(token), regex=True, na=False)
            candidate_mask = token_mask if candidate_mask is None else (candidate_mask | token_mask)

        if candidate_mask is None:
            return []

        candidates = dataframe.loc[candidate_mask].head(4000)
        scored_rows: list[tuple[float, int, int, int, Mapping[str, Any]]] = []
        for position, (_, row) in enumerate(candidates.iterrows()):
            row_dict = row.to_dict()
            metadata = self._metadata_from_row(row_dict)
            if filters and any(str(metadata.get(key, "")) != str(value) for key, value in filters.items()):
                continue

            title = str(row_dict.get("article_title", "")).casefold()
            content = str(row_dict.get("chunk_text", "")).casefold()
            title_hits = sum(1 for token in tokens if token in title)
            content_hits = sum(1 for token in tokens if token in content)
            if title_hits == 0 and content_hits == 0:
                continue
            score = min(1.0, (title_hits * 2.5 + content_hits) / max(len(tokens), 1))
            scored_rows.append((score, title_hits, content_hits, -position, row_dict))

        scored_rows.sort(key=lambda item: (item[0], item[1], item[2], item[3]), reverse=True)
        retrieved: list[RetrievedDocument] = []
        deferred_duplicates: list[RetrievedDocument] = []
        seen_sources: set[str] = set()
        for score, _, _, _, row in scored_rows[: max(k * 20, 100)]:
            metadata = self._metadata_from_row(row)
            source_key = str(metadata.get("url") or metadata.get("source") or row.get("article_title", ""))
            document = RetrievedDocument(
                document_id=str(row.get("chunk_id", len(retrieved))),
                title=str(row.get("article_title", "Harici Tıbbi Makale")),
                content=str(row.get("chunk_text", "")),
                source=str(metadata.get("source", "external-rag")),
                metadata={**metadata, "retrieval_mode": "external-keyword-fallback"},
                score=score,
            )
            if source_key in seen_sources:
                deferred_duplicates.append(document)
                continue
            seen_sources.add(source_key)
            retrieved.append(document)
            if len(retrieved) >= k:
                break

        for document in deferred_duplicates:
            if len(retrieved) >= k:
                break
            retrieved.append(document)
        return retrieved

    def _query_tokens(self, query: str) -> list[str]:
        normalized = query.casefold()
        raw_tokens = re.findall(r"[0-9a-zçğıöşü]{3,}", normalized)
        stop_words = {
            "bir",
            "icin",
            "için",
            "nedir",
            "neden",
            "nedeni",
            "nasıl",
            "nasil",
            "olur",
            "olan",
            "olarak",
            "hangi",
            "miyim",
            "misin",
            "midir",
            "var",
            "yok",
        }
        seen: set[str] = set()
        tokens: list[str] = []
        for token in raw_tokens:
            if token in stop_words or token in seen:
                continue
            seen.add(token)
            tokens.append(token)
            for variant in self._token_variants(token):
                if variant in stop_words or variant in seen:
                    continue
                seen.add(variant)
                tokens.append(variant)
        return tokens

    def _token_variants(self, token: str) -> list[str]:
        variants: list[str] = []
        if token.startswith("refl"):
            variants.extend(["reflü", "reflu"])
        suffixes = (
            "ünün",
            "unun",
            "ının",
            "inin",
            "nün",
            "nun",
            "nın",
            "nin",
            "leri",
            "ları",
            "lar",
            "ler",
            "dan",
            "den",
            "tan",
            "ten",
            "dır",
            "dir",
            "dur",
            "dür",
            "sı",
            "si",
            "su",
            "sü",
        )
        for suffix in suffixes:
            if token.endswith(suffix) and len(token) - len(suffix) >= 3:
                variants.append(token[: -len(suffix)])
        return variants

    def import_chunks_from_parquet(
        self,
        parquet_path: str | Path,
        *,
        reset: bool = False,
        batch_size: int = 64,
    ) -> int:
        import chromadb
        import pandas as pd

        parquet_file = Path(parquet_path)
        if not parquet_file.exists():
            raise FileNotFoundError(f"Parquet dosyasi bulunamadi: {parquet_file}")

        dataframe = pd.read_parquet(parquet_file)
        required_columns = {"chunk_id", "chunk_text"}
        if not required_columns.issubset(set(dataframe.columns)):
            raise ValueError(
                "Parquet dosyasinda en az chunk_id ve chunk_text kolonlari olmali."
            )

        self.persist_directory.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(self.persist_directory))
        if reset:
            try:
                client.delete_collection(name=self.collection_name)
            except Exception:
                pass
        collection = client.get_or_create_collection(name=self.collection_name)

        records = dataframe.fillna("").to_dict(orient="records")
        for start in range(0, len(records), batch_size):
            batch = records[start : start + batch_size]
            ids = [str(row["chunk_id"]) for row in batch]
            documents = [str(row["chunk_text"]) for row in batch]
            metadatas = [self._metadata_from_row(row) for row in batch]
            embeddings = self.embedding_service.embed_texts(
                [
                    f"{metadata.get('title', '')}\n{document}".strip()
                    for metadata, document in zip(metadatas, documents)
                ]
            )
            collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings,
            )
        self._attempted_external_import = True
        return len(records)

    def _metadata_from_row(self, row: Mapping[str, Any]) -> dict[str, str]:
        title = str(row.get("article_title", "")).strip() or "Harici Tıbbi Makale"
        hospital = str(row.get("hospital", "")).strip()
        url = str(row.get("url", "")).strip()
        source = url or hospital or "external-rag"
        metadata = {
            "title": title,
            "source": source,
        }
        if hospital:
            metadata["hospital"] = hospital
        if url:
            metadata["url"] = url
        return metadata

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
