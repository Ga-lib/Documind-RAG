"""
FastAPI application entrypoint.

Wires together all route modules, configures CORS, and exposes the app
that Uvicorn serves.
"""

from fastapi import FastAPI

from app.api.routes import ask, documents, health, upload
from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="A production-style RAG system for document question-answering.",
)

app.include_router(health.router)
app.include_router(documents.router)
app.include_router(upload.router)
app.include_router(ask.router)


@app.on_event("startup")
def on_startup():
    logger.info(f"{settings.app_name} v{settings.app_version} starting up")