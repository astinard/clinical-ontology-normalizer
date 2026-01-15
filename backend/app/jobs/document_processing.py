"""Document processing job functions."""

import logging
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.database import get_sync_engine
from app.models import Document
from app.schemas.base import JobStatus

logger = logging.getLogger(__name__)


def process_document(document_id: str) -> dict:
    """Process a clinical document through the NLP pipeline.

    This function is executed by an RQ worker. It performs:
    1. Updates document status to PROCESSING
    2. Extracts mentions from the document text (Phase 4)
    3. Maps mentions to OMOP concepts (Phase 5)
    4. Creates ClinicalFacts (Phase 6)
    5. Updates document status to COMPLETED or FAILED

    Args:
        document_id: The UUID of the document to process.

    Returns:
        Dictionary with processing results including mention count.
    """
    logger.info(f"Starting document processing for document_id={document_id}")

    try:
        with Session(get_sync_engine()) as session:
            # Update status to PROCESSING
            session.execute(
                update(Document)
                .where(Document.id == document_id)
                .values(status=JobStatus.PROCESSING)
            )
            session.commit()

            # Fetch the document
            stmt = select(Document).where(Document.id == document_id)
            result = session.execute(stmt)
            document = result.scalar_one_or_none()

            if document is None:
                logger.error(f"Document not found: {document_id}")
                return {"success": False, "error": "Document not found"}

            # Placeholder: NLP processing will be implemented in Phase 4
            # For now, just mark as completed
            logger.info(f"Processing document: patient_id={document.patient_id}, note_type={document.note_type}")

            # TODO: Phase 4 - Extract mentions using NLP service
            # mentions = nlp_service.extract_mentions(document.text)

            # TODO: Phase 5 - Map mentions to OMOP concepts
            # for mention in mentions:
            #     mapping_service.map_to_concepts(mention)

            # TODO: Phase 6 - Create ClinicalFacts
            # fact_builder.create_facts(document.id, mentions)

            # Update status to COMPLETED
            session.execute(
                update(Document)
                .where(Document.id == document_id)
                .values(
                    status=JobStatus.COMPLETED,
                    processed_at=datetime.now(UTC),
                )
            )
            session.commit()

            logger.info(f"Document processing completed for document_id={document_id}")

            return {
                "success": True,
                "document_id": document_id,
                "patient_id": document.patient_id,
                "mention_count": 0,  # Will be populated in Phase 4
            }

    except Exception as e:
        logger.exception(f"Error processing document {document_id}: {e}")

        # Try to update status to FAILED
        try:
            with Session(get_sync_engine()) as session:
                session.execute(
                    update(Document)
                    .where(Document.id == document_id)
                    .values(status=JobStatus.FAILED)
                )
                session.commit()
        except Exception:
            logger.exception("Failed to update document status to FAILED")

        return {"success": False, "error": str(e)}
