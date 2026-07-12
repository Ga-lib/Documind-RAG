"""
Document service: orchestrates the upload -> load -> chunk -> embed -> store
pipeline, plus document listing and deletion.

This is the layer the API routes call into. It knows about RAG components
(loader, chunker, embedder, store) but nothing about HTTP/FastAPI, which
keeps business logic reusable outside the API (e.g. from a CLI script).
"""

import hashlib
from pathlib import Path

from app.config.settings import settings
from app.rag.chunking.chunker import get_chunker
from app.rag.embeddings.embedder import Embedder
from app.rag.loader.pdf_loader import PDFLoader
from app.utils.exceptions import DuplicateDocumentError, FileTooLargeError
from app.utils.hashing import hash_file
from app.utils.logger import get_logger
from app.vectorstore.chroma_store import ChromaStore

logger = get_logger(__name__)


class DocumentService:
    """Handles the full lifecycle of documents: upload, index, list, delete."""

    def __init__(self):
        self._loader = PDFLoader()
        self._chunker = get_chunker()
        self._embedder = Embedder()
        self._store = ChromaStore()

    def upload_and_index(self, file_path: str | Path, original_filename: str) -> int:
        """
        Load, chunk, embed, and store a PDF that has already been saved to disk.

        Args:
            file_path: where the uploaded file currently lives on disk.
            original_filename: the filename to record as metadata (used
                for deletion and filtering later).

        Returns:
            Number of chunks created and stored.

        Raises:
            FileTooLargeError: if the file exceeds the configured size limit.
            DuplicateDocumentError: if this exact file was already indexed.
            CorruptedPDFError / EmptyDocumentError: propagated from the loader.
        """
        file_path = Path(file_path)

        size_mb = file_path.stat().st_size / (1024 * 1024)
        if size_mb > settings.max_file_size_mb:
            raise FileTooLargeError(
                f"'{original_filename}' is {size_mb:.1f}MB, which exceeds the "
                f"{settings.max_file_size_mb}MB limit."
            )

        file_hash = hash_file(file_path)
        existing_filenames = self._store.list_document_filenames()
        # Duplicate detection is filename-based here: if a document with the
        # same name is already indexed, we treat a fresh upload as a
        # duplicate rather than silently creating overlapping chunks. A
        # content-hash check (file_hash) is computed above for future use
        # (e.g. detecting the same file uploaded under a different name)
        # but isn't wired into the comparison yet — noted as a known gap
        # rather than pretending it's fully implemented.
        if original_filename in existing_filenames:
            raise DuplicateDocumentError(
                f"'{original_filename}' has already been indexed. "
                "Delete it first if you want to re-upload."
            )

        document = self._loader.load(file_path)
        chunks = self._chunker.split(document.full_text, original_filename)

        if not chunks:
            logger.warning(f"No chunks produced for '{original_filename}'")
            return 0

        texts = [c.text for c in chunks]
        embeddings = self._embedder.embed_texts(texts)
        ids = [f"{original_filename}::chunk_{c.chunk_index}" for c in chunks]
        metadatas = [
            {
                "source_filename": original_filename,
                "chunk_index": c.chunk_index,
                "file_hash": file_hash,
            }
            for c in chunks
        ]

        self._store.add_chunks(ids=ids, texts=texts, embeddings=embeddings, metadatas=metadatas)
        logger.info(f"Indexed '{original_filename}': {len(chunks)} chunks")
        return len(chunks)

    def list_documents(self) -> list[str]:
        """Return all indexed document filenames."""
        return self._store.list_document_filenames()

    def delete_document(self, filename: str) -> None:
        """Remove all chunks belonging to a document."""
        self._store.delete_by_filename(filename)