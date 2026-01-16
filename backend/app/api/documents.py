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


# ============================================================================
# Enhanced Vocabulary Search Endpoint
# ============================================================================


class VocabularySearchRequest(BaseModel):
    """Request body for vocabulary search."""

    query: str = Field(..., description="Search query (term, abbreviation, or natural language)")
    limit: int = Field(10, ge=1, le=100, description="Maximum number of results")
    use_semantic: bool = Field(False, description="Use semantic similarity search (slower but finds related terms)")


class VocabularyConceptResult(BaseModel):
    """A single vocabulary concept result."""

    concept_id: int = Field(..., description="OMOP concept ID")
    concept_name: str = Field(..., description="Standard concept name")
    concept_code: str = Field(..., description="Source vocabulary code")
    vocabulary_id: str = Field(..., description="Source vocabulary (SNOMED, RxNorm, etc.)")
    domain: str = Field(..., description="OMOP domain (Condition, Drug, Measurement, etc.)")
    synonyms: list[str] = Field(..., description="All known synonyms")
    similarity_score: float | None = Field(None, description="Similarity score (for semantic search)")


class VocabularySearchResponse(BaseModel):
    """Response from vocabulary search."""

    results: list[VocabularyConceptResult] = Field(..., description="Matching concepts")
    search_time_ms: float = Field(..., description="Time taken for search in ms")
    result_count: int = Field(..., description="Number of results returned")
    search_mode: str = Field(..., description="Search mode used (text or semantic)")
    stats: dict[str, int | bool] = Field(..., description="Vocabulary statistics")


@router.post(
    "/vocabulary/search",
    response_model=VocabularySearchResponse,
    summary="Search enhanced OMOP vocabulary",
    description="Search for OMOP concepts using text matching or semantic similarity.",
)
async def search_vocabulary(
    request: VocabularySearchRequest,
) -> VocabularySearchResponse:
    """Search the enhanced OMOP vocabulary.

    This endpoint provides two search modes:
    - **Text search**: Fast exact and partial matching against concept names and synonyms.
      Automatically expands clinical abbreviations (HTN->hypertension, DM->diabetes, etc.)
    - **Semantic search**: Uses sentence embeddings to find conceptually similar terms.
      Useful for natural language queries like "sugar disease" -> diabetes.

    The vocabulary includes:
    - 269+ concepts across Conditions, Drugs, Measurements, Procedures
    - UMLS-style synonym expansion with 100+ clinical abbreviations
    - American/British spelling variations (anemia/anaemia, tumor/tumour)

    Args:
        request: Search query and options.

    Returns:
        VocabularySearchResponse with matching concepts and statistics.
    """
    import time
    from app.services.vocabulary_enhanced import get_enhanced_vocabulary_service

    start_time = time.perf_counter()

    # Get enhanced vocabulary service
    service = get_enhanced_vocabulary_service(
        use_embeddings=request.use_semantic,
        use_automaton=False,  # Not needed for search
    )

    results: list[VocabularyConceptResult] = []
    search_mode = "text"

    if request.use_semantic:
        # Semantic similarity search
        search_mode = "semantic"
        matches = service.semantic_search(request.query, limit=request.limit)
        for concept, score in matches:
            results.append(
                VocabularyConceptResult(
                    concept_id=concept.concept_id,
                    concept_name=concept.concept_name,
                    concept_code=concept.concept_code,
                    vocabulary_id=concept.vocabulary_id,
                    domain=concept.domain.value if hasattr(concept.domain, "value") else str(concept.domain),
                    synonyms=concept.synonyms[:10],  # Limit synonyms for response size
                    similarity_score=round(score, 4),
                )
            )
    else:
        # Fast text search
        matches = service.search(request.query, limit=request.limit)
        for concept in matches:
            results.append(
                VocabularyConceptResult(
                    concept_id=concept.concept_id,
                    concept_name=concept.concept_name,
                    concept_code=concept.concept_code,
                    vocabulary_id=concept.vocabulary_id,
                    domain=concept.domain.value if hasattr(concept.domain, "value") else str(concept.domain),
                    synonyms=concept.synonyms[:10],
                    similarity_score=None,
                )
            )

    search_time_ms = (time.perf_counter() - start_time) * 1000

    # Get vocabulary statistics
    stats = service.get_enhanced_stats()

    return VocabularySearchResponse(
        results=results,
        search_time_ms=round(search_time_ms, 2),
        result_count=len(results),
        search_mode=search_mode,
        stats=stats,
    )


