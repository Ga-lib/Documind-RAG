"""
Pydantic request/response schemas for the API layer.

These models define the exact shape of data the API accepts and returns.
FastAPI uses them to validate incoming requests automatically and to
generate the Swagger/OpenAPI documentation.
"""

from pydantic import BaseModel, Field


# --- /upload ---

class UploadResponse(BaseModel):
    filename: str
    chunks_created: int
    message: str


# --- /ask ---

class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, description="The user's question")
    top_k: int | None = Field(
        default=None, ge=1, le=20, description="Number of chunks to retrieve"
    )
    source_filename: str | None = Field(
        default=None, description="Restrict search to a specific document"
    )


class SourceCitation(BaseModel):
    source_number: int
    filename: str
    chunk_index: int
    text_snippet: str
    distance: float


class AskResponse(BaseModel):
    question: str
    answer: str
    sources: list[SourceCitation]


# --- /documents ---

class DocumentInfo(BaseModel):
    filename: str


class DocumentListResponse(BaseModel):
    documents: list[DocumentInfo]
    count: int


class DeleteDocumentResponse(BaseModel):
    filename: str
    message: str


# --- /health ---

class HealthResponse(BaseModel):
    status: str
    app_name: str
    version: str


# --- Generic error response ---

class ErrorResponse(BaseModel):
    error: str
    detail: str