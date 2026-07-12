"""
Answer generation via the Groq API.

Takes retrieved chunks and a user question, builds the anti-hallucination
prompt, and calls Groq's chat completion endpoint to produce a grounded
answer. Isolated behind this one file so swapping to a different LLM
provider (OpenAI, Anthropic, local model) later only requires changing
this module, not any calling code.
"""

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
    """The LLM's answer plus the source chunks it was grounded in."""

    answer: str
    sources: list[StoredChunk]


class Generator:
    """Generates grounded answers from retrieved context using Groq."""

    def __init__(self):
        self._client = Groq(api_key=settings.groq_api_key)

    def generate(self, question: str, chunks: list[StoredChunk]) -> GeneratedAnswer:
        """
        Generate an answer to `question` using only the provided `chunks`
        as context.

        Raises:
            LLMTimeoutError: if the Groq API call times out.
            LLMAPIError: if the Groq API returns an error response.
        """
        user_prompt = build_user_prompt(question, chunks)

        logger.info(
            f"Calling Groq model '{settings.groq_model}' with {len(chunks)} "
            f"context chunks"
        )

        try:
            response = self._client.chat.completions.create(
                model=settings.groq_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=settings.temperature,
                max_tokens=1024,
                timeout=30,
            )
        except APITimeoutError as exc:
            logger.error(f"Groq API call timed out: {exc}")
            raise LLMTimeoutError("The AI model took too long to respond.") from exc
        except APIError as exc:
            logger.error(f"Groq API returned an error: {exc}")
            raise LLMAPIError(f"The AI model returned an error: {exc}") from exc

        answer_text = response.choices[0].message.content
        logger.info(f"Generated answer ({len(answer_text)} characters)")

        return GeneratedAnswer(answer=answer_text, sources=chunks)