"""
Embedding generation using Sentence-Transformers.

Converts text chunks into dense vectors that capture semantic meaning,
so that similarity search later can find chunks related to a query even
when they don't share exact keywords.
"""

from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.config.settings import settings
from app.utils.exceptions import EmbeddingError
from app.utils.logger import get_logger

logger = get_logger(__name__)


@lru_cache
def _load_model(model_name: str) -> SentenceTransformer:
    """
    Load and cache the Sentence-Transformers model.

    lru_cache ensures the (relatively expensive) model load only happens
    once per process, even if Embedder() is instantiated multiple times.
    """
    logger.info(f"Loading embedding model '{model_name}' (first run downloads it)")
    model = SentenceTransformer(model_name)
    logger.info(f"Embedding model '{model_name}' loaded successfully")
    return model


class Embedder:
    """Generates vector embeddings for text using a Sentence-Transformers model."""

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or settings.embedding_model
        self._model = _load_model(self.model_name)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        Embed a batch of texts into vectors.

        Batching (rather than one-at-a-time) is significantly faster on
        both CPU and GPU, which is why chunks should be embedded together
        rather than individually.

        Raises:
            EmbeddingError: if the model fails to produce embeddings.
        """
        if not texts:
            return []

        try:
            vectors = self._model.encode(
                texts,
                batch_size=32,
                show_progress_bar=False,
                convert_to_numpy=True,
            )
        except Exception as exc:
            logger.error(f"Embedding generation failed: {exc}")
            raise EmbeddingError(f"Failed to generate embeddings: {exc}") from exc

        logger.info(f"Generated {len(vectors)} embeddings (dim={vectors.shape[1]})")
        return vectors.tolist()

    def embed_query(self, query: str) -> list[float]:
        """Embed a single query string (convenience wrapper for search-time use)."""
        return self.embed_texts([query])[0]