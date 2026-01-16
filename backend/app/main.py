"""FastAPI application for Clinical Ontology Normalizer."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import documents_router, export_router, fhir_router, jobs_router, patients_router, search_router
from app.core.config import settings
from app.core.database import close_db, init_db
from app.core.queue import clear_queues
from app.core.redis import close_redis


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager.

    Handles startup and shutdown events:
    - Startup: Initialize database connection
    - Shutdown: Close database and Redis connections, clear queues
    """
    # Startup
    if settings.debug:
        await init_db()
    yield
    # Shutdown
    clear_queues()
    close_redis()
    await close_db()


app = FastAPI(
    title="Clinical Ontology Normalizer",
    description="API for ingesting clinical data, extracting mentions, mapping to OMOP concepts, and building patient knowledge graphs.",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:3002"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(documents_router)
app.include_router(export_router)
app.include_router(fhir_router)
app.include_router(jobs_router)
app.include_router(patients_router)
app.include_router(search_router)


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, Any]:
    """Health check endpoint.

    Returns service status and basic info for monitoring.
    """
    return {
        "status": "healthy",
        "service": "clinical-ontology-normalizer",
        "version": "0.1.0",
        "timestamp": datetime.now(UTC).isoformat(),
    }


@app.get("/", tags=["Health"])
async def root() -> dict[str, str]:
    """Root endpoint with API info."""
    return {
        "service": "Clinical Ontology Normalizer API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }
