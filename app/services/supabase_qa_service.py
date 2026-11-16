"""User-scoped vector search and grounded answer generation."""
from app.rag.embeddings.embedder import Embedder
from app.rag.generator.generator import Generator
from app.services.supabase_rest import SupabaseREST
from app.vectorstore.chroma_store import StoredChunk
from app.models.schemas import SourceCitation
class SupabaseQAService:
    def __init__(self,user): self.db=SupabaseREST(user["access_token"]); self.embedder=Embedder(); self.generator=Generator()
    def ask(self,question,top_k=None,source_filename=None):
        did=None
        if source_filename:
            doc=self.db.get_doc(source_filename)
            if not doc or doc["status"]!="ready": return "I could not find relevant information in your indexed documents.",[]
            did=doc["id"]
        rows=self.db.search(self.embedder.embed_query(question),top_k or 4,did)
        chunks=[StoredChunk(id=r["id"],text=r["content"],metadata={"source_filename":r["filename"],"chunk_index":r["chunk_index"]},distance=1-float(r["similarity"])) for r in rows]
        result=self.generator.generate(question,chunks)
        cites=[SourceCitation(source_number=i,filename=c.metadata.get("source_filename","unknown"),chunk_index=c.metadata.get("chunk_index",-1),text_snippet=c.text[:200],distance=c.distance) for i,c in enumerate(result.sources,1)]
        return result.answer,cites
