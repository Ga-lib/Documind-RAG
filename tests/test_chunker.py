"""
Unit tests for the chunking strategies.
"""

import pytest

from app.rag.chunking.chunker import FixedSizeChunker, RecursiveChunker


class TestFixedSizeChunker:
    def test_splits_text_into_chunks(self):
        chunker = FixedSizeChunker(chunk_size=10, chunk_overlap=2)
        text = "a" * 25

        chunks = chunker.split(text, source_filename="test.pdf")

        assert len(chunks) > 1
        assert all(c.source_filename == "test.pdf" for c in chunks)

    def test_chunk_indices_are_sequential(self):
        chunker = FixedSizeChunker(chunk_size=10, chunk_overlap=2)
        text = "a" * 25

        chunks = chunker.split(text, source_filename="test.pdf")

        indices = [c.chunk_index for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_empty_text_produces_no_chunks(self):
        chunker = FixedSizeChunker(chunk_size=10, chunk_overlap=2)

        chunks = chunker.split("", source_filename="test.pdf")

        assert chunks == []

    def test_short_text_produces_one_chunk(self):
        chunker = FixedSizeChunker(chunk_size=1000, chunk_overlap=200)
        text = "Short text."

        chunks = chunker.split(text, source_filename="test.pdf")

        assert len(chunks) == 1
        assert chunks[0].text == "Short text."


class TestRecursiveChunker:
    def test_splits_long_text_into_multiple_chunks(self):
        chunker = RecursiveChunker(chunk_size=50, chunk_overlap=10)
        text = "This is a sentence. " * 20

        chunks = chunker.split(text, source_filename="test.pdf")

        assert len(chunks) > 1

    def test_prefers_paragraph_boundaries(self):
        chunker = RecursiveChunker(chunk_size=30, chunk_overlap=5)
        text = "First paragraph here.\n\nSecond paragraph here."

        chunks = chunker.split(text, source_filename="test.pdf")

        assert all(c.text.strip() for c in chunks)
        combined = " ".join(c.text for c in chunks)
        assert "First paragraph" in combined
        assert "Second paragraph" in combined

    def test_empty_text_produces_no_chunks(self):
        chunker = RecursiveChunker(chunk_size=1000, chunk_overlap=200)

        chunks = chunker.split("", source_filename="test.pdf")

        assert chunks == []

    @pytest.mark.parametrize("chunk_size,overlap", [(100, 20), (500, 100), (1000, 200)])
    def test_various_configurations_do_not_error(self, chunk_size, overlap):
        chunker = RecursiveChunker(chunk_size=chunk_size, chunk_overlap=overlap)
        text = "Some reasonably long text content. " * 50

        chunks = chunker.split(text, source_filename="test.pdf")

        assert len(chunks) > 0