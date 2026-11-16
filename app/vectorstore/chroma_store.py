"""ChromaDB persistent vector-store adapter."""

from dataclasses import dataclass
import os
from pathlib import Path

os.environ["ANONYMIZED_TELEMETRY"] = "False"

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config.settings import settings
from app.utils.exceptions import VectorStoreError
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class StoredChunk:
    id: str
    text: str
    metadata: dict
    distance: float


class ChromaStore:
    def __init__(self):
        try:
            Path(settings.vector_db_path).mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(
                path=settings.vector_db_path,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            self._collection = self._client.get_or_create_collection(
                name=settings.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        except Exception as exc:
            logger.exception("Failed to initialize ChromaDB")
            raise VectorStoreError("Could not initialize vector store.") from exc

    def add_chunks(self, ids: list[str], texts: list[str], embeddings: list[list[float]], metadatas: list[dict]) -> None:
        if not ids:
            return
        try:
            self._collection.add(ids=ids, documents=texts, embeddings=embeddings, metadatas=metadatas)
        except Exception as exc:
            logger.exception("Failed to add chunks to vector store")
            raise VectorStoreError("Could not store document chunks.") from exc

    def query(self, query_embedding: list[float], top_k: int, where: dict | None = None) -> list[StoredChunk]:
        try:
            count = self._collection.count()
            if count == 0:
                return []
            results = self._collection.query(query_embeddings=[query_embedding], n_results=min(top_k, count), where=where)
        except Exception as exc:
            logger.exception("Vector store query failed")
            raise VectorStoreError("Vector search failed.") from exc
        return [
            StoredChunk(id=chunk_id, text=text, metadata=metadata or {}, distance=distance)
            for chunk_id, text, metadata, distance in zip(
                results["ids"][0], results["documents"][0], results["metadatas"][0], results["distances"][0]
            )
        ]

    def has_file_hash(self, file_hash: str) -> bool:
        try:
            result = self._collection.get(where={"file_hash": file_hash}, include=["metadatas"], limit=1)
            return bool(result.get("ids"))
        except Exception as exc:
            logger.exception("Duplicate-content lookup failed")
            raise VectorStoreError("Could not check for duplicate documents.") from exc

    def delete_by_filename(self, filename: str) -> None:
        try:
            existing = self._collection.get(where={"source_filename": filename}, include=["metadatas"], limit=1)
            if not existing.get("ids"):
                raise KeyError(filename)
            self._collection.delete(where={"source_filename": filename})
        except KeyError:
            raise
        except Exception as exc:
            logger.exception("Failed to delete document")
            raise VectorStoreError("Could not delete document.") from exc

    def list_document_filenames(self) -> list[str]:
        try:
            all_items = self._collection.get(include=["metadatas"])
            return sorted({meta["source_filename"] for meta in all_items["metadatas"] if meta and meta.get("source_filename")})
        except Exception as exc:
            logger.exception("Failed to list documents")
            raise VectorStoreError("Could not list documents.") from exc