# ============================================================================
# Drug Interaction Checking Endpoint
# ============================================================================


class DrugInteractionCheckRequest(BaseModel):
    """Request body for drug interaction check."""

    drugs: list[str] = Field(..., description="List of drug names to check for interactions")


class DrugInteractionResult(BaseModel):
    """A single drug interaction."""

    drug1: str = Field(..., description="First drug in the interaction")
    drug2: str = Field(..., description="Second drug in the interaction")
    severity: str = Field(..., description="Severity level (contraindicated, major, moderate, minor)")
    interaction_type: str = Field(..., description="Type of interaction (pharmacokinetic, etc.)")
    description: str = Field(..., description="Description of the interaction mechanism")
    clinical_effect: str = Field(..., description="Clinical effects/risks")
    management: str = Field(..., description="Recommended management strategy")
    references: list[str] = Field(..., description="Source references")


class DrugInteractionCheckResponse(BaseModel):
    """Response from drug interaction check."""

    drugs_checked: list[str] = Field(..., description="Normalized list of drugs that were checked")
    interactions: list[DrugInteractionResult] = Field(..., description="Found interactions")
    total_interactions: int = Field(..., description="Total number of interactions found")
    by_severity: dict[str, int] = Field(..., description="Count by severity level")
    highest_severity: str | None = Field(None, description="Most severe interaction level found")
    has_contraindicated: bool = Field(..., description="Whether any contraindicated combinations exist")
    has_major: bool = Field(..., description="Whether any major interactions exist")
    check_time_ms: float = Field(..., description="Time taken for the check in ms")
    database_stats: dict = Field(..., description="Drug interaction database statistics")


@router.post(
    "/clinical/drug-interactions",
    response_model=DrugInteractionCheckResponse,
    summary="Check for drug-drug interactions",
    description="Check a list of medications for known drug-drug interactions.",
)
async def check_drug_interactions(
    request: DrugInteractionCheckRequest,
) -> DrugInteractionCheckResponse:
    """Check for drug-drug interactions among a list of medications.

    This endpoint checks for known clinically significant drug-drug interactions
    based on FDA labels and clinical guidelines. It returns:

    - **Contraindicated**: Combinations that should never be used together
    - **Major**: Serious interactions requiring close monitoring or avoidance
    - **Moderate**: Interactions requiring caution and monitoring
    - **Minor**: Usually not clinically significant

    Supports both generic and brand names, as well as common abbreviations
    (e.g., ASA for aspirin, HCTZ for hydrochlorothiazide).

    Args:
        request: List of drug names to check.

    Returns:
        DrugInteractionCheckResponse with all found interactions and statistics.
    """
    import time
    from app.services.drug_interactions import get_drug_interaction_service

    start_time = time.perf_counter()

    service = get_drug_interaction_service()
    result = service.check_interactions(request.drugs)

    check_time_ms = (time.perf_counter() - start_time) * 1000

    # Convert interactions to response format
    interactions = [
        DrugInteractionResult(
            drug1=i.drug1,
            drug2=i.drug2,
            severity=i.severity.value,
            interaction_type=i.interaction_type.value,
            description=i.description,
            clinical_effect=i.clinical_effect,
            management=i.management,
            references=i.references,
        )
        for i in result.interactions_found
    ]

    return DrugInteractionCheckResponse(
        drugs_checked=result.drugs_checked,
        interactions=interactions,
        total_interactions=result.total_interactions,
        by_severity=result.by_severity,
        highest_severity=result.highest_severity.value if result.highest_severity else None,
        has_contraindicated=result.has_contraindicated,
        has_major=result.has_major,
        check_time_ms=round(check_time_ms, 2),
        database_stats=service.get_stats(),
    )


# ============================================================================
# Lab Interpretation Endpoint
# ============================================================================


class LabValue(BaseModel):
    """A single lab value for interpretation."""

    test: str = Field(..., description="Test name, code, or alias (e.g., 'Na', 'sodium', 'K')")
    value: float = Field(..., description="Numeric value")


class LabInterpretRequest(BaseModel):
    """Request body for lab interpretation."""

    values: list[LabValue] = Field(..., description="List of lab values to interpret")
    gender: str | None = Field(None, description="Patient gender ('male' or 'female') for gender-specific ranges")


