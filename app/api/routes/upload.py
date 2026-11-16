"""Authenticated, bounded PDF upload."""
import uuid
from pathlib import Path
from fastapi import APIRouter,Depends,HTTPException,UploadFile
from app.api.dependencies import get_document_service
from app.config.settings import settings
from app.models.schemas import UploadResponse
from app.services.supabase_document_service import SupabaseDocumentService
from app.utils.logger import get_logger
logger=get_logger(__name__)
router=APIRouter(tags=["Upload"])
MAX_UPLOAD_BYTES=settings.max_file_size_mb*1024*1024
@router.post("/upload",response_model=UploadResponse)
def upload_document(file:UploadFile,service:SupabaseDocumentService=Depends(get_document_service)):
    filename=Path(file.filename or "").name
    if not filename or Path(filename).suffix.lower() not in settings.allowed_extensions: raise HTTPException(400,"Only PDF files are supported.")
    temp=Path("/tmp")/f"documind-{uuid.uuid4().hex}.pdf"; total=0
    try:
        with temp.open("wb") as dst:
            while block:=file.file.read(1024*1024):
                total+=len(block)
                if total>MAX_UPLOAD_BYTES: raise HTTPException(413,f"File exceeds {settings.max_file_size_mb}MB.")
                dst.write(block)
        if temp.read_bytes()[:5]!=b"%PDF-": raise HTTPException(400,"The uploaded file is not a valid PDF.")
        count=service.upload_and_index(temp,filename)
        return UploadResponse(filename=filename,chunks_created=count,message=f"'{filename}' indexed with {count} chunks.")
    except HTTPException: raise
    except ValueError as exc: raise HTTPException(409,str(exc)) from exc
    except Exception as exc:
        logger.exception("Supabase PDF upload failed")
        raise HTTPException(502,"Could not store or index this PDF. Please retry.") from exc
    finally:
        temp.unlink(missing_ok=True); file.file.close()
