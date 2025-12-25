"""
FastAPI main application for SecureDoc Flow Privacy Proxy.
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
from contextlib import asynccontextmanager

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
    logger.info("Shutting down SecureDoc Flow Privacy Proxy")


app = FastAPI(
    title="SecureDoc Flow Privacy Proxy",
    description="MedTech AI Privacy Proxy with PHI anonymization",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler that doesn't log request bodies."""
    logger.error(f"Unhandled exception: {type(exc).__name__}: {str(exc)}")
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