class LabInterpretResult(BaseModel):
    """Interpretation result for a single lab value."""

    test_name: str = Field(..., description="Full test name")
    value: float = Field(..., description="The input value")
    unit: str = Field(..., description="Unit of measurement")
    level: str = Field(..., description="Interpretation level (critical_low, low, normal, high, critical_high)")
    reference_range: str = Field(..., description="Normal reference range (e.g., '136-145')")
    is_critical: bool = Field(..., description="Whether the value is critically abnormal")
    clinical_significance: str = Field(..., description="Clinical significance of the value")
    possible_causes: list[str] = Field(..., description="Possible causes of abnormal value")
    recommended_actions: list[str] = Field(..., description="Recommended clinical actions")


class LabInterpretResponse(BaseModel):
    """Response from lab interpretation."""

    interpretations: list[LabInterpretResult] = Field(..., description="Interpretations for each lab value")
    unrecognized_tests: list[str] = Field(..., description="Tests that were not recognized")
    total_interpreted: int = Field(..., description="Number of tests successfully interpreted")
    abnormal_count: int = Field(..., description="Number of abnormal values")
    critical_count: int = Field(..., description="Number of critical values")
    interpret_time_ms: float = Field(..., description="Time taken for interpretation in ms")
    database_stats: dict = Field(..., description="Lab reference database statistics")


@router.post(
    "/clinical/lab-interpret",
    response_model=LabInterpretResponse,
    summary="Interpret laboratory values",
    description="Interpret lab results with reference ranges and clinical guidance.",
)
async def interpret_lab_values(
    request: LabInterpretRequest,
) -> LabInterpretResponse:
    """Interpret laboratory values against reference ranges.

    This endpoint provides clinical interpretation for lab values including:
    - Normal/abnormal/critical classification
    - Reference ranges (with gender-specific values when applicable)
    - Possible causes of abnormal values
    - Recommended clinical actions

    Supports common lab tests from:
    - Basic Metabolic Panel (Na, K, Cl, CO2, BUN, Cr, Glucose)
    - Complete Metabolic Panel (plus ALT, AST, ALP, bilirubin, albumin)
    - Complete Blood Count (WBC, Hgb, Hct, Plt, MCV)
    - Coagulation (PT, INR, PTT)
    - Cardiac markers (Troponin, BNP)
    - Lipid panel (TC, LDL, HDL, TG)
    - Thyroid (TSH, FT4, FT3)
    - And more...

    Args:
        request: Lab values to interpret and optional patient gender.

    Returns:
        LabInterpretResponse with interpretations and statistics.
    """
    import time
    from app.services.lab_reference import get_lab_reference_service

    start_time = time.perf_counter()

    service = get_lab_reference_service()

    interpretations: list[LabInterpretResult] = []
    unrecognized: list[str] = []
    abnormal_count = 0
    critical_count = 0

    for lab in request.values:
        result = service.interpret(lab.test, lab.value, request.gender)

        if result is None:
            unrecognized.append(lab.test)
            continue

        if result.level.value != "normal":
            abnormal_count += 1

        if result.is_critical:
            critical_count += 1

        interpretations.append(
            LabInterpretResult(
                test_name=result.test_name,
                value=result.value,
                unit=result.unit,
                level=result.level.value,
                reference_range=result.reference_range,
                is_critical=result.is_critical,
                clinical_significance=result.clinical_significance,
                possible_causes=result.possible_causes,
                recommended_actions=result.recommended_actions,
            )
        )

    interpret_time_ms = (time.perf_counter() - start_time) * 1000

    return LabInterpretResponse(
        interpretations=interpretations,
        unrecognized_tests=unrecognized,
        total_interpreted=len(interpretations),
        abnormal_count=abnormal_count,
        critical_count=critical_count,
        interpret_time_ms=round(interpret_time_ms, 2),
        database_stats=service.get_stats(),
    )


# ============================================================================
# Clinical Calculator Endpoint
# ============================================================================


class CalculatorRequest(BaseModel):
    """Request body for clinical calculator."""

    calculator: str = Field(
        ...,
        description="Calculator name: bmi, chadsvasc, hasbled, meld, egfr, wells_dvt, curb65, framingham",
    )
    parameters: dict = Field(
        ...,
        description="Calculator-specific parameters",
    )


