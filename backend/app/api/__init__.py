"""API routers for Clinical Ontology Normalizer."""

from app.api.dashboard import router as dashboard_router
from app.api.documents import router as documents_router
from app.api.export import router as export_router
from app.api.fhir import router as fhir_router
from app.api.jobs import router as jobs_router
from app.api.patients import router as patients_router
from app.api.search import router as search_router

__all__ = [
    "dashboard_router",
    "documents_router",
    "export_router",
    "fhir_router",
    "jobs_router",
    "patients_router",
    "search_router",
]
