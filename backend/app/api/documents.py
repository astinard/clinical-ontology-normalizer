"""Document API endpoints."""

import logging
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.queue import QUEUE_NAMES, enqueue_job
from app.jobs import process_document
from app.models import Document as DocumentModel
from app.models.mention import Mention as MentionModel
from app.schemas import DocumentCreate, JobStatus
from app.schemas.document import Document, DocumentUploadResponse
from app.schemas.mention import Mention
from app.services.nlp_rule_based import RuleBasedNLPService

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


@router.get(
    "/{doc_id}/mentions",
    response_model=list[Mention],
    summary="Get document mentions",
    description="Retrieve all extracted mentions for a document.",
)
async def get_document_mentions(
    doc_id: UUID,
    db: DbSession,
) -> list[Mention]:
    """Get all mentions extracted from a document.

    Args:
        doc_id: The UUID of the document.
        db: Database session.

    Returns:
        List of Mention objects with text spans and attributes.

    Raises:
        HTTPException: 404 if document not found.
    """
    # Verify document exists
    stmt = select(DocumentModel).where(DocumentModel.id == str(doc_id))
    result = await db.execute(stmt)
    document = result.scalar_one_or_none()

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {doc_id} not found",
        )

    # Get all mentions for this document
    stmt = select(MentionModel).where(MentionModel.document_id == str(doc_id))
    result = await db.execute(stmt)
    mentions = result.scalars().all()

    return [
        Mention(
            id=UUID(m.id),
            document_id=UUID(m.document_id),
            text=m.text,
            start_offset=m.start_offset,
            end_offset=m.end_offset,
            lexical_variant=m.lexical_variant,
            section=m.section,
            assertion=m.assertion,
            temporality=m.temporality,
            experiencer=m.experiencer,
            confidence=m.confidence,
            created_at=m.created_at,
        )
        for m in mentions
    ]


class ExtractPreviewRequest(BaseModel):
    """Request body for live extraction preview."""

    text: str = Field(..., description="Clinical note text to extract from")
    note_type: str | None = Field(None, description="Type of clinical note")


class ExtractedMentionPreview(BaseModel):
    """Preview of an extracted mention (without database IDs)."""

    text: str = Field(..., description="The extracted text span")
    start_offset: int = Field(..., description="Character start position")
    end_offset: int = Field(..., description="Character end position")
    lexical_variant: str = Field(..., description="Normalized form from vocabulary")
    section: str | None = Field(None, description="Clinical section detected")
    assertion: str = Field(..., description="Assertion status (present/absent/possible)")
    temporality: str = Field(..., description="Temporal context (current/past/future)")
    experiencer: str = Field(..., description="Who it applies to (patient/family/other)")
    confidence: float = Field(..., description="Extraction confidence 0.0-1.0")
    domain: str | None = Field(None, description="OMOP domain hint")
    omop_concept_id: int | None = Field(None, description="Matched OMOP concept ID")


class ExtractPreviewResponse(BaseModel):
    """Response from live extraction preview."""

    mentions: list[ExtractedMentionPreview] = Field(..., description="Extracted mentions")
    extraction_time_ms: float = Field(..., description="Time taken for extraction in ms")
    mention_count: int = Field(..., description="Total number of mentions extracted")


@router.post(
    "/preview/extract",
    response_model=ExtractPreviewResponse,
    summary="Preview extraction without saving",
    description="Run NLP extraction on text and return results without saving to database.",
)
async def preview_extraction(
    request: ExtractPreviewRequest,
) -> ExtractPreviewResponse:
    """Run live extraction preview on clinical text.

    This endpoint runs the NLP extraction pipeline on the provided text
    and returns the extracted mentions WITHOUT saving them to the database.
    Useful for testing extraction quality and previewing results.

    Args:
        request: The text to extract from.

    Returns:
        ExtractPreviewResponse with extracted mentions and timing.
    """
    import time

    # Initialize NLP service
    nlp_service = RuleBasedNLPService()

    # Run extraction with timing
    start_time = time.perf_counter()
    extracted = nlp_service.extract_mentions(
        text=request.text,
        document_id=uuid4(),  # Dummy ID for preview
        note_type=request.note_type,
    )
    extraction_time_ms = (time.perf_counter() - start_time) * 1000

    # Convert to preview format
    mentions = [
        ExtractedMentionPreview(
            text=m.text,
            start_offset=m.start_offset,
            end_offset=m.end_offset,
            lexical_variant=m.lexical_variant,
            section=m.section,
            assertion=m.assertion.value,
            temporality=m.temporality.value,
            experiencer=m.experiencer.value,
            confidence=m.confidence,
            domain=m.domain_hint,
            omop_concept_id=m.omop_concept_id,
        )
        for m in extracted
    ]

    return ExtractPreviewResponse(
        mentions=mentions,
        extraction_time_ms=round(extraction_time_ms, 2),
        mention_count=len(mentions),
    )


# ============================================================================
# Value Extraction Endpoints
# ============================================================================

from app.models.clinical_value import ValueType
from app.services.value_extraction import get_value_extraction_service
from app.services.nlp_clinical_ner import get_clinical_ner_service
from app.services.relation_extraction import get_relation_extraction_service, RelationType
from app.services.nlp_ensemble import get_ensemble_nlp_service


class ExtractValuesRequest(BaseModel):
    """Request body for clinical value extraction."""

    text: str = Field(..., description="Clinical note text to extract values from")
    include_vitals: bool = Field(True, description="Extract vital signs")
    include_labs: bool = Field(True, description="Extract lab results")
    include_measurements: bool = Field(True, description="Extract clinical measurements")
    include_medications: bool = Field(True, description="Extract medication doses")


class ExtractedValuePreview(BaseModel):
    """Preview of an extracted clinical value."""

    text: str = Field(..., description="The extracted text span")
    start_offset: int = Field(..., description="Character start position")
    end_offset: int = Field(..., description="Character end position")
    name: str = Field(..., description="Name/label of the measurement")
    value_type: str = Field(..., description="Type of value (vital_sign, lab_result, etc.)")
    value: float | None = Field(None, description="Primary numeric value")
    value_secondary: float | None = Field(None, description="Secondary value (e.g., diastolic BP)")
    unit: str | None = Field(None, description="Unit of measurement")
    unit_normalized: str | None = Field(None, description="Normalized standard unit")
    frequency: str | None = Field(None, description="Medication frequency (e.g., BID)")
    route: str | None = Field(None, description="Medication route (e.g., oral)")
    omop_concept_id: int | None = Field(None, description="Linked OMOP concept ID")
    confidence: float = Field(..., description="Extraction confidence 0.0-1.0")


class ExtractValuesResponse(BaseModel):
    """Response from clinical value extraction."""

    values: list[ExtractedValuePreview] = Field(..., description="Extracted clinical values")
    extraction_time_ms: float = Field(..., description="Time taken for extraction in ms")
    value_count: int = Field(..., description="Total number of values extracted")
    by_type: dict[str, int] = Field(..., description="Count of values by type")


@router.post(
    "/preview/values",
    response_model=ExtractValuesResponse,
    summary="Extract clinical values without saving",
    description="Extract vital signs, lab results, measurements, and medication doses from clinical text.",
)
async def preview_value_extraction(
    request: ExtractValuesRequest,
) -> ExtractValuesResponse:
    """Run clinical value extraction on text.

    This endpoint extracts quantitative clinical data:
    - Vital signs: BP, HR, RR, Temp, O2 sat, Weight, Height, BMI
    - Lab results: Chemistry (Na, K, Cr, BUN, glucose), CBC (WBC, Hgb, Plt), etc.
    - Measurements: EF, LVEF
    - Medication doses: Drug name, dose, unit, frequency, route

    Results are NOT saved to the database. Use for previewing extraction.

    Args:
        request: The text to extract from and extraction options.

    Returns:
        ExtractValuesResponse with extracted values and timing.
    """
    import time

    # Get extraction service
    service = get_value_extraction_service()

    # Run extraction with timing
    start_time = time.perf_counter()
    extracted = service.extract_all(
        text=request.text,
        include_vitals=request.include_vitals,
        include_labs=request.include_labs,
        include_measurements=request.include_measurements,
        include_medications=request.include_medications,
    )
    extraction_time_ms = (time.perf_counter() - start_time) * 1000

    # Convert to preview format
    values = [
        ExtractedValuePreview(
            text=v.text,
            start_offset=v.start_offset,
            end_offset=v.end_offset,
            name=v.name,
            value_type=v.value_type.value,
            value=v.value,
            value_secondary=v.value_secondary,
            unit=v.unit,
            unit_normalized=v.unit_normalized,
            frequency=v.frequency,
            route=v.route,
            omop_concept_id=v.omop_concept_id,
            confidence=v.confidence,
        )
        for v in extracted
    ]

    # Count by type
    by_type: dict[str, int] = {}
    for v in extracted:
        type_name = v.value_type.value
        by_type[type_name] = by_type.get(type_name, 0) + 1

    return ExtractValuesResponse(
        values=values,
        extraction_time_ms=round(extraction_time_ms, 2),
        value_count=len(values),
        by_type=by_type,
    )


# ============================================================================
# Clinical NER Endpoints
# ============================================================================


class ExtractNERRequest(BaseModel):
    """Request body for clinical NER extraction."""

    text: str = Field(..., description="Clinical note text to extract entities from")
    note_type: str | None = Field(None, description="Type of clinical note for context")
    min_confidence: float = Field(0.5, ge=0.0, le=1.0, description="Minimum confidence threshold")


class ExtractedNEREntity(BaseModel):
    """Preview of an extracted clinical entity."""

    text: str = Field(..., description="The extracted text span")
    start_offset: int = Field(..., description="Character start position")
    end_offset: int = Field(..., description="Character end position")
    normalized_text: str = Field(..., description="Normalized/lemmatized form")
    domain: str | None = Field(None, description="OMOP domain (Condition, Drug, Procedure, etc.)")
    section: str | None = Field(None, description="Clinical section detected")
    assertion: str = Field(..., description="Assertion status (present/absent/possible)")
    temporality: str = Field(..., description="Temporal context (current/past/future)")
    experiencer: str = Field(..., description="Who it applies to (patient/family/other)")
    confidence: float = Field(..., description="Extraction confidence 0.0-1.0")


class ExtractNERResponse(BaseModel):
    """Response from clinical NER extraction."""

    entities: list[ExtractedNEREntity] = Field(..., description="Extracted clinical entities")
    extraction_time_ms: float = Field(..., description="Time taken for extraction in ms")
    entity_count: int = Field(..., description="Total number of entities extracted")
    by_domain: dict[str, int] = Field(..., description="Count of entities by domain")
    model_info: dict[str, bool] = Field(..., description="Information about available models")


@router.post(
    "/preview/ner",
    response_model=ExtractNERResponse,
    summary="Extract clinical entities using ML NER",
    description="Run ML-based Named Entity Recognition on clinical text using transformer models.",
)
async def preview_ner_extraction(
    request: ExtractNERRequest,
) -> ExtractNERResponse:
    """Run clinical NER extraction on text using ML models.

    This endpoint uses transformer-based NER models (Bio_ClinicalBERT variants)
    to extract clinical entities from text. It identifies:
    - Conditions/Diseases: Medical problems, symptoms
    - Drugs/Medications: Treatment drugs, chemicals
    - Procedures: Medical procedures
    - Measurements/Tests: Lab tests, diagnostic procedures
    - Anatomic sites: Body parts, organs

    Results include context detection (assertion, temporality, experiencer).
    Results are NOT saved to the database. Use for previewing extraction.

    Args:
        request: The text to extract from and configuration options.

    Returns:
        ExtractNERResponse with extracted entities and timing.
    """
    import time

    # Get NER service
    service = get_clinical_ner_service()

    # Run extraction with timing
    start_time = time.perf_counter()
    extracted = service.extract_mentions(
        text=request.text,
        document_id=uuid4(),  # Dummy ID for preview
        note_type=request.note_type,
    )
    extraction_time_ms = (time.perf_counter() - start_time) * 1000

    # Filter by confidence
    extracted = [e for e in extracted if e.confidence >= request.min_confidence]

    # Convert to preview format
    entities = [
        ExtractedNEREntity(
            text=e.text,
            start_offset=e.start_offset,
            end_offset=e.end_offset,
            normalized_text=e.lexical_variant,
            domain=e.domain_hint,
            section=e.section,
            assertion=e.assertion.value,
            temporality=e.temporality.value,
            experiencer=e.experiencer.value,
            confidence=e.confidence,
        )
        for e in extracted
    ]

    # Count by domain
    by_domain: dict[str, int] = {}
    for e in extracted:
        domain = e.domain_hint or "Unknown"
        by_domain[domain] = by_domain.get(domain, 0) + 1

    # Model availability info
    model_info = {
        "spacy_available": service._spacy_available if service._initialized else False,
        "transformer_available": service._transformer_available if service._initialized else False,
    }

    return ExtractNERResponse(
        entities=entities,
        extraction_time_ms=round(extraction_time_ms, 2),
        entity_count=len(entities),
        by_domain=by_domain,
        model_info=model_info,
    )


# ============================================================================
# Relation Extraction Endpoints
# ============================================================================


class ExtractRelationsRequest(BaseModel):
    """Request body for clinical relation extraction."""

    text: str = Field(..., description="Clinical note text to extract relations from")
    use_ner: bool = Field(True, description="Use NER to extract mentions first")
    use_patterns: bool = Field(True, description="Use pattern matching for relation extraction")
    min_confidence: float = Field(0.5, ge=0.0, le=1.0, description="Minimum confidence threshold")