class CalculatorResultResponse(BaseModel):
    """Response from clinical calculator."""

    calculator_name: str = Field(..., description="Full name of the calculator")
    score: float = Field(..., description="Calculated score")
    score_unit: str = Field(..., description="Unit of the score (points, %, kg/m2, etc.)")
    risk_level: str = Field(..., description="Risk level (low, moderate, high, very_high)")
    interpretation: str = Field(..., description="Clinical interpretation of the score")
    recommendations: list[str] = Field(..., description="Clinical recommendations based on score")
    components: dict = Field(..., description="Individual components that contribute to the score")
    references: list[str] = Field(..., description="Source references")
    calculation_time_ms: float = Field(..., description="Time taken for calculation in ms")


class CalculatorListResponse(BaseModel):
    """Response listing available calculators."""

    calculators: list[dict] = Field(..., description="Available calculators with their parameters")
    total_count: int = Field(..., description="Total number of calculators")


@router.get(
    "/clinical/calculators",
    response_model=CalculatorListResponse,
    summary="List available clinical calculators",
    description="Get a list of all available clinical risk calculators and their parameters.",
)
async def list_calculators() -> CalculatorListResponse:
    """List all available clinical risk calculators.

    Returns information about each calculator including:
    - Calculator name and description
    - Required and optional parameters
    - Parameter types and valid ranges

    Returns:
        CalculatorListResponse with available calculators.
    """
    from app.services.clinical_calculators import ClinicalCalculatorService

    service = ClinicalCalculatorService()

    calculators = [
        {
            "name": "bmi",
            "full_name": "Body Mass Index (BMI)",
            "description": "Calculates BMI for obesity classification",
            "required_params": {"weight_kg": "Weight in kilograms", "height_cm": "Height in centimeters"},
            "optional_params": {},
        },
        {
            "name": "chadsvasc",
            "full_name": "CHA₂DS₂-VASc Score",
            "description": "Stroke risk assessment for atrial fibrillation",
            "required_params": {"age": "Patient age in years", "female": "True if female sex"},
            "optional_params": {
                "congestive_heart_failure": "History of CHF",
                "hypertension": "History of hypertension",
                "diabetes": "History of diabetes",
                "stroke_tia_thromboembolism": "Prior stroke/TIA/thromboembolism",
                "vascular_disease": "History of vascular disease",
            },
        },
        {
            "name": "hasbled",
            "full_name": "HAS-BLED Score",
            "description": "Bleeding risk in atrial fibrillation patients on anticoagulation",
            "required_params": {},
            "optional_params": {
                "hypertension": "Uncontrolled hypertension (>160 mmHg)",
                "renal_disease": "Chronic dialysis/transplant/Cr>2.3",
                "liver_disease": "Chronic liver disease or bilirubin>2x/enzymes>3x",
                "stroke_history": "Prior stroke history",
                "bleeding_history": "Prior major bleed or predisposition",
                "labile_inr": "Unstable/high INRs (time in range <60%)",
                "age_over_65": "Age > 65 years",
                "antiplatelet_or_nsaid": "Concurrent antiplatelet or NSAID use",
                "alcohol": "Alcohol abuse (>8 drinks/week)",
            },
        },
        {
            "name": "meld",
            "full_name": "MELD Score (Model for End-Stage Liver Disease)",
            "description": "Severity of chronic liver disease for transplant prioritization",
            "required_params": {
                "creatinine": "Serum creatinine (mg/dL)",
                "bilirubin": "Total bilirubin (mg/dL)",
                "inr": "INR",
            },
            "optional_params": {
                "sodium": "Serum sodium (mEq/L) for MELD-Na calculation",
                "on_dialysis": "On dialysis twice in past week",
            },
        },
        {
            "name": "egfr",
            "full_name": "eGFR (CKD-EPI 2021)",
            "description": "Estimated glomerular filtration rate for kidney function",
            "required_params": {
                "creatinine": "Serum creatinine (mg/dL)",
                "age": "Patient age in years",
                "female": "True if female sex",
            },
            "optional_params": {},
        },
        {
            "name": "wells_dvt",
            "full_name": "Wells' Criteria for DVT",
            "description": "Clinical probability of deep vein thrombosis",
            "required_params": {},
            "optional_params": {
                "active_cancer": "Active cancer (within 6 months)",
                "paralysis_immobilization": "Paralysis/paresis/recent immobilization of lower extremity",
                "bedridden_3_days": "Bedridden >3 days or major surgery in past 12 weeks",
                "localized_tenderness": "Localized tenderness along deep venous system",
                "entire_leg_swollen": "Entire leg swollen",
                "calf_swelling_3cm": "Calf swelling >3cm vs asymptomatic leg",
                "pitting_edema": "Pitting edema confined to symptomatic leg",
                "collateral_superficial_veins": "Collateral superficial veins",
                "previous_dvt": "Previously documented DVT",
                "alternative_diagnosis_likely": "Alternative diagnosis as likely or more likely than DVT (-2 points)",
            },
        },
        {
            "name": "curb65",
            "full_name": "CURB-65 Score",
            "description": "Pneumonia severity assessment for disposition decisions",
            "required_params": {},
            "optional_params": {
                "confusion": "New-onset confusion",
                "bun_over_19": "BUN > 19 mg/dL (or Urea > 7 mmol/L)",
                "respiratory_rate_over_30": "Respiratory rate >= 30/min",
                "sbp_under_90_or_dbp_under_60": "SBP < 90 or DBP <= 60 mmHg",
                "age_65_or_older": "Age >= 65 years",
            },
        },
        {
            "name": "framingham",
            "full_name": "Framingham 10-Year CVD Risk",
            "description": "10-year cardiovascular disease risk prediction",
            "required_params": {
                "age": "Patient age (30-74 years)",
                "female": "True if female sex",
                "total_cholesterol": "Total cholesterol (mg/dL)",
                "hdl_cholesterol": "HDL cholesterol (mg/dL)",
                "systolic_bp": "Systolic blood pressure (mmHg)",
            },
            "optional_params": {
                "bp_treated": "On blood pressure treatment",
                "smoker": "Current smoker",
                "diabetic": "Has diabetes",
            },
        },
    ]

    return CalculatorListResponse(
        calculators=calculators,
        total_count=len(calculators),
    )


