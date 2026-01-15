"""Document and StructuredResource schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.base import JobStatus, ResourceType


class DocumentCreate(BaseModel):
    """Schema for creating a new document."""

    patient_id: str = Field(..., description="Patient identifier")
    note_type: str = Field(..., description="Type of clinical note (progress_note, discharge_summary, etc.)")
    text: str = Field(..., description="Raw clinical note text")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class Document(BaseModel):
    """Schema for a clinical document."""

    id: UUID = Field(..., description="Unique document identifier")
    patient_id: str = Field(..., description="Patient identifier")
    note_type: str = Field(..., description="Type of clinical note")
    text: str = Field(..., description="Raw clinical note text")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    status: JobStatus = Field(default=JobStatus.QUEUED, description="Processing status")
    job_id: UUID | None = Field(None, description="Processing job ID")
    created_at: datetime = Field(..., description="When the document was uploaded")
    processed_at: datetime | None = Field(None, description="When processing completed")

    model_config = {"from_attributes": True}


class DocumentUploadResponse(BaseModel):
    """Response from document upload."""

    document_id: UUID = Field(..., description="ID of the uploaded document")
    job_id: UUID = Field(..., description="ID of the processing job")
    status: JobStatus = Field(..., description="Initial job status")


class StructuredResourceCreate(BaseModel):
    """Schema for creating a structured resource (FHIR/CSV)."""

    patient_id: str = Field(..., description="Patient identifier")
    resource_type: ResourceType = Field(..., description="Type of structured resource")
    payload: dict[str, Any] = Field(..., description="The structured data payload")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class StructuredResource(BaseModel):
    """Schema for a structured clinical resource."""

    id: UUID = Field(..., description="Unique resource identifier")
    patient_id: str = Field(..., description="Patient identifier")
    resource_type: ResourceType = Field(..., description="Type of resource (fhir_bundle, csv)")
    payload: dict[str, Any] = Field(..., description="The structured data payload")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    status: JobStatus = Field(default=JobStatus.QUEUED, description="Processing status")
    created_at: datetime = Field(..., description="When the resource was uploaded")
    processed_at: datetime | None = Field(None, description="When processing completed")

    model_config = {"from_attributes": True}
