"""Authenticated document list and deletion."""
from fastapi import APIRouter,Depends,HTTPException
from app.api.dependencies import get_document_service
from app.models.schemas import DeleteDocumentResponse,DocumentInfo,DocumentListResponse
from app.services.supabase_document_service import SupabaseDocumentService
from app.utils.logger import get_logger
logger=get_logger(__name__)
router=APIRouter(tags=["Documents"])
@router.get("/documents",response_model=DocumentListResponse)
def list_documents(service:SupabaseDocumentService=Depends(get_document_service)):
    try: rows=service.list_documents()
    except Exception as exc:
        logger.exception("Document listing failed"); raise HTTPException(502,"Could not load your documents.") from exc
    docs=[DocumentInfo(id=r["id"],filename=r["filename"]) for r in rows if r.get("status")=="ready"]
    return DocumentListResponse(documents=docs,count=len(docs))
@router.delete("/documents/{document_id}",response_model=DeleteDocumentResponse)
def delete_document(document_id:str,service:SupabaseDocumentService=Depends(get_document_service)):
    try: service.delete_document(document_id)
    except KeyError as exc: raise HTTPException(404,"Document not found.") from exc
    except Exception as exc:
        logger.exception("Document deletion failed"); raise HTTPException(502,"Could not delete document.") from exc
    return DeleteDocumentResponse(filename=document_id,message="Document deleted successfully.")
