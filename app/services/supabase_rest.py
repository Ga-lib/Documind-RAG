"""Supabase REST adapter using caller JWT for RLS."""
import requests
from urllib.parse import quote
from app.config.settings import settings

class SupabaseREST:
    def __init__(self, token):
        if not settings.supabase_url or not settings.supabase_anon_key: raise RuntimeError("Supabase is not configured")
        self.base=settings.supabase_url.rstrip("/")
        self.headers={"apikey":settings.supabase_anon_key,"Authorization":f"Bearer {token}","Content-Type":"application/json"}
    def req(self,method,path,params=None,json=None,data=None,extra=None):
        r=requests.request(method,self.base+path,headers={**self.headers,**(extra or {})},params=params,json=json,data=data,timeout=settings.supabase_timeout_seconds)
        if not r.ok: raise RuntimeError(f"Supabase {r.status_code}: {r.text[:300]}")
        return r.json() if r.content else None
    def upload(self,path,content):
        return self.req("POST",f"/storage/v1/object/{settings.supabase_bucket}/{quote(path,safe='/')}",data=content,extra={"Content-Type":"application/pdf","x-upsert":"false"})
    def remove(self,path):
        return self.req("DELETE",f"/storage/v1/object/{settings.supabase_bucket}",json={"prefixes":[path]})
    def list_docs(self):
        return self.req("GET","/rest/v1/documind_documents",{"select":"id,filename,status,chunks_count,created_at","order":"created_at.desc"})
    def get_doc(self,name):
        rows=self.req("GET","/rest/v1/documind_documents",{"select":"id,filename,storage_path,status,content_hash","filename":f"eq.{name}","limit":"1"})
        return rows[0] if rows else None
    def get_doc_by_id(self,document_id):
        rows=self.req("GET","/rest/v1/documind_documents",{"select":"id,filename,storage_path,status,content_hash","id":f"eq.{document_id}","limit":"1"})
        return rows[0] if rows else None
    def insert_doc(self,row):
        return self.req("POST","/rest/v1/documind_documents",{"select":"id"},row,extra={"Prefer":"return=representation"})[0]
    def update_doc(self,id,row): return self.req("PATCH","/rest/v1/documind_documents",{"id":f"eq.{id}"},row,extra={"Prefer":"return=minimal"})
    def insert_chunks(self,rows):
        if rows: self.req("POST","/rest/v1/documind_chunks",json=rows,extra={"Prefer":"return=minimal"})
    def delete_doc(self,id): return self.req("DELETE","/rest/v1/documind_documents",{"id":f"eq.{id}"},extra={"Prefer":"return=minimal"})
    def search(self,vector,k,docid=None):
        body={"query_embedding":"["+ ",".join(str(float(x)) for x in vector)+"]","match_count":max(1,min(int(k),20)),"filter_document_id":docid}
        return self.req("POST","/rest/v1/rpc/match_documind_chunks",json=body)
