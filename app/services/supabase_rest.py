"""Per-request Supabase REST client. All data access uses the caller JWT so RLS applies."""
from dataclasses import dataclass
from urllib.parse import quote
import requests

from app.config.settings import settings


@dataclass(frozen=True)
class AuthenticatedUser:
    id: str
    access_token: str


class SupabaseREST:
    def __init__(self, access_token: str):
        if not settings.supabase_url or not settings.supabase_anon_key:
            raise RuntimeError("Supabase URL and publishable key are not configured.")
        self.base = settings.supabase_url.rstrip("/")
        self.headers = {
            "apikey": settings.supabase_anon_key,
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        self.timeout = settings.supabase_timeout_seconds

    def request(self, method: str, path: str, *, params=None, json=None, data=None, headers=None):
        merged = {**self.headers, **(headers or {})}
        response = requests.request(
            method, f"{self.base}{path}", headers=merged, params=params,
            json=json, data=data, timeout=self.timeout,
        )
        if not response.ok:
            raise RuntimeError(f"Supabase request failed ({response.status_code}): {response.text[:500]}")
        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    def upload_pdf(self, path: str, content: bytes):
        return self.request(
            "POST", f"/storage/v1/object/{settings.supabase_bucket}/{quote(path, safe='/')}",
            data=content,
            headers={"Content-Type": "application/pdf", "x-upsert": "false"},
        )

    def delete_file(self, path: str):
        return self.request(
            "DELETE", f"/storage/v1/object/{settings.supabase_bucket}/{quote(path, safe='/')}",
            json={"prefixes": [path]},
        )

    def insert_document(self, payload: dict):
        rows = self.request("POST", "/rest/v1/documind_documents",
                            params={"select": "*"}, json=payload,
                            headers={"Prefer": "return=representation"})
        return rows[0]

    def update_document(self, document_id: str, payload: dict):
        return self.request("PATCH", "/rest/v1/documind_documents",
                            params={"id": f"eq.{document_id}"},
                            json=payload, headers={"Prefer": "return=minimal"})

    def insert_chunks(self, rows: list[dict]):
        if rows:
            self.request("POST", "/rest/v1/documind_chunks",
                         json=rows, headers={"Prefer": "return=minimal"})

    def list_documents(self):
        return self.request("GET", "/rest/v1/documind_documents",
                            params={"select": "id,filename,status,chunks_count,created_at",
                                    "order": "created_at.desc"})

    def get_document(self, filename: str):
        rows = self.request("GET", "/rest/v1/documind_documents",
                            params={"select": "id,filename,storage_path,content_hash,status",
                                    "filename": f"eq.{filename}", "limit": "1"})
        return rows[0] if rows else None

    def delete_document(self, document_id: str):
        return self.request("DELETE", "/rest/v1/documind_documents",
                            params={"id": f"eq.{document_id}"})

    def search_chunks(self, embedding: list[float], top_k: int, document_id: str | None = None):
        payload = {"query_embedding": "[" + ",".join(map(str, embedding)) + "]",
                   "match_count": top_k, "filter_document_id": document_id}
        return self.request("POST", "/rest/v1/rpc/match_documind_chunks", json=payload)
