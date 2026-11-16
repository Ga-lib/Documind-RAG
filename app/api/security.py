"""API-key authentication for state-changing and document-data endpoints."""

import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

from app.config.settings import settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(provided_key: str | None = Depends(_api_key_header)) -> None:
    # Local development remains frictionless. Production refuses to start
    # unless DOCUMIND_API_KEY is configured in Settings.
    expected = settings.documind_api_key
    if expected is None:
        return
    if provided_key is None or not secrets.compare_digest(provided_key, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A valid X-API-Key header is required.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
