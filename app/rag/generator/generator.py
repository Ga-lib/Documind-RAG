"""Grounded answer generation through the Groq API."""

from dataclasses import dataclass

from groq import Groq, APIError, APITimeoutError

from app.config.settings import settings
from app.rag.generator.prompt_templates import SYSTEM_PROMPT, build_user_prompt
from app.utils.exceptions import LLMAPIError, LLMTimeoutError
from app.utils.logger import get_logger
from app.vectorstore.chroma_store import StoredChunk

logger = get_logger(__name__)


@dataclass
class GeneratedAnswer:
    answer: str
    sources: list[StoredChunk]


class Generator:
    def __init__(self):
        self._client = Groq(api_key=settings.groq_api_key, timeout=settings.llm_timeout_seconds)

    def generate(self, question: str, chunks: list[StoredChunk]) -> GeneratedAnswer:
        if not chunks:
            return GeneratedAnswer(
                answer="I could not find relevant information in the indexed documents.",
                sources=[],
            )
        user_prompt = build_user_prompt(question, chunks)
        logger.info("Calling Groq model %s with %d context chunks", settings.groq_model, len(chunks))
        try:
            response = self._client.chat.completions.create(
                model=settings.groq_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=settings.temperature,
                max_tokens=settings.max_tokens,
                timeout=settings.llm_timeout_seconds,
            )
        except APITimeoutError as exc:
            logger.warning("Groq API request timed out")
            raise LLMTimeoutError("The AI model took too long to respond.") from exc
        except APIError as exc:
            logger.exception("Groq API request failed")
            raise LLMAPIError("The AI model request failed. Please try again later.") from exc

        answer_text = response.choices[0].message.content if response.choices else None
        if not answer_text or not answer_text.strip():
            raise LLMAPIError("The AI model returned an empty response.")
        logger.info("Generated answer (%d characters)", len(answer_text))
        return GeneratedAnswer(answer=answer_text.strip(), sources=chunks)
