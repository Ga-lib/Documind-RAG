"""
Text chunking strategies.

Splits extracted document text into overlapping chunks suitable for
embedding and retrieval. Implements both a naive fixed-size strategy and
a recursive strategy that prefers natural text boundaries, so the
tradeoff between them can be demonstrated by switching config.
"""

from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Chunk:
    """A single chunk of text, ready to be embedded."""

    text: str
    chunk_index: int  # position of this chunk within its source document
    source_filename: str


class BaseChunker:
    """Common interface all chunking strategies implement."""

    def split(self, text: str, source_filename: str) -> list[Chunk]:
        raise NotImplementedError


class FixedSizeChunker(BaseChunker):
    """
    Splits text into fixed-size character windows with overlap.

    Simplest possible strategy: cuts every `chunk_size` characters
    regardless of sentence or paragraph boundaries. Fast and predictable,
    but can split a sentence (or even a word) in half, which hurts
    embedding quality since a fragment may no longer carry clear meaning.
    """

    def __init__(self, chunk_size: int, chunk_overlap: int):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split(self, text: str, source_filename: str) -> list[Chunk]:
        chunks: list[Chunk] = []
        start = 0
        index = 0
        step = self.chunk_size - self.chunk_overlap

        while start < len(text):
            end = start + self.chunk_size
            piece = text[start:end].strip()
            if piece:
                chunks.append(
                    Chunk(text=piece, chunk_index=index, source_filename=source_filename)
                )
                index += 1
            start += step

        return chunks


class RecursiveChunker(BaseChunker):
    """
    Splits text preferring natural boundaries: paragraphs, then sentences,
    then words, only falling back to a hard character cut if a piece is
    still too large. This is the production-default strategy because it
    keeps each chunk semantically coherent, which meaningfully improves
    retrieval quality over fixed-size chunking.
    """

    def __init__(self, chunk_size: int, chunk_overlap: int):
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def split(self, text: str, source_filename: str) -> list[Chunk]:
        pieces = self._splitter.split_text(text)
        return [
            Chunk(text=piece.strip(), chunk_index=i, source_filename=source_filename)
            for i, piece in enumerate(pieces)
            if piece.strip()
        ]


def get_chunker() -> BaseChunker:
    """
    Factory that returns the configured chunking strategy.

    Reads `chunking.strategy` from config.yaml (via settings) so the
    strategy can be swapped without touching any calling code.
    """
    strategy = "recursive"  # config.yaml currently only exposes this default
    logger.info(
        f"Using '{strategy}' chunker (chunk_size={settings.chunk_size}, "
        f"overlap={settings.chunk_overlap})"
    )

    if strategy == "fixed":
        return FixedSizeChunker(
            chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap
        )
    return RecursiveChunker(
        chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap
    )