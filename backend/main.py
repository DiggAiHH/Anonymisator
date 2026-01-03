"""
FastAPI main application for SecureDoc Flow Privacy Proxy.
"""
import os
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from backend.routers import securedoc, billing

# Configure logging to exclude request bodies
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    logger.info("Starting SecureDoc Flow Privacy Proxy")
    yield
    try:
        # Close shared HTTP clients (best-effort)
        await securedoc.llm_client.close()
    except Exception:
        logger.warning("Failed to close LLM client")
    logger.info("Shutting down SecureDoc Flow Privacy Proxy")


app = FastAPI(
    title="SecureDoc Flow Privacy Proxy",
    description="MedTech AI Privacy Proxy with PHI anonymization",
    version="1.0.0",
    lifespan=lifespan
)

def _parse_csv_env(name: str) -> list[str]:
    raw = os.getenv(name, "").strip()
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


# CORS (secure-by-default): disabled unless explicitly configured
cors_allow_origins = _parse_csv_env("CORS_ALLOW_ORIGINS")
cors_allow_credentials = _env_bool("CORS_ALLOW_CREDENTIALS", default=False)

if cors_allow_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_allow_origins,
        allow_credentials=cors_allow_credentials,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept", "Origin"],
    )
    logger.info(
        "CORS enabled for %d origin(s) (credentials=%s)",
        len(cors_allow_origins),
        cors_allow_credentials,
    )
else:
    logger.info("CORS disabled (set CORS_ALLOW_ORIGINS to enable)")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler that doesn't log request bodies."""
    # Do not log exception messages, as they can contain personal data.
    logger.error(
        "Unhandled exception: %s (path=%s)",
        type(exc).__name__,
        getattr(getattr(request, "url", None), "path", ""),
    )
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": "An unexpected error occurred"}
    )


# Include routers
app.include_router(securedoc.router, prefix="/v1", tags=["securedoc"])
app.include_router(billing.router, prefix="/v1", tags=["billing"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "SecureDoc Flow Privacy Proxy",
        "version": "1.0.0",
        "status": "operational"
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


_REPO_ROOT = Path(__file__).resolve().parents[1]


def _ui_file(name: str) -> Path:
    return _REPO_ROOT / name


@app.get("/ui/version1")
async def ui_version1():
    path = _ui_file("Version 1.html")
    if not path.exists():
        return JSONResponse(status_code=404, content={"error": "Not found"})
    return FileResponse(path)


@app.get("/ui/version2")
async def ui_version2():
    path = _ui_file("Version 2.html")
    if not path.exists():
        return JSONResponse(status_code=404, content={"error": "Not found"})
    return FileResponse(path)


@app.get("/ui/presentation")
async def ui_presentation():
    path = _ui_file("Präsentation.html")
    if not path.exists():
        return JSONResponse(status_code=404, content={"error": "Not found"})
    return FileResponse(path)
