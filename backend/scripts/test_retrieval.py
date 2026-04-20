from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Query local Chroma collection.")
    parser.add_argument("query")
    parser.add_argument("--top-k", type=int, default=3)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    from infrastructure.ai.embedding_service import EmbeddingService
    from infrastructure.database.vector.faiss_chroma_db import ChromaVectorDBService

    vector_db = ChromaVectorDBService(embedding_service=EmbeddingService())

    import asyncio

    results = asyncio.run(vector_db.similarity_search(args.query, k=args.top_k))
    if not results:
        print("No documents found.")
        return

    for index, document in enumerate(results, start=1):
        print(f"[{index}] {document.title} | score={document.score:.4f}")
        print(f"source={document.source}")
        print(document.excerpt(320))
        print("-" * 80)


if __name__ == "__main__":
    main()
