"""Authenticated document question-answering endpoint."""
from fastapi import APIRouter,Depends,HTTPException
from app.api.dependencies import get_qa_service
from app.models.schemas import AskRequest,AskResponse
from app.services.supabase_qa_service import SupabaseQAService
from app.utils.exceptions import LLMAPIError,LLMTimeoutError,RetrievalError
from app.utils.logger import get_logger
logger=get_logger(__name__)
router=APIRouter(tags=["Ask"])
@router.post("/ask",response_model=AskResponse)
def ask_question(request:AskRequest,service:SupabaseQAService=Depends(get_qa_service)):
    try: answer,sources=service.ask(request.question,request.top_k,request.source_document_id)
    except LLMTimeoutError as exc: raise HTTPException(504,exc.message) from exc
    except LLMAPIError as exc: raise HTTPException(502,exc.message) from exc
    except Exception as exc:
        logger.exception("Supabase retrieval failed")
        raise HTTPException(502,"Could not retrieve your documents or generate an answer.") from exc
    return AskResponse(question=request.question,answer=answer,sources=sources)