class ExtractedRelationPreview(BaseModel):
    """Preview of an extracted clinical relation."""

    source_text: str = Field(..., description="Source entity text")
    source_start: int = Field(..., description="Source entity start position")
    source_end: int = Field(..., description="Source entity end position")
    source_domain: str | None = Field(None, description="Source entity domain")

    target_text: str = Field(..., description="Target entity text")
    target_start: int = Field(..., description="Target entity start position")
    target_end: int = Field(..., description="Target entity end position")
    target_domain: str | None = Field(None, description="Target entity domain")

    relation_type: str = Field(..., description="Type of relation (treats, causes, etc.)")
    confidence: float = Field(..., description="Extraction confidence 0.0-1.0")
    evidence_text: str = Field(..., description="Text span containing the relation")
    extraction_method: str = Field(..., description="How the relation was extracted")


class ExtractRelationsResponse(BaseModel):
    """Response from clinical relation extraction."""

    relations: list[ExtractedRelationPreview] = Field(..., description="Extracted relations")
    extraction_time_ms: float = Field(..., description="Time taken for extraction in ms")
    relation_count: int = Field(..., description="Total number of relations extracted")
    by_type: dict[str, int] = Field(..., description="Count of relations by type")
    entity_count: int = Field(0, description="Number of entities found (if NER was used)")


@router.post(
    "/preview/relations",
    response_model=ExtractRelationsResponse,
    summary="Extract clinical relations",
    description="Extract relationships between clinical entities (drug-treats-condition, etc.).",
)
async def preview_relation_extraction(
    request: ExtractRelationsRequest,
) -> ExtractRelationsResponse:
    """Run clinical relation extraction on text.

    This endpoint extracts relationships between clinical entities:
    - Treatment relations: Drug treats Condition
    - Adverse relations: Drug causes Side Effect
    - Diagnostic relations: Test diagnoses Condition
    - Procedural relations: Procedure for Condition

    Can optionally run NER first to extract entities, then find relations
    between them. Results are NOT saved to the database.

    Args:
        request: The text to extract from and configuration options.

    Returns:
        ExtractRelationsResponse with extracted relations and timing.
    """
    import time

    # Get services
    relation_service = get_relation_extraction_service()
    ner_service = get_clinical_ner_service()

    # Run extraction with timing
    start_time = time.perf_counter()

    mentions = None
    entity_count = 0

    # Optionally run NER first
    if request.use_ner:
        mentions = ner_service.extract_mentions(
            text=request.text,
            document_id=uuid4(),
            note_type=None,
        )
        entity_count = len(mentions)

    # Extract relations
    if request.use_patterns:
        relations = relation_service.extract_all(request.text, mentions)
    else:
        relations = relation_service.extract_mention_relations(request.text, mentions or [])

    extraction_time_ms = (time.perf_counter() - start_time) * 1000

    # Filter by confidence
    relations = [r for r in relations if r.confidence >= request.min_confidence]

    # Convert to preview format
    relation_previews = [
        ExtractedRelationPreview(
            source_text=r.source_text,
            source_start=r.source_start,
            source_end=r.source_end,
            source_domain=r.source_domain,
            target_text=r.target_text,
            target_start=r.target_start,
            target_end=r.target_end,
            target_domain=r.target_domain,
            relation_type=r.relation_type.value,
            confidence=r.confidence,
            evidence_text=r.evidence_text,
            extraction_method=r.extraction_method,
        )
        for r in relations
    ]

    # Count by type
    by_type: dict[str, int] = {}
    for r in relations:
        type_name = r.relation_type.value
        by_type[type_name] = by_type.get(type_name, 0) + 1

    return ExtractRelationsResponse(
        relations=relation_previews,
        extraction_time_ms=round(extraction_time_ms, 2),
        relation_count=len(relations),
        by_type=by_type,
        entity_count=entity_count,
    )


# ============================================================================
# Ensemble Extraction Endpoint
# ============================================================================


class EnsembleExtractRequest(BaseModel):
    """Request body for ensemble clinical extraction."""

    text: str = Field(..., description="Clinical note text to process")
    note_type: str | None = Field(None, description="Type of clinical note for context")
    use_rule_based: bool = Field(True, description="Enable rule-based extraction")
    use_ml_ner: bool = Field(True, description="Enable ML NER extraction")
    use_value_extraction: bool = Field(True, description="Enable value extraction")
    use_relation_extraction: bool = Field(True, description="Enable relation extraction")
    min_confidence: float = Field(0.5, ge=0.0, le=1.0, description="Minimum confidence threshold")


