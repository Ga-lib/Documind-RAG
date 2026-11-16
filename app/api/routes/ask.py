"""Question-answering endpoint."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_qa_service
from app.api.security import require_api_key
from app.models.schemas import AskRequest, AskResponse
from app.services.qa_service import QAService
from app.utils.exceptions import LLMAPIError, LLMTimeoutError, RetrievalError
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["Ask"], dependencies=[Depends(require_api_key)])


@router.post("/ask", response_model=AskResponse)
def ask_question(request: AskRequest, service: QAService = Depends(get_qa_service)) -> AskResponse:
    try:
        answer, sources = service.ask(
            question=request.question, top_k=request.top_k, source_filename=request.source_filename
        )
    except RetrievalError as exc:
        raise HTTPException(status_code=500, detail=exc.message) from exc
    except LLMTimeoutError as exc:
        raise HTTPException(status_code=504, detail=exc.message) from exc
    except LLMAPIError as exc:
        raise HTTPException(status_code=502, detail=exc.message) from exc
    except Exception as exc:
        logger.exception("Unexpected error during question answering")
        raise HTTPException(status_code=500, detail="Internal error while answering.") from exc
    return AskResponse(question=request.question, answer=answer, sources=sources)
