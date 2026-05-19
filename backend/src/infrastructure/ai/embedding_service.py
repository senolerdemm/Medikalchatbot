from __future__ import annotations

import hashlib
import os
from functools import lru_cache
from pathlib import Path


os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

DEFAULT_EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
KNOWN_EMBEDDING_DIMENSIONS = {
    "sentence-transformers/paraphrase-multilingual-mpnet-base-v2": 768,
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2": 384,
}


class EmbeddingService:
    """
    RAG pipeline'i icin sentence-transformers tabanli embedding servisi sunar.
    Model henuz kurulmamissa deterministic fallback ile gelistirme akisini
    bloke etmez.
    """

    def __init__(
        self,
        *,
        model_name: str = DEFAULT_EMBEDDING_MODEL,
        fallback_dimensions: int = 32,
    ) -> None:
        self.model_name = model_name
        self.fallback_dimensions = fallback_dimensions

    def embed_text(self, text: str) -> list[float]:
        model = self._get_model()
        if model is None:
            return self._fallback_embed(text)
        vector = model.encode(text, normalize_embeddings=True)
        return [float(value) for value in vector.tolist()]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        model = self._get_model()
        if model is None:
            return [self._fallback_embed(text) for text in texts]
        vectors = model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return [[float(value) for value in vector.tolist()] for vector in vectors]

    def dimension_hint(self) -> int | None:
        if self.model_name in KNOWN_EMBEDDING_DIMENSIONS:
            return KNOWN_EMBEDDING_DIMENSIONS[self.model_name]
        if Path(self.model_name).exists():
            return None
        return None

    def has_real_model(self) -> bool:
        return self._get_model() is not None

    def _fallback_embed(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        return [
            int.from_bytes(digest[index : index + 4], "big") / 2**32
            for index in range(0, self.fallback_dimensions * 4, 4)
        ]

    @lru_cache(maxsize=1)
    def _get_model(self):
        try:
            from sentence_transformers import SentenceTransformer

            local_model_path = self._resolve_local_model_path()
            if local_model_path is not None:
                return SentenceTransformer(str(local_model_path), local_files_only=True)

            try:
                return SentenceTransformer(self.model_name, local_files_only=True)
            except Exception:
                return SentenceTransformer(self.model_name)
        except Exception:
            return None

    def _resolve_local_model_path(self) -> Path | None:
        if Path(self.model_name).exists():
            return Path(self.model_name)

        model_cache_name = f"models--{self.model_name.replace('/', '--')}"
        cache_root = Path.home() / ".cache" / "huggingface" / "hub" / model_cache_name
        ref_file = cache_root / "refs" / "main"
        snapshots_dir = cache_root / "snapshots"
        if ref_file.exists():
            revision = ref_file.read_text(encoding="utf-8").strip()
            candidate = snapshots_dir / revision
            if candidate.exists():
                return candidate
        if snapshots_dir.exists():
            snapshots = sorted(
                [path for path in snapshots_dir.iterdir() if path.is_dir()],
                reverse=True,
            )
            if snapshots:
                return snapshots[0]
        return None
