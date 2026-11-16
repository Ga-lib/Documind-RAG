"""Unauthenticated liveness endpoint for load balancers and container healthchecks."""

from fastapi import APIRouter

from app.config.settings import settings
from app.models.schemas import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse(status="ok", app_name=settings.app_name, version=settings.app_version)
