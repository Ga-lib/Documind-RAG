"""Configurable fixed-size and recursive text chunking strategies."""

from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Chunk:
    text: str
    chunk_index: int
    source_filename: str


class BaseChunker:
    def split(self, text: str, source_filename: str) -> list[Chunk]:
        raise NotImplementedError


class FixedSizeChunker(BaseChunker):
    def __init__(self, chunk_size: int, chunk_overlap: int):
        if chunk_size <= 0 or chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError("Require chunk_size > chunk_overlap >= 0")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split(self, text: str, source_filename: str) -> list[Chunk]:
        chunks = []
        step = self.chunk_size - self.chunk_overlap
        for index, start in enumerate(range(0, len(text), step)):
            piece = text[start : start + self.chunk_size].strip()
            if piece:
                chunks.append(Chunk(piece, len(chunks), source_filename))
        return chunks


class RecursiveChunker(BaseChunker):
    def __init__(self, chunk_size: int, chunk_overlap: int):
        if chunk_size <= 0 or chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError("Require chunk_size > chunk_overlap >= 0")
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def split(self, text: str, source_filename: str) -> list[Chunk]:
        pieces = self._splitter.split_text(text)
        return [Chunk(piece.strip(), i, source_filename) for i, piece in enumerate(pieces) if piece.strip()]


def get_chunker() -> BaseChunker:
    strategy = settings.chunking_strategy
    logger.info(
        "Using %s chunker (chunk_size=%d, overlap=%d)",
        strategy, settings.chunk_size, settings.chunk_overlap,
    )
    chunker_class = FixedSizeChunker if strategy == "fixed" else RecursiveChunker
    return chunker_class(settings.chunk_size, settings.chunk_overlap)
