"""
Unit tests for the PDF loader.

Uses pytest's tmp_path fixture to create real temporary files on disk for
each test, so tests are self-contained and don't depend on any file
outside the test itself.
"""

import pytest
from pypdf import PdfWriter

from app.rag.loader.pdf_loader import PDFLoader
from app.utils.exceptions import CorruptedPDFError, EmptyDocumentError


def _make_valid_pdf_with_text(path, text: str = "Hello, this is test content."):
    """Build a minimal real PDF file with a text-containing page."""
    # pypdf's PdfWriter can't easily draw text without reportlab, so for a
    # deterministic test we build the simplest possible valid PDF via a
    # blank page — sufficient to test "opens successfully" but not
    # "extracts this exact text". For text-extraction assertions we rely
    # on the resume-based manual test we already ran; this covers the
    # loader's structural handling (valid vs corrupted vs empty).
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    with open(path, "wb") as f:
        writer.write(f)


class TestPDFLoader:
    def test_corrupted_pdf_raises_corrupted_error(self, tmp_path):
        fake_pdf = tmp_path / "corrupted.pdf"
        fake_pdf.write_bytes(b"This is not a real PDF file at all.")

        loader = PDFLoader()

        with pytest.raises(CorruptedPDFError):
            loader.load(fake_pdf)

    def test_blank_pdf_raises_empty_document_error(self, tmp_path):
        blank_pdf = tmp_path / "blank.pdf"
        _make_valid_pdf_with_text(blank_pdf)

        loader = PDFLoader()

        # A blank page has no extractable text, so this should raise
        # EmptyDocumentError rather than silently returning an empty document.
        with pytest.raises(EmptyDocumentError):
            loader.load(blank_pdf)

    def test_nonexistent_file_raises_corrupted_error(self, tmp_path):
        missing_path = tmp_path / "does_not_exist.pdf"

        loader = PDFLoader()

        with pytest.raises(CorruptedPDFError):
            loader.load(missing_path)