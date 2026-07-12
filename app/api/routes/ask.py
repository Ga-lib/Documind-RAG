"""
Question-answering endpoint.
"""

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_qa_service
from app.models.schemas import AskRequest, AskResponse
from app.services.qa_service import QAService
from app.utils.exceptions import LLMAPIError, LLMTimeoutError, RetrievalError
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["Ask"])


@router.post("/ask", response_model=AskResponse)
def ask_question(
    request: AskRequest,
    service: QAService = Depends(get_qa_service),
) -> AskResponse:
    """
    Ask a question and get a grounded answer with source citations, based
    only on the currently indexed documents.
    """
    try:
        answer, sources = service.ask(
            question=request.question,
            top_k=request.top_k,
            source_filename=request.source_filename,
        )
    except RetrievalError as exc:
        raise HTTPException(status_code=500, detail=exc.message)
    except LLMTimeoutError as exc:
        raise HTTPException(status_code=504, detail=exc.message)
    except LLMAPIError as exc:
        raise HTTPException(status_code=502, detail=exc.message)
    except Exception as exc:
        logger.error(f"Unexpected error during ask: {exc}")
        raise HTTPException(status_code=500, detail="Internal error while answering.")

    return AskResponse(question=request.question, answer=answer, sources=sources)