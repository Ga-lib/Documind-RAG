"""Tenant-scoped PDF ingestion and lifecycle on Supabase Storage/Postgres."""
from pathlib import Path
import uuid

from app.config.settings import settings
from app.rag.chunking.chunker import get_chunker
from app.rag.embeddings.embedder import Embedder
from app.rag.loader.pdf_loader import PDFLoader
from app.services.supabase_rest import AuthenticatedUser, SupabaseREST
from app.utils.hashing import hash_file


class SupabaseDocumentService:
    def __init__(self, user: AuthenticatedUser):
        self.user = user
        self.db = SupabaseREST(user.access_token)
        self.loader = PDFLoader()
        self.chunker = get_chunker()
        self.embedder = Embedder()

    def upload_and_index(self, file_path: str | Path, filename: str) -> int:
        path = Path(file_path)
        digest = hash_file(path)
        existing = self.db.request("GET", "/rest/v1/documind_documents",
            params={"select":"id", "content_hash":f"eq.{digest}", "limit":"1"})
        if existing:
            raise ValueError("This document has already been uploaded.")
        document_id = str(uuid.uuid4())
        storage_path = f"{self.user.id}/{document_id}.pdf"
        self.db.upload_pdf(storage_path, path.read_bytes())
        record = self.db.insert_document({
            "id": document_id, "owner_id": self.user.id, "filename": filename,
            "storage_path": storage_path, "content_hash": digest, "status": "processing"
        })
        try:
            loaded = self.loader.load(path)
            chunks = self.chunker.split(loaded.full_text, filename)
            vectors = self.embedder.embed_texts([chunk.text for chunk in chunks])
            rows = [{
                "owner_id": self.user.id, "document_id": document_id,
                "chunk_index": chunk.chunk_index, "content": chunk.text,
                "embedding": "[" + ",".join(map(str, vector)) + "]",
                "metadata": {"source_filename": filename, "chunk_index": chunk.chunk_index}
            } for chunk, vector in zip(chunks, vectors)]
            self.db.insert_chunks(rows)
            self.db.update_document(document_id, {"status":"ready", "chunks_count":len(rows)})
            return len(rows)
        except Exception:
            self.db.update_document(document_id, {"status":"failed"})
            raise

    def list_documents(self):
        return self.db.list_documents()

    def delete_document(self, filename: str):
        record = self.db.get_document(filename)
        if not record:
            raise KeyError(filename)
        self.db.delete_document(record["id"])
        self.db.delete_file(record["storage_path"])
