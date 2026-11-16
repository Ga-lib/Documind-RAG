"""Validate Supabase user sessions against the Auth server."""
import requests
from fastapi import Depends,HTTPException
from fastapi.security import HTTPBearer,HTTPAuthorizationCredentials
from app.config.settings import settings
_bearer=HTTPBearer(auto_error=False)
def get_current_user(credentials: HTTPAuthorizationCredentials|None=Depends(_bearer)):
    if not credentials or credentials.scheme.lower()!="bearer": raise HTTPException(401,"Sign in to continue.")
    try:
        r=requests.get(settings.supabase_url.rstrip("/")+"/auth/v1/user",headers={"apikey":settings.supabase_anon_key,"Authorization":f"Bearer {credentials.credentials}"},timeout=settings.supabase_timeout_seconds)
        if r.status_code!=200: raise ValueError("Invalid session")
        u=r.json()
        if not u.get("id"): raise ValueError("Missing user id")
        return {"id":u["id"],"access_token":credentials.credentials}
    except Exception as exc: raise HTTPException(401,"Session expired. Please sign in again.") from exc
