"""
Health check endpoint — used by monitoring tools, load balancers, and
Docker healthchecks to verify the service is up and responding.
"""

from fastapi import APIRouter

from app.config.settings import settings
from app.models.schemas import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Return basic service status and version info."""
    return HealthResponse(
        status="ok",
        app_name=settings.app_name,
        version=settings.app_version,
    )