"""Tests for deployment configuration precedence and request bounds."""

import pytest
from pydantic import ValidationError

from app.config.settings import get_settings
from app.models.schemas import AskRequest


def test_environment_overrides_yaml_defaults(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    monkeypatch.setenv("GROQ_MODEL", "openai/gpt-oss-120b")
    monkeypatch.setenv("CHUNK_SIZE", "800")
    monkeypatch.setenv("VECTOR_DB_PATH", "/tmp/documind-test-vectors")
    get_settings.cache_clear()
    try:
        configured = get_settings()
        assert configured.groq_model == "openai/gpt-oss-120b"
        assert configured.chunk_size == 800
        assert configured.vector_db_path == "/tmp/documind-test-vectors"
    finally:
        get_settings.cache_clear()


def test_question_length_is_bounded():
    with pytest.raises(ValidationError):
        AskRequest(question="x" * 4001)


def test_source_filename_length_is_bounded():
    with pytest.raises(ValidationError):
        AskRequest(question="Summarize this", source_filename="x" * 256)
