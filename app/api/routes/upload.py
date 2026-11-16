"""Bounded PDF upload and indexing endpoint."""

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from app.api.dependencies import get_document_service
from app.config.settings import settings
from app.models.schemas import UploadResponse
from app.services.document_service import DocumentService
from app.utils.exceptions import (
    CorruptedPDFError, DuplicateDocumentError, EmptyDocumentError,
    FileTooLargeError, UnsupportedFileTypeError,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["Upload"])
MAX_UPLOAD_BYTES = settings.max_file_size_mb * 1024 * 1024


@router.post("/upload", response_model=UploadResponse)
def upload_document(
    file: UploadFile,
    service: DocumentService = Depends(get_document_service),
) -> UploadResponse:
    filename = Path(file.filename or "").name
    if not filename or Path(filename).suffix.lower() not in settings.allowed_extensions:
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    upload_dir = Path(settings.upload_path)
    upload_dir.mkdir(parents=True, exist_ok=True)
    saved_path = upload_dir / f"{uuid.uuid4().hex}.pdf"
    total = 0

    try:
        with saved_path.open("wb") as destination:
            while block := file.file.read(1024 * 1024):
                total += len(block)
                if total > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File exceeds the {settings.max_file_size_mb}MB upload limit.",
                    )
                destination.write(block)

        with saved_path.open("rb") as source:
            if source.read(5) != b"%PDF-":
                raise HTTPException(status_code=400, detail="The uploaded file is not a valid PDF.")

        chunks_created = service.upload_and_index(saved_path, filename)
    except HTTPException:
        raise
    except FileTooLargeError as exc:
        raise HTTPException(status_code=413, detail=exc.message) from exc
    except DuplicateDocumentError as exc:
        raise HTTPException(status_code=409, detail=exc.message) from exc
    except CorruptedPDFError as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc
    except EmptyDocumentError as exc:
        raise HTTPException(status_code=422, detail=exc.message) from exc
    except UnsupportedFileTypeError as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc
    except Exception as exc:
        logger.exception("Unexpected upload failure")
        raise HTTPException(status_code=500, detail="Internal error during upload.") from exc
    finally:
        saved_path.unlink(missing_ok=True)
        file.file.close()

    return UploadResponse(
        filename=filename,
        chunks_created=chunks_created,
        message=f"'{filename}' indexed successfully with {chunks_created} chunks.",
    )
