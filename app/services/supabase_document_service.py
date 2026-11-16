"""PDF ingestion and lifecycle backed by Supabase Storage and pgvector."""
from pathlib import Path
import uuid
from app.rag.chunking.chunker import get_chunker
from app.rag.embeddings.embedder import Embedder
from app.rag.loader.pdf_loader import PDFLoader
from app.services.supabase_rest import SupabaseREST
from app.utils.hashing import hash_file
class SupabaseDocumentService:
    def __init__(self,user):
        self.user=user; self.db=SupabaseREST(user["access_token"]); self.loader=PDFLoader(); self.chunker=get_chunker(); self.embedder=Embedder()
    def upload_and_index(self,file_path,filename):
        path=Path(file_path); digest=hash_file(path)
        dup=self.db.req("GET","/rest/v1/documind_documents",{"select":"id","content_hash":f"eq.{digest}","limit":"1"})
        if dup: raise ValueError("This PDF has already been uploaded.")
        did=str(uuid.uuid4()); storage=f'{self.user["id"]}/{did}.pdf'
        self.db.upload(storage,path.read_bytes())
        try:
            self.db.insert_doc({"id":did,"owner_id":self.user["id"],"filename":filename,"storage_path":storage,"content_hash":digest,"status":"processing"})
            doc=self.loader.load(path); chunks=self.chunker.split(doc.full_text,filename)
            vectors=self.embedder.embed_texts([c.text for c in chunks])
            rows=[{"owner_id":self.user["id"],"document_id":did,"chunk_index":c.chunk_index,"content":c.text,"embedding":"["+ ",".join(str(float(v)) for v in vec)+"]","metadata":{"source_filename":filename,"chunk_index":c.chunk_index}} for c,vec in zip(chunks,vectors)]
            self.db.insert_chunks(rows); self.db.update_doc(did,{"status":"ready","chunks_count":len(rows)})
            return len(rows)
        except Exception:
            self.db.update_doc(did,{"status":"failed"}); self.db.remove(storage); raise
    def list_documents(self): return self.db.list_docs()
    def delete_document(self,filename):
        row=self.db.get_doc(filename)
        if not row: raise KeyError(filename)
        self.db.delete_doc(row["id"]); self.db.remove(row["storage_path"])
