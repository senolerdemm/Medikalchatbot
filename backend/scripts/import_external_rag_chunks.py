from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, "backend/src")

from core.config import get_settings
from presentation.dependencies import get_vector_db


def main() -> None:
    settings = get_settings()
    default_path = settings.external_rag_chunks_path or ""

    parser = argparse.ArgumentParser(
        description="Harici chunks.parquet dosyasini mevcut Chroma koleksiyonuna aktarir."
    )
    parser.add_argument(
        "--parquet-path",
        default=default_path,
        help="chunks.parquet dosyasinin yolu",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Var olan koleksiyonu silip yeniden olustur",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=256,
        help="Embedding ve upsert batch boyutu",
    )
    args = parser.parse_args()

    if not args.parquet_path:
        raise SystemExit(
            "Parquet yolu bulunamadi. --parquet-path verin veya EXTERNAL_RAG_CHUNKS_PATH ayarlayin."
        )

    parquet_path = Path(args.parquet_path).expanduser().resolve()
    imported_count = get_vector_db().import_chunks_from_parquet(
        parquet_path,
        reset=args.reset,
        batch_size=args.batch_size,
    )
    print(f"{imported_count} chunk Chroma koleksiyonuna aktarıldı: {parquet_path}")


if __name__ == "__main__":
    main()
