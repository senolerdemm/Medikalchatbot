from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = Field(default="development", alias="APP_ENV")
    database_url: str = Field(
        default="postgresql+psycopg://medical_user:medical_password@127.0.0.1:5432/medical_chatbot",
        alias="DATABASE_URL",
    )
    session_secret: str = Field(
        default="medical-chatbot-demo-secret",
        alias="SESSION_SECRET",
    )
    session_ttl_hours: int = Field(default=72, alias="SESSION_TTL_HOURS")
    chroma_path: str = Field(
        default="backend/data/rag/chroma",
        alias="CHROMA_PATH",
    )
    allow_vector_fallback: bool = Field(
        default=True,
        alias="ALLOW_VECTOR_FALLBACK",
    )
    embedding_model: str = Field(
        default="sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
        alias="EMBEDDING_MODEL",
    )
    llm_base_url: str = Field(
        default="http://127.0.0.1:11434",
        alias="LLM_BASE_URL",
    )
    llm_provider: str = Field(
        default="ollama",
        alias="LLM_PROVIDER",
    )
    llm_model: str = Field(
        default="medassist-finetuned",
        alias="LLM_MODEL",
    )
    llm_adapter_path: str | None = Field(
        default=None,
        alias="LLM_ADAPTER_PATH",
    )
    llm_base_model_path: str | None = Field(
        default=None,
        alias="LLM_BASE_MODEL_PATH",
    )
    llm_device: str = Field(
        default="auto",
        alias="LLM_DEVICE",
    )
    llm_max_new_tokens: int = Field(
        default=96,
        alias="LLM_MAX_NEW_TOKENS",
    )
    llm_timeout_seconds: int = Field(
        default=120,
        alias="LLM_TIMEOUT_SECONDS",
    )
    llm_context_window: int = Field(
        default=2048,
        alias="LLM_CONTEXT_WINDOW",
    )
    llm_keep_alive: str = Field(
        default="30m",
        alias="LLM_KEEP_ALIVE",
    )
    llm_temperature: float = Field(
        default=0.2,
        alias="LLM_TEMPERATURE",
    )
    external_rag_chunks_path: str | None = Field(
        default=None,
        alias="EXTERNAL_RAG_CHUNKS_PATH",
    )
    external_rag_index_path: str | None = Field(
        default=None,
        alias="EXTERNAL_RAG_INDEX_PATH",
    )
    external_rag_index_dimension: int | None = Field(
        default=None,
        alias="EXTERNAL_RAG_INDEX_DIMENSION",
    )
    external_rag_document_count: int | None = Field(
        default=None,
        alias="EXTERNAL_RAG_DOCUMENT_COUNT",
    )

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parents[2] / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @model_validator(mode="after")
    def normalize_localhost_urls(self) -> "Settings":
        project_root = Path(__file__).resolve().parents[3]
        if "@localhost:" in self.database_url:
            self.database_url = self.database_url.replace("@localhost:", "@127.0.0.1:")
        if self.llm_base_url.startswith("http://localhost:"):
            self.llm_base_url = self.llm_base_url.replace("http://localhost:", "http://127.0.0.1:")
        chroma_path = Path(self.chroma_path)
        if not chroma_path.is_absolute():
            self.chroma_path = str((project_root / chroma_path).resolve())
        if self.llm_adapter_path:
            adapter_path = Path(self.llm_adapter_path)
            if not adapter_path.is_absolute():
                self.llm_adapter_path = str((project_root / adapter_path).resolve())
        if self.llm_base_model_path:
            base_model_path = Path(self.llm_base_model_path)
            if base_model_path.exists() and not base_model_path.is_absolute():
                self.llm_base_model_path = str((project_root / base_model_path).resolve())
        embedding_model_path = Path(self.embedding_model)
        if embedding_model_path.exists() and not embedding_model_path.is_absolute():
            self.embedding_model = str((project_root / embedding_model_path).resolve())
        if self.external_rag_chunks_path:
            external_chunks_path = Path(self.external_rag_chunks_path)
            if not external_chunks_path.is_absolute():
                self.external_rag_chunks_path = str((project_root / external_chunks_path).resolve())
        if self.external_rag_index_path:
            external_index_path = Path(self.external_rag_index_path)
            if not external_index_path.is_absolute():
                self.external_rag_index_path = str((project_root / external_index_path).resolve())
        return self


@lru_cache()
def get_settings() -> Settings:
    return Settings()
