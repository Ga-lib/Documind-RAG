"""
Centralized application settings.

Loads secrets from .env and non-secret configuration from config.yaml,
merging both into a single type-safe Settings object used throughout the app.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Path to this file's directory -> app/config/
CONFIG_DIR = Path(__file__).parent
CONFIG_YAML_PATH = CONFIG_DIR / "config.yaml"


def _load_yaml_config() -> dict:
    """Read config.yaml and return it as a plain dict."""
    if not CONFIG_YAML_PATH.exists():
        raise FileNotFoundError(
            f"config.yaml not found at {CONFIG_YAML_PATH}. "
            "Did you create app/config/config.yaml?"
        )
    with open(CONFIG_YAML_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


class Settings(BaseSettings):
    """
    Application settings, merged from .env (secrets) and config.yaml (tuning).

    Environment variables (from .env) always take priority over config.yaml
    defaults, which lets you override any setting per-environment without
    editing code.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Secrets / environment-specific (from .env) ---
    groq_api_key: str = Field(..., description="Groq API key, required")
    groq_model: str = Field(default="llama-3.3-70b-versatile")

    # --- Paths (can be overridden by .env, default from config.yaml) ---
    vector_db_path: str = Field(default="./data/vector_db")
    upload_path: str = Field(default="./data/uploads")

    # --- Chunking (can be overridden by .env) ---
    chunk_size: int = Field(default=1000)
    chunk_overlap: int = Field(default=200)

    # --- Retrieval ---
    top_k: int = Field(default=4)

    # --- LLM generation ---
    temperature: float = Field(default=0.1)

    # --- Embeddings ---
    embedding_model: str = Field(default="all-MiniLM-L6-v2")

    # --- Populated from config.yaml, not .env ---
    app_name: str = "DocuMind RAG"
    app_version: str = "0.1.0"
    environment: Literal["development", "production"] = "development"
    search_type: Literal["similarity", "mmr"] = "similarity"
    mmr_diversity: float = 0.5
    max_file_size_mb: int = 20
    allowed_extensions: list[str] = [".pdf"]
    log_level: str = "INFO"
    log_format: Literal["json", "text"] = "json"
    collection_name: str = "documind_documents"


@lru_cache
def get_settings() -> Settings:
    """
    Build and cache the Settings object.

    lru_cache ensures the .env + config.yaml files are read only once per
    process, and every part of the app that calls get_settings() shares
    the same Settings instance.
    """
    yaml_config = _load_yaml_config()

    # Flatten the nested YAML into the fields Settings expects.
    overrides = {
        "app_name": yaml_config["app"]["name"],
        "app_version": yaml_config["app"]["version"],
        "environment": yaml_config["app"]["environment"],
        "search_type": yaml_config["retrieval"]["search_type"],
        "mmr_diversity": yaml_config["retrieval"]["mmr_diversity"],
        "max_file_size_mb": yaml_config["upload"]["max_file_size_mb"],
        "allowed_extensions": yaml_config["upload"]["allowed_extensions"],
        "log_level": yaml_config["logging"]["level"],
        "log_format": yaml_config["logging"]["format"],
        "collection_name": yaml_config["vector_store"]["collection_name"],
    }

    # Settings() automatically reads .env first; we then layer in
    # the non-secret YAML values that .env doesn't cover.
    return Settings(**overrides)


# Convenience singleton for simple imports: `from app.config.settings import settings`
settings = get_settings()