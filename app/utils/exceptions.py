"""
Custom exception hierarchy for DocuMind RAG.

Using specific exception types (instead of generic Exception/ValueError)
lets the API layer catch each one and return the correct HTTP status code
and a clear message, instead of leaking a raw stack trace to the client.
"""


class DocuMindError(Exception):
    """Base class for all custom exceptions in this application."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


# --- Document loading errors ---

class DocumentError(DocuMindError):
    """Base class for errors related to document loading/processing."""


class FileNotFoundInStoreError(DocumentError):
    """Raised when a requested document ID does not exist."""


class UnsupportedFileTypeError(DocumentError):
    """Raised when an uploaded file is not an allowed type (e.g. not a PDF)."""


class CorruptedPDFError(DocumentError):
    """Raised when a PDF file cannot be parsed/read."""


class EmptyDocumentError(DocumentError):
    """Raised when a PDF contains no extractable text."""


class DuplicateDocumentError(DocumentError):
    """Raised when an uploaded document is a duplicate of an existing one."""


class FileTooLargeError(DocumentError):
    """Raised when an uploaded file exceeds the configured size limit."""


# --- Embedding / vector store errors ---

class EmbeddingError(DocuMindError):
    """Raised when embedding generation fails."""


class VectorStoreError(DocuMindError):
    """Raised when a vector database operation (insert/query/delete) fails."""


# --- LLM / generation errors ---

class LLMError(DocuMindError):
    """Base class for errors from the LLM provider."""


class LLMTimeoutError(LLMError):
    """Raised when the LLM API call times out."""


class LLMAPIError(LLMError):
    """Raised when the LLM API returns an error response."""


# --- Retrieval errors ---

class RetrievalError(DocuMindError):
    """Raised when the retrieval step fails."""