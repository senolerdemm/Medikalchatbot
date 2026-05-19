from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from infrastructure.ai.embedding_service import EmbeddingService
from infrastructure.database.vector.faiss_chroma_db import ChromaVectorDBService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Query external FAISS-backed RAG output.")
    parser.add_argument("query")
    parser.add_argument("--top-k", type=int, default=3)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    vector_db = ChromaVectorDBService(embedding_service=EmbeddingService())
    results = vector_db._external_faiss_search(query=args.query, k=args.top_k, filters=None)
    print(f"count={len(results)}")
    for index, document in enumerate(results, start=1):
        print(f"[{index}] {document.title} | score={document.score:.4f} | {document.source}")
        print(document.excerpt(220))
        print("-" * 80)


if __name__ == "__main__":
    main()