@router.post(
    "/clinical/calculate",
    response_model=CalculatorResultResponse,
    summary="Run a clinical calculator",
    description="Calculate clinical risk scores using validated calculators.",
)
async def run_calculator(
    request: CalculatorRequest,
) -> CalculatorResultResponse:
    """Run a clinical risk calculator.

    Available calculators:

    - **bmi**: Body Mass Index - obesity classification
    - **chadsvasc**: CHA₂DS₂-VASc - stroke risk in atrial fibrillation
    - **hasbled**: HAS-BLED - bleeding risk on anticoagulation
    - **meld**: MELD/MELD-Na - liver disease severity for transplant
    - **egfr**: CKD-EPI eGFR - estimated kidney function
    - **wells_dvt**: Wells' Criteria - DVT clinical probability
    - **curb65**: CURB-65 - pneumonia severity/disposition
    - **framingham**: Framingham - 10-year CVD risk prediction

    Each calculator returns:
    - Score with units
    - Risk level classification
    - Clinical interpretation
    - Evidence-based recommendations
    - Component breakdown
    - Source references

    Args:
        request: Calculator name and parameters.

    Returns:
        CalculatorResultResponse with calculated score and interpretation.

    Raises:
        HTTPException: 400 if calculator unknown or parameters invalid.
    """
    import time
    from app.services.clinical_calculators import get_clinical_calculator_service

    start_time = time.perf_counter()

    service = get_clinical_calculator_service()

    # Validate calculator exists
    available = service.get_available_calculators()
    if request.calculator.lower() not in available:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown calculator '{request.calculator}'. Available: {', '.join(available)}",
        )

    try:
        result = service.calculate(request.calculator.lower(), **request.parameters)
    except TypeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid parameters for {request.calculator}: {e}",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Calculation error for {request.calculator}: {e}",
        )

    calculation_time_ms = (time.perf_counter() - start_time) * 1000

    return CalculatorResultResponse(
        calculator_name=result.calculator_name,
        score=result.score,
        score_unit=result.score_unit,
        risk_level=result.risk_level.value,
        interpretation=result.interpretation,
        recommendations=result.recommendations,
        components=result.components,
        references=result.references,
        calculation_time_ms=round(calculation_time_ms, 2),
    )


# ============================================================================
# Differential Diagnosis Endpoint
# ============================================================================


class DifferentialDiagnosisRequest(BaseModel):
    """Request body for differential diagnosis generation."""

    findings: list[str] = Field(
        ...,
        description="List of clinical findings (symptoms, signs, abnormalities)",
    )
    age: int | None = Field(None, ge=0, le=120, description="Patient age in years")
    gender: str | None = Field(None, description="Patient gender ('male' or 'female')")
    max_diagnoses: int = Field(10, ge=1, le=20, description="Maximum diagnoses to return")


