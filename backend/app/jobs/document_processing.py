"""Document processing job functions."""

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.database import get_sync_engine
from app.models import Document
from app.models.mention import Mention
from app.schemas.base import JobStatus
from app.services.nlp_rule_based import RuleBasedNLPService

logger = logging.getLogger(__name__)

# Singleton NLP service for reuse across job calls
_nlp_service: RuleBasedNLPService | None = None


def get_nlp_service() -> RuleBasedNLPService:
    """Get or create the NLP service singleton."""
    global _nlp_service
    if _nlp_service is None:
        _nlp_service = RuleBasedNLPService()
    return _nlp_service


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

            logger.info(
                f"Processing document: patient_id={document.patient_id}, "
                f"note_type={document.note_type}"
            )

            # Phase 4: Extract mentions using NLP service
            nlp_service = get_nlp_service()
            extracted_mentions = nlp_service.extract_mentions(
                text=document.text,
                document_id=UUID(document_id),
                note_type=document.note_type,
            )

            logger.info(f"Extracted {len(extracted_mentions)} mentions from document")

            # Create Mention records in database
            mention_records: list[Mention] = []
            for extracted in extracted_mentions:
                mention = Mention(
                    document_id=document_id,
                    text=extracted.text,
                    start_offset=extracted.start_offset,
                    end_offset=extracted.end_offset,
                    lexical_variant=extracted.lexical_variant,
                    section=extracted.section,
                    assertion=extracted.assertion,
                    temporality=extracted.temporality,
                    experiencer=extracted.experiencer,
                    confidence=extracted.confidence,
                )
                mention_records.append(mention)
                session.add(mention)

            session.flush()  # Assign IDs to mentions

            # TODO: Phase 5 - Map mentions to OMOP concepts
            # for mention in mention_records:
            #     mapping_service.map_to_concepts(mention)

            # TODO: Phase 6 - Create ClinicalFacts
            # fact_builder.create_facts(document.id, mention_records)

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

            logger.info(
                f"Document processing completed for document_id={document_id}, "
                f"mention_count={len(mention_records)}"
            )

            return {
                "success": True,
                "document_id": document_id,
                "patient_id": document.patient_id,
                "mention_count": len(mention_records),
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
