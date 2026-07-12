"""
ChromaDB vector store wrapper.

Isolates all ChromaDB-specific code behind a small interface, so the rest
of the app (retriever, services) never imports chromadb directly. This is
what makes swapping to a different vector database later a one-file change
instead of a rewrite.
"""

from dataclasses import dataclass

import os

os.environ["ANONYMIZED_TELEMETRY"] = "False"

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config.settings import settings
from app.utils.exceptions import VectorStoreError
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class StoredChunk:
    """A chunk as returned from a similarity search, with its distance score."""

    id: str
    text: str
    metadata: dict
    distance: float


class ChromaStore:
    """Wraps a persistent ChromaDB collection for storing and querying chunk vectors."""

    def __init__(self):
        try:
            self._client = chromadb.PersistentClient(
                path=settings.vector_db_path,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            self._collection = self._client.get_or_create_collection(
                name=settings.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info(
                f"Connected to ChromaDB collection '{settings.collection_name}' "
                f"at '{settings.vector_db_path}'"
            )
        except Exception as exc:
            logger.error(f"Failed to initialize ChromaDB: {exc}")
            raise VectorStoreError(f"Could not initialize vector store: {exc}") from exc

    def add_chunks(
        self,
        ids: list[str],
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
    ) -> None:
        """
        Insert chunks into the collection.

        ids must be globally unique (we'll build them as
        f"{filename}::chunk_{index}" at the call site) so re-uploading the
        same document with the same chunks overwrites rather than duplicates.
        """
        if not ids:
            return
        try:
            self._collection.upsert(
                ids=ids,
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
            )
            logger.info(f"Upserted {len(ids)} chunks into vector store")
        except Exception as exc:
            logger.error(f"Failed to add chunks to vector store: {exc}")
            raise VectorStoreError(f"Could not store chunks: {exc}") from exc

    def query(
        self,
        query_embedding: list[float],
        top_k: int,
        where: dict | None = None,
    ) -> list[StoredChunk]:
        """
        Find the top_k chunks most similar to query_embedding.

        `where` is an optional metadata filter, e.g. {"source_filename": "x.pdf"},
        letting a caller restrict search to a specific document.
        """
        try:
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where,
            )
        except Exception as exc:
            logger.error(f"Vector store query failed: {exc}")
            raise VectorStoreError(f"Query failed: {exc}") from exc

        stored_chunks: list[StoredChunk] = []
        ids = results["ids"][0]
        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        for i in range(len(ids)):
            stored_chunks.append(
                StoredChunk(
                    id=ids[i],
                    text=documents[i],
                    metadata=metadatas[i],
                    distance=distances[i],
                )
            )

        logger.info(f"Query returned {len(stored_chunks)} chunks")
        return stored_chunks

    def delete_by_filename(self, filename: str) -> None:
        """Remove all chunks belonging to a specific source document."""
        try:
            self._collection.delete(where={"source_filename": filename})
            logger.info(f"Deleted all chunks for '{filename}'")
        except Exception as exc:
            logger.error(f"Failed to delete chunks for '{filename}': {exc}")
            raise VectorStoreError(f"Could not delete document: {exc}") from exc

    def list_document_filenames(self) -> list[str]:
        """Return the unique set of source filenames currently stored."""
        try:
            all_items = self._collection.get(include=["metadatas"])
        except Exception as exc:
            logger.error(f"Failed to list documents: {exc}")
            raise VectorStoreError(f"Could not list documents: {exc}") from exc

        filenames = {
            meta["source_filename"]
            for meta in all_items["metadatas"]
            if meta and "source_filename" in meta
        }
        return sorted(filenames)