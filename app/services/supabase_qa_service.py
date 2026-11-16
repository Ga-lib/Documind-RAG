"""RLS-scoped vector retrieval and grounded answer generation."""
from app.models.schemas import SourceCitation
from app.rag.embeddings.embedder import Embedder
from app.rag.generator.generator import Generator
from app.services.supabase_rest import AuthenticatedUser, SupabaseREST
from app.vectorstore.chroma_store import StoredChunk


class SupabaseQAService:
    def __init__(self, user: AuthenticatedUser):
        self.db = SupabaseREST(user.access_token)
        self.embedder = Embedder()
        self.generator = Generator()

    def ask(self, question: str, top_k: int | None = None, source_filename: str | None = None):
        document_id = None
        if source_filename:
            doc = self.db.get_document(source_filename)
            if not doc or doc["status"] != "ready":
                return "I could not find relevant information in the indexed documents.", []
            document_id = doc["id"]
        matches = self.db.search_chunks(self.embedder.embed_query(question), top_k or 4, document_id)
        chunks = [StoredChunk(
            id=row["id"], text=row["content"],
            metadata={"source_filename":row["filename"], "chunk_index":row["chunk_index"]},
            distance=1.0 - float(row["similarity"])
        ) for row in matches]
        result = self.generator.generate(question, chunks)
        citations = [SourceCitation(source_number=i, filename=c.metadata.get("source_filename","unknown"),
            chunk_index=c.metadata.get("chunk_index",-1), text_snippet=c.text[:200], distance=c.distance)
            for i,c in enumerate(result.sources,1)]
        return result.answer, citations
