"""Document ingestion and lifecycle service."""

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
    def __init__(self):
        self._loader = PDFLoader()
        self._chunker = get_chunker()
        self._embedder = Embedder()
        self._store = ChromaStore()

    def upload_and_index(self, file_path: str | Path, original_filename: str) -> int:
        file_path = Path(file_path)
        if not file_path.is_file():
            raise FileNotFoundError("Uploaded file was not saved.")
        size_bytes = file_path.stat().st_size
        max_bytes = settings.max_file_size_mb * 1024 * 1024
        if size_bytes > max_bytes:
            raise FileTooLargeError(
                f"File exceeds the configured {settings.max_file_size_mb}MB limit."
            )

        file_hash = hash_file(file_path)
        if self._store.has_file_hash(file_hash) or original_filename in self._store.list_document_filenames():
            raise DuplicateDocumentError("A document with this content or filename has already been indexed.")

        document = self._loader.load(file_path)
        chunks = self._chunker.split(document.full_text, original_filename)
        if not chunks:
            return 0

        texts = [chunk.text for chunk in chunks]
        embeddings = self._embedder.embed_texts(texts)
        document_id = file_hash[:24]
        ids = [f"{document_id}::chunk_{chunk.chunk_index}" for chunk in chunks]
        metadatas = [
            {
                "source_filename": original_filename,
                "chunk_index": chunk.chunk_index,
                "file_hash": file_hash,
                "document_id": document_id,
            }
            for chunk in chunks
        ]
        self._store.add_chunks(ids=ids, texts=texts, embeddings=embeddings, metadatas=metadatas)
        logger.info("Indexed '%s' as %s (%d chunks)", original_filename, document_id, len(chunks))
        return len(chunks)

    def list_documents(self) -> list[str]:
        return self._store.list_document_filenames()

    def delete_document(self, filename: str) -> None:
        self._store.delete_by_filename(filename)
