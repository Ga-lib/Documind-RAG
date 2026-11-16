"""Unit tests for retrieval ranking and MMR behavior."""

from app.config.settings import settings
from app.rag.retriever.retriever import Retriever
from app.vectorstore.chroma_store import StoredChunk


class FakeStore:
    def __init__(self, chunks):
        self.chunks = chunks
        self.requested_top_k = None

    def query(self, query_embedding, top_k, where=None):
        self.requested_top_k = top_k
        return self.chunks[:top_k]


class FakeEmbedder:
    def embed_query(self, query):
        return [1.0, 0.0]

    def embed_texts(self, texts):
        vectors = {"best": [1.0, 0.0], "near-duplicate": [0.99, 0.01], "different": [0.0, 1.0]}
        return [vectors[text] for text in texts]


def test_similarity_retrieval_uses_requested_top_k(monkeypatch):
    monkeypatch.setattr(settings, "search_type", "similarity")
    chunks = [StoredChunk(str(i), str(i), {}, 0.1 * i) for i in range(3)]
    store = FakeStore(chunks)
    result = Retriever(store=store, embedder=FakeEmbedder()).retrieve("question", top_k=2)
    assert len(result) == 2
    assert store.requested_top_k == 2


def test_mmr_penalizes_redundant_candidates(monkeypatch):
    monkeypatch.setattr(settings, "search_type", "mmr")
    monkeypatch.setattr(settings, "mmr_diversity", 0.8)
    chunks = [StoredChunk("1", "best", {}, 0.05), StoredChunk("2", "near-duplicate", {}, 0.08), StoredChunk("3", "different", {}, 0.2)]
    store = FakeStore(chunks)
    result = Retriever(store=store, embedder=FakeEmbedder()).retrieve("question", top_k=2)
    assert [chunk.id for chunk in result] == ["1", "3"]
    assert store.requested_top_k == 10


def test_blank_question_returns_no_results():
    retriever = Retriever(store=FakeStore([]), embedder=FakeEmbedder())
    assert retriever.retrieve("   ") == []
