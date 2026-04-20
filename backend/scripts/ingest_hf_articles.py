from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

from datasets import load_dataset


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest Hugging Face medical articles into local Chroma DB."
    )
    parser.add_argument(
        "--dataset",
        default="alibayram/turkish-hospital-medical-articles",
    )
    parser.add_argument("--token", default=os.getenv("HF_TOKEN"))
    parser.add_argument(
        "--split",
        default="all",
        help="Dataset split name or 'all' to ingest every hospital split.",
    )
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument(
        "--limit-per-split",
        type=int,
        default=None,
        help="Maximum number of rows to ingest from each split.",
    )
    parser.add_argument("--chunk-size", type=int, default=1200)
    parser.add_argument("--chunk-overlap", type=int, default=200)
    parser.add_argument(
        "--collection",
        default="medical_articles",
    )
    parser.add_argument(
        "--persist-dir",
        default="backend/data/rag/chroma",
    )
    parser.add_argument(
        "--processed-output",
        default="backend/data/rag/processed/ingested_chunks.jsonl",
    )
    parser.add_argument(
        "--embedding-model",
        default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete and recreate the Chroma collection before ingesting.",
    )
    return parser.parse_args()


def clean_text(text: str) -> str:
    text = text or ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    if chunk_size <= overlap:
        raise ValueError("chunk_size must be greater than overlap")
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


def detect_field(row: dict, candidates: tuple[str, ...], default: str = "") -> str:
    lowered = {str(key).lower(): key for key in row}
    for candidate in candidates:
        matched_key = lowered.get(candidate.lower())
        if matched_key is not None and row.get(matched_key):
            return str(row.get(matched_key, default))
    return default


def row_to_chunks(
    row: dict,
    row_index: int,
    *,
    split_name: str,
    chunk_size: int,
    chunk_overlap: int,
) -> list[dict]:
    title = clean_text(
        detect_field(row, ("title", "headline", "article_title"), default="Untitled")
    )
    content = clean_text(
        detect_field(
            row,
            ("content", "text", "body", "article", "article_text", "description"),
        )
    )
    if len(content) < 300:
        return []

    category = clean_text(detect_field(row, ("category", "department", "specialty")))
    url = clean_text(detect_field(row, ("url", "link", "source_url")))
    source = (
        clean_text(detect_field(row, ("source",)))
        or f"huggingface_medical_articles::{split_name}"
    )
    publish_date = clean_text(detect_field(row, ("publish_date",)))
    update_date = clean_text(detect_field(row, ("update_date",)))
    scrape_date = clean_text(detect_field(row, ("scrape_date",)))

    chunks = []
    for chunk_index, chunk in enumerate(
        chunk_text(content, chunk_size=chunk_size, overlap=chunk_overlap)
    ):
        chunks.append(
            {
                "doc_id": f"{split_name}_doc_{row_index}",
                "chunk_id": f"{split_name}_doc_{row_index}_chunk_{chunk_index}",
                "title": title,
                "text": f"{title}\n\n{chunk}",
                "source": source,
                "category": category or split_name,
                "hospital_split": split_name,
                "url": url,
                "publish_date": publish_date,
                "update_date": update_date,
                "scrape_date": scrape_date,
            }
        )
    return chunks


def main() -> None:
    args = parse_args()

    from chromadb import PersistentClient

    from infrastructure.ai.embedding_service import EmbeddingService

    dataset = load_dataset(args.dataset, token=args.token)
    all_chunks: list[dict] = []
    selected_splits = (
        list(dataset.keys()) if args.split == "all" else [args.split]
    )
    total_rows = 0
    for split_name in selected_splits:
        split = dataset[split_name]
        split_rows = 0
        for row_index, row in enumerate(split):
            if args.limit and total_rows >= args.limit:
                break
            if args.limit_per_split and split_rows >= args.limit_per_split:
                break
            all_chunks.extend(
                row_to_chunks(
                    row,
                    row_index,
                    split_name=split_name,
                    chunk_size=args.chunk_size,
                    chunk_overlap=args.chunk_overlap,
                )
            )
            total_rows += 1
            split_rows += 1
        if args.limit and total_rows >= args.limit:
            break

    persist_dir = Path(args.persist_dir)
    persist_dir.mkdir(parents=True, exist_ok=True)

    processed_output = Path(args.processed_output)
    processed_output.parent.mkdir(parents=True, exist_ok=True)
    with processed_output.open("w", encoding="utf-8") as file_handle:
        for chunk in all_chunks:
            file_handle.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    client = PersistentClient(path=str(persist_dir))
    if args.reset:
        try:
            client.delete_collection(args.collection)
        except Exception:
            pass
    collection = client.get_or_create_collection(name=args.collection)

    embedding_service = EmbeddingService(model_name=args.embedding_model)
    texts = [chunk["text"] for chunk in all_chunks]
    embeddings = embedding_service.embed_texts(texts)

    batch_size = 64
    for start in range(0, len(all_chunks), batch_size):
        end = start + batch_size
        batch = all_chunks[start:end]
        collection.add(
            ids=[chunk["chunk_id"] for chunk in batch],
            documents=[chunk["text"] for chunk in batch],
            metadatas=[
                {
                    "doc_id": chunk["doc_id"],
                    "title": chunk["title"],
                    "source": chunk["source"],
                    "category": chunk["category"],
                    "hospital_split": chunk["hospital_split"],
                    "url": chunk["url"],
                    "publish_date": chunk["publish_date"],
                    "update_date": chunk["update_date"],
                    "scrape_date": chunk["scrape_date"],
                }
                for chunk in batch
            ],
            embeddings=embeddings[start:end],
        )

    print(f"Ingest completed. Collection count: {collection.count()}")
    print(f"Processed chunks saved to: {processed_output}")
    print(f"Chroma path: {persist_dir}")


if __name__ == "__main__":
    main()
