"""PDF ingestion and lifecycle backed by Supabase Storage and pgvector."""
from pathlib import Path
import uuid

from app.rag.chunking.chunker import get_chunker
from app.rag.embeddings.embedder import Embedder
from app.rag.loader.pdf_loader import PDFLoader
from app.services.supabase_rest import SupabaseREST
from app.utils.hashing import hash_file
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SupabaseDocumentService:
    def __init__(self, user):
        self.user = user
        self.db = SupabaseREST(user["access_token"])
        self.loader = PDFLoader()
        self.chunker = get_chunker()
        self.embedder = Embedder()

    def upload_and_index(self, file_path, filename):
        path = Path(file_path)
        digest = hash_file(path)

        # The UI addresses documents by filename, so prevent ambiguous
        # selection/deletion when two files share the same name.
        if self.db.get_doc(filename):
            raise ValueError(
                "A document with this filename already exists. Rename the PDF and retry."
            )

        duplicates = self.db.req(
            "GET",
            "/rest/v1/documind_documents",
            {"select": "id", "content_hash": f"eq.{digest}", "limit": "1"},
        )
        if duplicates:
            raise ValueError("This PDF has already been uploaded.")

        document_id = str(uuid.uuid4())
        storage_path = f'{self.user["id"]}/{document_id}.pdf'
        uploaded = False
        record_created = False

        try:
            self.db.upload(storage_path, path.read_bytes())
            uploaded = True

            self.db.insert_doc(
                {
                    "id": document_id,
                    "owner_id": self.user["id"],
                    "filename": filename,
                    "storage_path": storage_path,
                    "content_hash": digest,
                    "status": "processing",
                }
            )
            record_created = True

            document = self.loader.load(path)
            chunks = self.chunker.split(document.full_text, filename)
            if not chunks:
                raise ValueError("No readable text was found in this PDF.")

            vectors = self.embedder.embed_texts([chunk.text for chunk in chunks])
            if len(vectors) != len(chunks):
                raise RuntimeError("Embedding count does not match the chunk count.")

            rows = [
                {
                    "owner_id": self.user["id"],
                    "document_id": document_id,
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.text,
                    "embedding": "[" + ",".join(str(float(value)) for value in vector) + "]",
                    "metadata": {
                        "source_filename": filename,
                        "chunk_index": chunk.chunk_index,
                    },
                }
                for chunk, vector in zip(chunks, vectors)
            ]
            self.db.insert_chunks(rows)
            self.db.update_doc(
                document_id,
                {"status": "ready", "chunks_count": len(rows)},
            )
            return len(rows)

        except Exception:
            # Cleanup must not hide the original ingestion failure. In
            # particular, a failed insert_doc must not prevent storage cleanup.
            if record_created:
                try:
                    self.db.update_doc(document_id, {"status": "failed"})
                except Exception:
                    logger.exception("Could not mark failed document %s", document_id)

            if uploaded:
                try:
                    self.db.remove(storage_path)
                except Exception:
                    logger.exception("Could not remove failed upload %s", storage_path)

            raise

    def list_documents(self):
        return self.db.list_docs()

    def delete_document(self, filename):
        row = self.db.get_doc(filename)
        if not row:
            raise KeyError(filename)

        # Keep the row if storage deletion fails, so the user can retry.
        self.db.remove(row["storage_path"])
        self.db.delete_doc(row["id"])
