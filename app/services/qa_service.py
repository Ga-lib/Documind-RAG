"""
QA service: orchestrates retrieval + generation for a user's question,
and formats the result into API-ready source citations.
"""

from app.models.schemas import SourceCitation
from app.rag.generator.generator import Generator
from app.rag.retriever.retriever import Retriever
from app.utils.logger import get_logger

logger = get_logger(__name__)


class QAService:
    """Answers a user's question by retrieving relevant chunks and generating a grounded answer."""

    def __init__(self):
        self._retriever = Retriever()
        self._generator = Generator()

    def ask(
        self,
        question: str,
        top_k: int | None = None,
        source_filename: str | None = None,
    ) -> tuple[str, list[SourceCitation]]:
        """
        Answer a question using the RAG pipeline.

        Returns:
            A tuple of (answer_text, list_of_source_citations).
        """
        chunks = self._retriever.retrieve(
            query=question, top_k=top_k, source_filename=source_filename
        )
        result = self._generator.generate(question, chunks)

        citations = [
            SourceCitation(
                source_number=i,
                filename=chunk.metadata.get("source_filename", "unknown"),
                chunk_index=chunk.metadata.get("chunk_index", -1),
                text_snippet=chunk.text[:200],
                distance=chunk.distance,
            )
            for i, chunk in enumerate(result.sources, start=1)
        ]

        return result.answer, citations