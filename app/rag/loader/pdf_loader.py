"""
PDF loading and text extraction.

Responsible for reading a PDF file from disk and turning it into plain
text plus per-page metadata. Deliberately knows nothing about chunking,
embeddings, or the vector store — it only does one job: PDF -> text.
"""

from dataclasses import dataclass, field
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.utils.exceptions import CorruptedPDFError, EmptyDocumentError
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class LoadedPage:
    """Plain text extracted from a single PDF page, with its page number."""

    page_number: int  # 1-indexed, matches how humans refer to PDF pages
    text: str


@dataclass
class LoadedDocument:
    """Result of loading one PDF: all its pages plus basic metadata."""

    filename: str
    pages: list[LoadedPage] = field(default_factory=list)

    @property
    def full_text(self) -> str:
        """Concatenate all pages into one string, in page order."""
        return "\n\n".join(page.text for page in self.pages)

    @property
    def page_count(self) -> int:
        return len(self.pages)


class PDFLoader:
    """Loads a PDF file from disk and extracts its text content."""

    def load(self, file_path: str | Path) -> LoadedDocument:
        """
        Load a PDF and extract text from every page.

        Raises:
            CorruptedPDFError: if the file cannot be parsed as a PDF at all.
            EmptyDocumentError: if the PDF parses but contains no extractable
                text (e.g. a scanned image with no OCR layer).
        """
        file_path = Path(file_path)
        logger.info(f"Loading PDF: {file_path.name}")

        try:
            reader = PdfReader(str(file_path))
        except PdfReadError as exc:
            logger.error(f"Failed to parse PDF '{file_path.name}': {exc}")
            raise CorruptedPDFError(
                f"'{file_path.name}' could not be read as a valid PDF. "
                "The file may be corrupted or not a real PDF."
            ) from exc
        except Exception as exc:
            # pypdf can raise several underlying exception types for bad
            # files; anything we didn't anticipate is still a corrupted-PDF
            # situation from the caller's point of view.
            logger.error(f"Unexpected error opening '{file_path.name}': {exc}")
            raise CorruptedPDFError(
                f"'{file_path.name}' could not be opened. Error: {exc}"
            ) from exc

        if reader.is_encrypted:
            logger.error(f"PDF '{file_path.name}' is password-protected")
            raise CorruptedPDFError(
                f"'{file_path.name}' is password-protected and cannot be read."
            )

        pages: list[LoadedPage] = []
        for i, page in enumerate(reader.pages, start=1):
            try:
                text = page.extract_text() or ""
            except Exception as exc:
                logger.warning(
                    f"Could not extract text from page {i} of "
                    f"'{file_path.name}': {exc}. Skipping this page."
                )
                text = ""
            pages.append(LoadedPage(page_number=i, text=text.strip()))

        document = LoadedDocument(filename=file_path.name, pages=pages)

        if not document.full_text.strip():
            logger.error(f"PDF '{file_path.name}' contains no extractable text")
            raise EmptyDocumentError(
                f"'{file_path.name}' contains no extractable text. "
                "It may be a scanned image without OCR, or a blank document."
            )

        logger.info(
            f"Loaded '{file_path.name}': {document.page_count} pages, "
            f"{len(document.full_text)} characters"
        )
        return document