"""Thread-safe singleton dependency providers for application services."""

from threading import Lock

from app.services.document_service import DocumentService
from app.services.qa_service import QAService

_service_lock = Lock()
_document_service: DocumentService | None = None
_qa_service: QAService | None = None


def get_document_service() -> DocumentService:
    global _document_service
    if _document_service is None:
        with _service_lock:
            if _document_service is None:
                _document_service = DocumentService()
    return _document_service


def get_qa_service() -> QAService:
    global _qa_service
    if _qa_service is None:
        with _service_lock:
            if _qa_service is None:
                _qa_service = QAService()
    return _qa_service
