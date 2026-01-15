"""API routers for Clinical Ontology Normalizer."""

from app.api.documents import router as documents_router
from app.api.jobs import router as jobs_router

__all__ = ["documents_router", "jobs_router"]
