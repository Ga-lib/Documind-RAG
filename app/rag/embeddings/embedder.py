"""Memory-efficient ONNX embedding generation with FastEmbed."""

from functools import lru_cache

from fastembed import TextEmbedding

from app.config.settings import settings
from app.utils.exceptions import EmbeddingError
from app.utils.logger import get_logger

logger = get_logger(__name__)


@lru_cache
def _load_model(model_name: str) -> TextEmbedding:
    """Load the ONNX-backed embedding model once per process."""
    logger.info("Loading FastEmbed model '%s'", model_name)
    return TextEmbedding(model_name=model_name)


class Embedder:
    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or settings.embedding_model
        self._model = _load_model(self.model_name)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            vectors = self._model.embed(
                texts,
                batch_size=settings.embedding_batch_size,
            )
            return [vector.tolist() for vector in vectors]
        except Exception as exc:
            logger.exception("Embedding generation failed")
            raise EmbeddingError("Failed to generate text embeddings.") from exc

    def embed_query(self, query: str) -> list[float]:
        try:
            vector = next(self._model.query_embed(query))
            return vector.tolist()
        except Exception as exc:
            logger.exception("Query embedding generation failed")
            raise EmbeddingError("Failed to generate query embedding.") from exc
