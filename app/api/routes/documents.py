"""Document listing and deletion endpoints."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_document_service
from app.models.schemas import DeleteDocumentResponse, DocumentInfo, DocumentListResponse
from app.services.document_service import DocumentService
from app.utils.exceptions import VectorStoreError
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["Documents"])


@router.get("/documents", response_model=DocumentListResponse)
def list_documents(service: DocumentService = Depends(get_document_service)) -> DocumentListResponse:
    try:
        filenames = service.list_documents()
    except VectorStoreError as exc:
        logger.exception("Failed to list documents")
        raise HTTPException(status_code=500, detail="Could not list documents.") from exc
    return DocumentListResponse(documents=[DocumentInfo(filename=name) for name in filenames], count=len(filenames))


@router.delete("/documents/{filename}", response_model=DeleteDocumentResponse)
def delete_document(filename: str, service: DocumentService = Depends(get_document_service)) -> DeleteDocumentResponse:
    try:
        service.delete_document(filename)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Document not found.") from exc
    except VectorStoreError as exc:
        logger.exception("Failed to delete document")
        raise HTTPException(status_code=500, detail="Could not delete document.") from exc
    return DeleteDocumentResponse(filename=filename, message=f"'{filename}' deleted successfully.")
