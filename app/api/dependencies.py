"""
FastAPI dependency providers.

Uses lru_cache so DocumentService/QAService (and everything they hold —
the embedding model, the Groq client, the Chroma connection) are created
once per process and reused across requests, instead of being expensively
rebuilt on every single API call.
"""

from functools import lru_cache

from app.services.document_service import DocumentService
from app.services.qa_service import QAService


@lru_cache
def get_document_service() -> DocumentService:
    return DocumentService()


@lru_cache
def get_qa_service() -> QAService:
    return QAService()