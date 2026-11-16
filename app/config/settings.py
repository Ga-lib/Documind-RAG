"""Centralized, validated application settings loaded from YAML and .env."""

from functools import lru_cache
from pathlib import Path
import os
from typing import Literal

import yaml
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

CONFIG_YAML_PATH = Path(__file__).parent / "config.yaml"


def _load_yaml_config() -> dict:
    if not CONFIG_YAML_PATH.is_file():
        raise FileNotFoundError(f"Configuration file not found: {CONFIG_YAML_PATH}")
    with CONFIG_YAML_PATH.open("r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream) or {}
    if not isinstance(data, dict):
        raise ValueError("config.yaml must contain a YAML mapping")
    return data


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    groq_api_key: str = Field(..., min_length=1, description="Groq API key")
    documind_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"
    vector_db_path: str = "./data/vector_db"
    upload_path: str = "./data/uploads"
    chunking_strategy: Literal["recursive", "fixed"] = "recursive"
    chunk_size: int = Field(default=1000, gt=0)
    chunk_overlap: int = Field(default=200, ge=0)
    top_k: int = Field(default=4, ge=1, le=20)
    temperature: float = Field(default=0.1, ge=0, le=2)
    max_tokens: int = Field(default=1024, gt=0)
    llm_timeout_seconds: int = Field(default=30, gt=0)
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_batch_size: int = Field(default=32, gt=0)
    app_name: str = "DocuMind RAG"
    app_version: str = "0.1.0"
    environment: Literal["development", "production"] = "development"
    search_type: Literal["similarity", "mmr"] = "similarity"
    mmr_diversity: float = Field(default=0.5, ge=0, le=1)
    max_file_size_mb: int = Field(default=20, gt=0)
    allowed_extensions: list[str] = [".pdf"]
    log_level: str = "INFO"
    log_format: Literal["json", "text"] = "json"
    collection_name: str = "documind_documents"

    @model_validator(mode="after")
    def validate_runtime_settings(self):
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        if self.documind_api_key and len(self.documind_api_key) < 24:
            raise ValueError("DOCUMIND_API_KEY must contain at least 24 characters")
        if self.environment == "production" and not self.documind_api_key:
            raise ValueError("DOCUMIND_API_KEY is required when APP environment is production")
        return self


@lru_cache
def get_settings() -> Settings:
    config = _load_yaml_config()

    # YAML supplies defaults; deployment environment variables always win.
    def configured(name: str, fallback):
        return os.getenv(name, fallback)
    app = config.get("app") or {}
    llm = config.get("llm") or {}
    embeddings = config.get("embeddings") or {}
    chunking = config.get("chunking") or {}
    retrieval = config.get("retrieval") or {}
    vector_store = config.get("vector_store") or {}
    upload = config.get("upload") or {}
    logging_config = config.get("logging") or {}
    extensions = configured("ALLOWED_EXTENSIONS", upload.get("allowed_extensions", [".pdf"]))
    if isinstance(extensions, str):
        extensions = [item.strip().lower() for item in extensions.split(",") if item.strip()]

    return Settings(
        app_name=configured("APP_NAME", app.get("name", "DocuMind RAG")),
        app_version=configured("APP_VERSION", app.get("version", "0.1.0")),
        environment=configured("ENVIRONMENT", app.get("environment", "development")),
        groq_model=configured("GROQ_MODEL", llm.get("model", "llama-3.3-70b-versatile")),
        temperature=configured("LLM_TEMPERATURE", llm.get("temperature", 0.1)),
        max_tokens=configured("LLM_MAX_TOKENS", llm.get("max_tokens", 1024)),
        llm_timeout_seconds=configured("LLM_TIMEOUT_SECONDS", llm.get("timeout_seconds", 30)),
        embedding_model=configured("EMBEDDING_MODEL", embeddings.get("model_name", "all-MiniLM-L6-v2")),
        embedding_batch_size=configured("EMBEDDING_BATCH_SIZE", embeddings.get("batch_size", 32)),
        chunking_strategy=configured("CHUNKING_STRATEGY", chunking.get("strategy", "recursive")),
        chunk_size=configured("CHUNK_SIZE", chunking.get("chunk_size", 1000)),
        chunk_overlap=configured("CHUNK_OVERLAP", chunking.get("chunk_overlap", 200)),
        top_k=configured("TOP_K", retrieval.get("top_k", 4)),
        search_type=configured("SEARCH_TYPE", retrieval.get("search_type", "similarity")),
        mmr_diversity=configured("MMR_DIVERSITY", retrieval.get("mmr_diversity", 0.5)),
        collection_name=configured("COLLECTION_NAME", vector_store.get("collection_name", "documind_documents")),
        vector_db_path=configured("VECTOR_DB_PATH", vector_store.get("persist_directory", "./data/vector_db")),
        upload_path=configured("UPLOAD_PATH", upload.get("directory", "./data/uploads")),
        max_file_size_mb=configured("MAX_FILE_SIZE_MB", upload.get("max_file_size_mb", 20)),
        allowed_extensions=extensions,
        log_level=configured("LOG_LEVEL", logging_config.get("level", "INFO")),
        log_format=configured("LOG_FORMAT", logging_config.get("format", "json")),
    )


settings = get_settings()
