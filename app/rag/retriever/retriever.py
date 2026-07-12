"""
Retrieval strategies built on top of the vector store.

Separates retrieval strategy (top-k, MMR, metadata filtering) from vector
storage mechanics (ChromaStore), so the strategy can be swapped or tuned
without touching any ChromaDB-specific code.
"""

import numpy as np

from app.config.settings import settings
from app.rag.embeddings.embedder import Embedder
from app.utils.exceptions import RetrievalError
from app.utils.logger import get_logger
from app.vectorstore.chroma_store import ChromaStore, StoredChunk

logger = get_logger(__name__)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    a_arr, b_arr = np.array(a), np.array(b)
    denom = np.linalg.norm(a_arr) * np.linalg.norm(b_arr)
    if denom == 0:
        return 0.0
    return float(np.dot(a_arr, b_arr) / denom)


class Retriever:
    """
    Retrieves relevant chunks for a query using the configured strategy.

    search_type comes from config.yaml ("similarity" or "mmr"), so behavior
    can be changed by editing config, not code — useful for demonstrating
    the tradeoff live.
    """

    def __init__(self, store: ChromaStore | None = None, embedder: Embedder | None = None):
        self._store = store or ChromaStore()
        self._embedder = embedder or Embedder()

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        source_filename: str | None = None,
    ) -> list[StoredChunk]:
        """
        Retrieve the most relevant chunks for a query.

        Args:
            query: the user's natural-language question.
            top_k: number of chunks to return; defaults to settings.top_k.
            source_filename: if given, restricts search to chunks from that
                document only (metadata filtering).
        """
        top_k = top_k or settings.top_k
        where = {"source_filename": source_filename} if source_filename else None

        try:
            query_vector = self._embedder.embed_query(query)
        except Exception as exc:
            logger.error(f"Failed to embed query: {exc}")
            raise RetrievalError(f"Could not process query: {exc}") from exc

        if settings.search_type == "mmr":
            return self._retrieve_mmr(query_vector, top_k, where)
        return self._retrieve_similarity(query_vector, top_k, where)

    def _retrieve_similarity(
        self, query_vector: list[float], top_k: int, where: dict | None
    ) -> list[StoredChunk]:
        """Plain top-k similarity search — fast, simple, may return near-duplicates."""
        logger.info(f"Retrieving top-{top_k} chunks via similarity search")
        return self._store.query(query_embedding=query_vector, top_k=top_k, where=where)

    def _retrieve_mmr(
        self, query_vector: list[float], top_k: int, where: dict | None
    ) -> list[StoredChunk]:
        """
        MMR retrieval: fetch a larger candidate pool via similarity, then
        greedily select `top_k` of them balancing relevance to the query
        against diversity from chunks already selected.
        """
        pool_size = max(top_k * 4, 10)
        logger.info(
            f"Retrieving via MMR: pooling {pool_size} candidates, selecting {top_k}"
        )
        candidates = self._store.query(
            query_embedding=query_vector, top_k=pool_size, where=where
        )
        if len(candidates) <= top_k:
            return candidates

        # We don't have candidate embeddings back from Chroma's query response,
        # so we re-embed candidate texts for the diversity comparison. This is
        # a deliberate simplification — acceptable for a portfolio-scale
        # project since candidate pools are small (tens of chunks, not
        # thousands), but noted here as a real limitation to discuss.
        candidate_vectors = self._embedder.embed_texts([c.text for c in candidates])

        selected_indices: list[int] = []
        remaining_indices = list(range(len(candidates)))
        lambda_param = settings.mmr_diversity

        # Seed with the single most relevant candidate.
        first = min(remaining_indices, key=lambda i: candidates[i].distance)
        selected_indices.append(first)
        remaining_indices.remove(first)

        while len(selected_indices) < top_k and remaining_indices:
            best_score = None
            best_index = None
            for i in remaining_indices:
                relevance = 1 - candidates[i].distance  # smaller distance = more relevant
                max_similarity_to_selected = max(
                    _cosine_similarity(candidate_vectors[i], candidate_vectors[j])
                    for j in selected_indices
                )
                mmr_score = (
                    lambda_param * relevance
                    - (1 - lambda_param) * max_similarity_to_selected
                )
                if best_score is None or mmr_score > best_score:
                    best_score = mmr_score
                    best_index = i
            selected_indices.append(best_index)
            remaining_indices.remove(best_index)

        return [candidates[i] for i in selected_indices]