class EnsembleMentionPreview(BaseModel):
    """Preview of an extracted mention from ensemble."""

    text: str = Field(..., description="The extracted text span")
    start_offset: int = Field(..., description="Character start position")
    end_offset: int = Field(..., description="Character end position")
    normalized_text: str = Field(..., description="Normalized/lemmatized form")
    domain: str | None = Field(None, description="OMOP domain")
    section: str | None = Field(None, description="Clinical section detected")
    assertion: str = Field(..., description="Assertion status")
    temporality: str = Field(..., description="Temporal context")
    experiencer: str = Field(..., description="Who it applies to")
    confidence: float = Field(..., description="Extraction confidence")
    omop_concept_id: int | None = Field(None, description="Linked OMOP concept ID")


class EnsembleExtractResponse(BaseModel):
    """Response from ensemble clinical extraction."""

    mentions: list[EnsembleMentionPreview] = Field(..., description="Extracted mentions")
    relations: list[ExtractedRelationPreview] = Field(..., description="Extracted relations")
    extraction_time_ms: float = Field(..., description="Total extraction time in ms")
    mention_count: int = Field(..., description="Number of mentions extracted")
    relation_count: int = Field(..., description="Number of relations extracted")
    by_domain: dict[str, int] = Field(..., description="Mentions by domain")
    by_relation_type: dict[str, int] = Field(..., description="Relations by type")


@router.post(
    "/preview/ensemble",
    response_model=EnsembleExtractResponse,
    summary="Run full ensemble extraction pipeline",
    description="Extract mentions and relations using all available NLP methods combined.",
)
async def preview_ensemble_extraction(
    request: EnsembleExtractRequest,
) -> EnsembleExtractResponse:
    """Run full ensemble extraction pipeline on clinical text.

    This endpoint combines multiple extraction methods:
    - **Rule-based**: High-precision patterns for medications, vitals, labs
    - **ML NER**: Transformer-based entity recognition for conditions, drugs
    - **Value extraction**: Quantitative measurements with unit normalization
    - **Relation extraction**: Relationships like drug-treats-condition

    Results are merged and deduplicated, with confidence boosting when
    multiple methods agree. NOT saved to database - use for previewing.

    Args:
        request: The text to extract from and configuration options.

    Returns:
        EnsembleExtractResponse with mentions, relations, and statistics.
    """
    import time

    # Configure and get ensemble service
    from app.services.nlp_ensemble import EnsembleConfig

    config = EnsembleConfig(
        use_rule_based=request.use_rule_based,
        use_ml_ner=request.use_ml_ner,
        use_value_extraction=request.use_value_extraction,
        use_relation_extraction=request.use_relation_extraction,
        min_confidence=request.min_confidence,
    )

    # Create a new service instance with this config (don't pollute singleton)
    from app.services.nlp_ensemble import EnsembleNLPService
    service = EnsembleNLPService(config=config)

    # Run extraction
    start_time = time.perf_counter()
    result = service.extract_all(
        text=request.text,
        document_id=uuid4(),
        note_type=request.note_type,
    )
    total_time_ms = (time.perf_counter() - start_time) * 1000

    # Convert mentions to preview format
    mentions = [
        EnsembleMentionPreview(
            text=m.text,
            start_offset=m.start_offset,
            end_offset=m.end_offset,
            normalized_text=m.lexical_variant,
            domain=m.domain_hint,
            section=m.section,
            assertion=m.assertion.value,
            temporality=m.temporality.value,
            experiencer=m.experiencer.value,
            confidence=m.confidence,
            omop_concept_id=m.omop_concept_id,
        )
        for m in result.mentions
    ]

    # Convert relations to preview format
    relations = [
        ExtractedRelationPreview(
            source_text=r.source_text,
            source_start=r.source_start,
            source_end=r.source_end,
            source_domain=r.source_domain,
            target_text=r.target_text,
            target_start=r.target_start,
            target_end=r.target_end,
            target_domain=r.target_domain,
            relation_type=r.relation_type.value,
            confidence=r.confidence,
            evidence_text=r.evidence_text,
            extraction_method=r.extraction_method,
        )
        for r in result.relations
    ]

    return EnsembleExtractResponse(
        mentions=mentions,
        relations=relations,
        extraction_time_ms=round(total_time_ms, 2),
        mention_count=len(mentions),
        relation_count=len(relations),
        by_domain=result.stats.get("by_domain", {}),
        by_relation_type=result.stats.get("by_relation_type", {}),
    )
