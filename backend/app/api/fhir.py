"""FHIR API endpoints for importing and interacting with FHIR data."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.fhir_import import FHIRImportService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/fhir", tags=["fhir"])


class FHIRImportRequest(BaseModel):
    """Request to import a patient from FHIR."""

    fhir_patient_id: str = Field(..., description="FHIR Patient resource ID")
    internal_patient_id: str | None = Field(
        None, description="Optional internal patient ID (defaults to fhir-{id})"
    )
    fhir_base_url: str = Field(
        "http://localhost:8090/fhir", description="FHIR server base URL"
    )


class FHIRImportResponse(BaseModel):
    """Response from FHIR import."""

    success: bool
    patient_id: str | None = None
    patient_name: str | None = None
    conditions: int = 0
    medications: int = 0
    allergies: int = 0
    observations: int = 0
    procedures: int = 0
    nodes: int = 0
    edges: int = 0
    error: str | None = None


@router.post("/import", response_model=FHIRImportResponse)
async def import_fhir_patient(
    request: FHIRImportRequest,
    session: AsyncSession = Depends(get_db),
) -> FHIRImportResponse:
    """Import a patient from FHIR server into the knowledge graph.

    This endpoint fetches a patient and all their clinical data from a FHIR
    server and creates:
    - Clinical facts for each condition, medication, observation, procedure
    - Knowledge graph nodes and edges representing the patient's clinical data

    Args:
        request: Import request with FHIR patient ID and server URL

    Returns:
        Import summary with counts of imported resources
    """
    logger.info(f"Starting FHIR import for patient {request.fhir_patient_id}")

    service = FHIRImportService(fhir_base_url=request.fhir_base_url)
    try:
        result = await service.import_patient(
            session=session,
            fhir_patient_id=request.fhir_patient_id,
            internal_patient_id=request.internal_patient_id,
        )
        return FHIRImportResponse(**result)
    except Exception as e:
        logger.exception(f"FHIR import failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await service.close()


@router.get("/patients/{fhir_patient_id}")
async def get_fhir_patient(
    fhir_patient_id: str,
    fhir_base_url: str = "http://localhost:8090/fhir",
) -> dict[str, Any]:
    """Fetch a patient directly from the FHIR server.

    This is a convenience endpoint to preview FHIR patient data before import.

    Args:
        fhir_patient_id: FHIR Patient resource ID
        fhir_base_url: FHIR server base URL

    Returns:
        FHIR Patient resource
    """
    service = FHIRImportService(fhir_base_url=fhir_base_url)
    try:
        patient = await service.fetch_patient(fhir_patient_id)
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        return patient
    finally:
        await service.close()


@router.get("/patients/{fhir_patient_id}/summary")
async def get_fhir_patient_summary(
    fhir_patient_id: str,
    fhir_base_url: str = "http://localhost:8090/fhir",
) -> dict[str, Any]:
    """Get a summary of patient data available in FHIR.

    This previews what would be imported without actually importing.

    Args:
        fhir_patient_id: FHIR Patient resource ID
        fhir_base_url: FHIR server base URL

    Returns:
        Summary with counts of each resource type
    """
    service = FHIRImportService(fhir_base_url=fhir_base_url)
    try:
        patient = await service.fetch_patient(fhir_patient_id)
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")

        # Fetch counts of each resource type
        conditions = await service.fetch_patient_resources(fhir_patient_id, "Condition")
        medications = await service.fetch_patient_resources(
            fhir_patient_id, "MedicationRequest"
        )
        allergies = await service.fetch_patient_resources(
            fhir_patient_id, "AllergyIntolerance"
        )
        observations = await service.fetch_patient_resources(
            fhir_patient_id, "Observation"
        )
        procedures = await service.fetch_patient_resources(fhir_patient_id, "Procedure")

        return {
            "fhir_patient_id": fhir_patient_id,
            "patient_name": service._extract_patient_name(patient),
            "gender": patient.get("gender"),
            "birth_date": patient.get("birthDate"),
            "conditions": len(conditions),
            "medications": len(medications),
            "allergies": len(allergies),
            "observations": len(observations),
            "procedures": len(procedures),
            "total_resources": (
                len(conditions)
                + len(medications)
                + len(allergies)
                + len(observations)
                + len(procedures)
            ),
        }
    finally:
        await service.close()
