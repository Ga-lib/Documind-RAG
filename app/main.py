"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.api.routes import ask, documents, health, upload
from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("%s v%s starting", settings.app_name, settings.app_version)
    yield
    logger.info("%s shutting down", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="A retrieval-augmented document question-answering system.",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(documents.router)
app.include_router(upload.router)
app.include_router(ask.router)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/config", include_in_schema=False)
def public_client_config():
    return {"supabase_url": settings.supabase_url, "supabase_anon_key": settings.supabase_anon_key}

@app.get("/", include_in_schema=False)
def serve_frontend():
    return FileResponse(STATIC_DIR / "index.html")
