"""Request-scoped service dependencies; every service carries the caller's JWT."""
from fastapi import Depends
from app.api.supabase_auth import get_current_user
from app.services.supabase_document_service import SupabaseDocumentService
from app.services.supabase_qa_service import SupabaseQAService
def get_document_service(user:dict=Depends(get_current_user)): return SupabaseDocumentService(user)
def get_qa_service(user:dict=Depends(get_current_user)): return SupabaseQAService(user)