class DiagnosisCandidateResponse(BaseModel):
    """A candidate diagnosis in the differential."""

    name: str = Field(..., description="Diagnosis name")
    omop_concept_id: int | None = Field(None, description="OMOP concept ID")
    icd10_code: str | None = Field(None, description="ICD-10 code")
    domain: str = Field(..., description="Clinical domain (cardiovascular, respiratory, etc.)")
    urgency: str = Field(..., description="Urgency level (emergent, urgent, semi_urgent, routine)")
    probability_score: float = Field(..., description="Relative probability score (0-1)")
    supporting_findings: list[str] = Field(..., description="Findings supporting this diagnosis")
    opposing_findings: list[str] = Field(..., description="Findings arguing against")
    red_flags: list[str] = Field(..., description="Warning signs to watch for")
    recommended_workup: list[str] = Field(..., description="Suggested diagnostic tests")
    key_features: list[str] = Field(..., description="Classic features of this diagnosis")


class DifferentialDiagnosisResponse(BaseModel):
    """Response from differential diagnosis generation."""

    presenting_findings: list[str] = Field(..., description="Input findings")
    age: int | None = Field(None, description="Patient age if provided")
    gender: str | None = Field(None, description="Patient gender if provided")
    differential: list[DiagnosisCandidateResponse] = Field(..., description="Ranked differential diagnoses")
    red_flag_diagnoses: list[str] = Field(..., description="High-urgency diagnoses to rule out")
    cannot_miss_diagnoses: list[str] = Field(..., description="Must-not-miss diagnoses")
    suggested_history: list[str] = Field(..., description="Additional history to gather")
    suggested_exam: list[str] = Field(..., description="Physical exam maneuvers")
    generation_time_ms: float = Field(..., description="Time taken in ms")
    database_stats: dict = Field(..., description="Diagnosis database statistics")


@router.post(
    "/clinical/differential",
    response_model=DifferentialDiagnosisResponse,
    summary="Generate differential diagnosis",
    description="Generate a ranked differential diagnosis from clinical findings.",
)
async def generate_differential_diagnosis(
    request: DifferentialDiagnosisRequest,
) -> DifferentialDiagnosisResponse:
    """Generate a ranked differential diagnosis based on clinical findings.

    This endpoint provides clinical decision support by analyzing presenting
    symptoms, signs, and findings to generate a ranked list of potential
    diagnoses. Results include:

    - **Probability ranking**: Diagnoses ranked by likelihood based on findings
    - **Urgency classification**: Emergent, urgent, semi-urgent, or routine
    - **Supporting evidence**: Which findings support each diagnosis
    - **Red flags**: Warning signs that require immediate attention
    - **Recommended workup**: Suggested diagnostic tests
    - **History/exam suggestions**: Additional data to gather

    Demographics (age, gender) adjust probability estimates based on
    disease epidemiology.

    **Important**: This is a clinical decision support tool and should not
    replace clinical judgment. All diagnoses should be confirmed through
    appropriate diagnostic workup.

    Args:
        request: Clinical findings and optional demographics.

    Returns:
        DifferentialDiagnosisResponse with ranked diagnoses and recommendations.
    """
    import time
    from app.services.differential_diagnosis import get_differential_diagnosis_service

    start_time = time.perf_counter()

    service = get_differential_diagnosis_service()

    result = service.generate_differential(
        findings=request.findings,
        age=request.age,
        gender=request.gender,
        max_diagnoses=request.max_diagnoses,
    )

    generation_time_ms = (time.perf_counter() - start_time) * 1000

    # Convert to response format
    differential = [
        DiagnosisCandidateResponse(
            name=dx.name,
            omop_concept_id=dx.omop_concept_id,
            icd10_code=dx.icd10_code,
            domain=dx.domain.value,
            urgency=dx.urgency.value,
            probability_score=dx.probability_score,
            supporting_findings=dx.supporting_findings,
            opposing_findings=dx.opposing_findings,
            red_flags=dx.red_flags,
            recommended_workup=dx.recommended_workup,
            key_features=dx.key_features,
        )
        for dx in result.differential
    ]

    return DifferentialDiagnosisResponse(
        presenting_findings=result.presenting_findings,
        age=result.age,
        gender=result.gender,
        differential=differential,
        red_flag_diagnoses=result.red_flag_diagnoses,
        cannot_miss_diagnoses=result.cannot_miss_diagnoses,
        suggested_history=result.suggested_history,
        suggested_exam=result.suggested_exam,
        generation_time_ms=round(generation_time_ms, 2),
        database_stats=service.get_stats(),
    )
