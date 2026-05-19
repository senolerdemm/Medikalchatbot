from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from application.services.rag_service import RAGService
from infrastructure.ai.embedding_service import EmbeddingService
from infrastructure.database.vector.faiss_chroma_db import ChromaVectorDBService


def main() -> None:
    queries_path = PROJECT_ROOT / "data" / "rag" / "processed" / "retrieval_eval_queries.json"
    queries = json.loads(queries_path.read_text(encoding="utf-8"))
    rag_service = RAGService(
        vector_db=ChromaVectorDBService(embedding_service=EmbeddingService())
    )
    for query in queries:
        docs = __import__("asyncio").run(rag_service.retrieve(query, k=3))
        print(f"\nQUERY: {query}")
        for index, doc in enumerate(docs, start=1):
            print(f"  [{index}] {doc.title} | {doc.score:.4f} | {doc.source}")


if __name__ == "__main__":
    main()
