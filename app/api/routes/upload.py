"""
PDF upload and indexing endpoint.
"""

import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from app.api.dependencies import get_document_service
from app.config.settings import settings
from app.models.schemas import UploadResponse
from app.services.document_service import DocumentService
from app.utils.exceptions import (
    CorruptedPDFError,
    DuplicateDocumentError,
    EmptyDocumentError,
    FileTooLargeError,
    UnsupportedFileTypeError,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["Upload"])


@router.post("/upload", response_model=UploadResponse)
def upload_document(
    file: UploadFile,
    service: DocumentService = Depends(get_document_service),
) -> UploadResponse:
    """
    Upload a PDF file to be indexed for question-answering.

    The file is saved to disk, then loaded, chunked, embedded, and stored
    in the vector database.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported.",
        )

    upload_dir = Path(settings.upload_path)
    upload_dir.mkdir(parents=True, exist_ok=True)

    temp_name = f"{uuid.uuid4().hex}_{file.filename}"
    saved_path = upload_dir / temp_name

    try:
        with open(saved_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        chunks_created = service.upload_and_index(
            file_path=saved_path, original_filename=file.filename
        )

    except FileTooLargeError as exc:
        raise HTTPException(status_code=413, detail=exc.message)
    except DuplicateDocumentError as exc:
        raise HTTPException(status_code=409, detail=exc.message)
    except CorruptedPDFError as exc:
        raise HTTPException(status_code=400, detail=exc.message)
    except EmptyDocumentError as exc:
        raise HTTPException(status_code=422, detail=exc.message)
    except UnsupportedFileTypeError as exc:
        raise HTTPException(status_code=400, detail=exc.message)
    except Exception as exc:
        logger.error(f"Unexpected error during upload: {exc}")
        raise HTTPException(status_code=500, detail="Internal error during upload.")
    finally:
        if saved_path.exists():
            saved_path.unlink()

    return UploadResponse(
        filename=file.filename,
        chunks_created=chunks_created,
        message=f"'{file.filename}' indexed successfully with {chunks_created} chunks.",
    )