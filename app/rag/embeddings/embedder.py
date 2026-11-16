"""Sentence-Transformers embedding generation."""

from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.config.settings import settings
from app.utils.exceptions import EmbeddingError
from app.utils.logger import get_logger

logger = get_logger(__name__)


@lru_cache
def _load_model(model_name: str) -> SentenceTransformer:
    logger.info("Loading embedding model '%s'", model_name)
    return SentenceTransformer(model_name)


class Embedder:
    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or settings.embedding_model
        self._model = _load_model(self.model_name)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            vectors = self._model.encode(
                texts,
                batch_size=settings.embedding_batch_size,
                show_progress_bar=False,
                convert_to_numpy=True,
            )
        except Exception as exc:
            logger.exception("Embedding generation failed")
            raise EmbeddingError("Failed to generate text embeddings.") from exc
        return vectors.tolist()

    def embed_query(self, query: str) -> list[float]:
        vectors = self.embed_texts([query])
        return vectors[0]
