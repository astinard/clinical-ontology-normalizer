"""API routers for Clinical Ontology Normalizer."""

from app.api.documents import router as documents_router
from app.api.export import router as export_router
from app.api.jobs import router as jobs_router
from app.api.patients import router as patients_router

__all__ = ["documents_router", "export_router", "jobs_router", "patients_router"]
