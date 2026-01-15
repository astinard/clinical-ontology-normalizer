"""Document API endpoints."""

import logging
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.queue import QUEUE_NAMES, enqueue_job
from app.jobs import process_document
from app.models import Document as DocumentModel
from app.schemas import DocumentCreate, JobStatus
from app.schemas.document import Document, DocumentUploadResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["Documents"])

# Type alias for database session dependency (avoids B008 linting issue)
DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.post(
    "",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a clinical document",
    description="Upload a clinical note for NLP processing. Returns document ID and job ID for tracking.",
)
async def upload_document(
    document: DocumentCreate,
    db: DbSession,
) -> DocumentUploadResponse:
    """Upload a clinical document for processing.

    Creates a new document record and queues it for NLP processing.
    The job_id can be used to track processing status.

    Args:
        document: The document to upload.
        db: Database session.

    Returns:
        DocumentUploadResponse with document_id and job_id.
    """
    # Generate job_id upfront
    job_id = uuid4()

    # Create document record with job_id
    db_document = DocumentModel(
        patient_id=document.patient_id,
        note_type=document.note_type,
        text=document.text,
        extra_metadata=document.metadata,
        status=JobStatus.QUEUED,
        job_id=job_id,
    )
    db.add(db_document)
    await db.flush()  # Get the ID without committing

    # Enqueue processing job
    try:
        enqueue_job(
            process_document,
            str(db_document.id),
            queue_name=QUEUE_NAMES["document"],
            job_id=job_id,
        )
        logger.info(f"Enqueued document processing job {job_id} for document {db_document.id}")
    except ImportError:
        # RQ not available - job won't be processed but API still works
        logger.warning("RQ not available, document will not be processed automatically")
    except Exception as e:
        # Redis not available - log warning but don't fail the upload
        logger.warning(f"Failed to enqueue job: {e}. Document saved but not queued.")

    return DocumentUploadResponse(
        document_id=UUID(db_document.id),
        job_id=job_id,
        status=JobStatus.QUEUED,
    )


@router.get(
    "/{doc_id}",
    response_model=Document,
    summary="Get a clinical document",
    description="Retrieve a clinical document by its ID.",
)
async def get_document(
    doc_id: UUID,
    db: DbSession,
) -> Document:
    """Retrieve a clinical document by ID.

    Args:
        doc_id: The UUID of the document to retrieve.
        db: Database session.

    Returns:
        Document with all fields including processing status.

    Raises:
        HTTPException: 404 if document not found.
    """
    stmt = select(DocumentModel).where(DocumentModel.id == str(doc_id))
    result = await db.execute(stmt)
    document = result.scalar_one_or_none()

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {doc_id} not found",
        )

    return Document(
        id=UUID(document.id),
        patient_id=document.patient_id,
        note_type=document.note_type,
        text=document.text,
        metadata=document.extra_metadata,
        status=document.status,
        job_id=document.job_id,
        created_at=document.created_at,
        processed_at=document.processed_at,
    )
