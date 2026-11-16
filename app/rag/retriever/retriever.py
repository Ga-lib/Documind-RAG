"""Similarity and maximal-marginal-relevance retrieval."""

import numpy as np

from app.config.settings import settings
from app.rag.embeddings.embedder import Embedder
from app.utils.exceptions import RetrievalError
from app.utils.logger import get_logger
from app.vectorstore.chroma_store import ChromaStore, StoredChunk

logger = get_logger(__name__)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    a_arr, b_arr = np.asarray(a), np.asarray(b)
    denom = np.linalg.norm(a_arr) * np.linalg.norm(b_arr)
    if denom == 0:
        return 0.0
    return float(np.clip(np.dot(a_arr, b_arr) / denom, -1.0, 1.0))


class Retriever:
    def __init__(self, store: ChromaStore | None = None, embedder: Embedder | None = None):
        self._store = store or ChromaStore()
        self._embedder = embedder or Embedder()

    def retrieve(self, query: str, top_k: int | None = None, source_filename: str | None = None) -> list[StoredChunk]:
        if not query or not query.strip():
            return []
        top_k = settings.top_k if top_k is None else top_k
        if top_k < 1:
            return []
        where = {"source_filename": source_filename} if source_filename else None
        try:
            query_vector = self._embedder.embed_query(query)
            if settings.search_type == "mmr":
                return self._retrieve_mmr(query_vector, top_k, where)
            return self._retrieve_similarity(query_vector, top_k, where)
        except RetrievalError:
            raise
        except Exception as exc:
            logger.exception("Retrieval failed")
            raise RetrievalError("Could not retrieve document context.") from exc

    def _retrieve_similarity(self, query_vector: list[float], top_k: int, where: dict | None) -> list[StoredChunk]:
        return self._store.query(query_embedding=query_vector, top_k=top_k, where=where)

    def _retrieve_mmr(self, query_vector: list[float], top_k: int, where: dict | None) -> list[StoredChunk]:
        candidates = self._store.query(query_embedding=query_vector, top_k=max(top_k * 4, 10), where=where)
        if len(candidates) <= top_k:
            return candidates
        candidate_vectors = self._embedder.embed_texts([item.text for item in candidates])
        diversity_weight = settings.mmr_diversity
        selected = [min(range(len(candidates)), key=lambda i: candidates[i].distance)]
        remaining = set(range(len(candidates))) - set(selected)

        while len(selected) < top_k and remaining:
            def score(index: int) -> float:
                # Chroma cosine distance is 1 - cosine similarity (range 0..2).
                relevance = 1.0 - candidates[index].distance
                redundancy = max(
                    _cosine_similarity(candidate_vectors[index], candidate_vectors[chosen])
                    for chosen in selected
                )
                return (1.0 - diversity_weight) * relevance - diversity_weight * redundancy

            best = max(remaining, key=score)
            selected.append(best)
            remaining.remove(best)
        return [candidates[index] for index in selected]
