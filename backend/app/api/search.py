"""Semantic search API endpoints."""

import logging
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_sync_engine
from app.models.clinical_fact import ClinicalFact as ClinicalFactModel
from app.models.knowledge_graph import KGNode
from app.services.embedding_service import get_embedding_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["Search"])


class SemanticSearchRequest(BaseModel):
    """Request body for semantic search."""

    query: str = Field(..., min_length=1, description="Natural language search query")
    patient_id: str | None = Field(None, description="Optional patient ID to filter results")
    domain: str | None = Field(None, description="Optional domain filter (condition, drug, measurement, procedure, observation)")
    top_k: int = Field(10, ge=1, le=100, description="Maximum number of results")
    threshold: float = Field(0.5, ge=0.0, le=1.0, description="Minimum similarity score")


class SearchResult(BaseModel):
    """Single search result."""

    id: str
    text: str
    score: float
    domain: str | None = None
    omop_concept_id: int | None = None
    patient_id: str | None = None
    metadata: dict | None = None


class SemanticSearchResponse(BaseModel):
    """Response from semantic search."""

    query: str
    results: list[SearchResult]
    total: int


class EmbeddingGenerationResponse(BaseModel):
    """Response from embedding generation."""

    facts_updated: int
    nodes_updated: int
    message: str


@router.post(
    "/semantic/facts",
    response_model=SemanticSearchResponse,
    summary="Semantic search clinical facts",
    description="Search clinical facts using natural language. Finds semantically similar facts even without exact text matches.",
)
def search_clinical_facts(request: SemanticSearchRequest) -> SemanticSearchResponse:
    """Search clinical facts by semantic similarity.

    Examples:
        - "heart problems" finds CHF, heart failure, cardiac conditions
        - "blood pressure medication" finds ACE inhibitors, beta blockers
        - "difficulty breathing" finds dyspnea, shortness of breath

    Args:
        request: Search parameters including query and filters.

    Returns:
        SemanticSearchResponse with matching facts.
    """
    logger.info(f"Semantic search facts: query='{request.query}', patient={request.patient_id}")

    embedding_service = get_embedding_service()

    # Generate query embedding
    query_embedding = embedding_service.encode(request.query)

    with Session(get_sync_engine()) as session:
        # Get facts with embeddings
        stmt = select(ClinicalFactModel).where(ClinicalFactModel.embedding.isnot(None))

        if request.patient_id:
            stmt = stmt.where(ClinicalFactModel.patient_id == request.patient_id)
        if request.domain:
            stmt = stmt.where(ClinicalFactModel.domain == request.domain)

        result = session.execute(stmt)
        facts = result.scalars().all()

        if not facts:
            return SemanticSearchResponse(
                query=request.query,
                results=[],
                total=0,
            )

        # Compute similarities
        fact_embeddings = [f.embedding for f in facts]
        similar_indices = embedding_service.find_similar(
            query_embedding,
            fact_embeddings,
            top_k=request.top_k,
            threshold=request.threshold,
        )

        # Build results
        results = []
        for idx, score in similar_indices:
            fact = facts[idx]
            results.append(SearchResult(
                id=str(fact.id),
                text=fact.concept_name,
                score=round(score, 4),
                domain=fact.domain.value if fact.domain else None,
                omop_concept_id=fact.omop_concept_id,
                patient_id=fact.patient_id,
                metadata={
                    "assertion": fact.assertion.value if fact.assertion else None,
                    "temporality": fact.temporality.value if fact.temporality else None,
                    "is_negated": fact.is_negated,
                    "confidence": fact.confidence,
                },
            ))

        return SemanticSearchResponse(
            query=request.query,
            results=results,
            total=len(results),
        )


@router.post(
    "/semantic/nodes",
    response_model=SemanticSearchResponse,
    summary="Semantic search knowledge graph nodes",
    description="Search knowledge graph nodes using natural language.",
)
def search_kg_nodes(request: SemanticSearchRequest) -> SemanticSearchResponse:
    """Search knowledge graph nodes by semantic similarity.

    Args:
        request: Search parameters including query and filters.

    Returns:
        SemanticSearchResponse with matching nodes.
    """
    logger.info(f"Semantic search nodes: query='{request.query}', patient={request.patient_id}")

    embedding_service = get_embedding_service()

    # Generate query embedding
    query_embedding = embedding_service.encode(request.query)

    with Session(get_sync_engine()) as session:
        # Get nodes with embeddings
        stmt = select(KGNode).where(KGNode.embedding.isnot(None))

        if request.patient_id:
            stmt = stmt.where(KGNode.patient_id == request.patient_id)
        if request.domain:
            stmt = stmt.where(KGNode.node_type == request.domain)

        result = session.execute(stmt)
        nodes = result.scalars().all()

        if not nodes:
            return SemanticSearchResponse(
                query=request.query,
                results=[],
                total=0,
            )

        # Compute similarities
        node_embeddings = [n.embedding for n in nodes]
        similar_indices = embedding_service.find_similar(
            query_embedding,
            node_embeddings,
            top_k=request.top_k,
            threshold=request.threshold,
        )

        # Build results
        results = []
        for idx, score in similar_indices:
            node = nodes[idx]
            results.append(SearchResult(
                id=str(node.id),
                text=node.label,
                score=round(score, 4),
                domain=node.node_type.value if node.node_type else None,
                omop_concept_id=node.omop_concept_id,
                patient_id=node.patient_id,
                metadata=node.properties,
            ))

        return SemanticSearchResponse(
            query=request.query,
            results=results,
            total=len(results),
        )


@router.post(
    "/generate-embeddings/{patient_id}",
    response_model=EmbeddingGenerationResponse,
    summary="Generate embeddings for patient data",
    description="Generate vector embeddings for a patient's clinical facts and KG nodes.",
)
def generate_patient_embeddings(
    patient_id: str,
    regenerate: Annotated[bool, Query(description="Regenerate all embeddings, not just missing ones")] = False,
) -> EmbeddingGenerationResponse:
    """Generate embeddings for a patient's clinical data.

    This enables semantic search for the patient's facts and graph nodes.

    Args:
        patient_id: The patient identifier.
        regenerate: If True, regenerate all embeddings. If False, only generate for records without embeddings.

    Returns:
        EmbeddingGenerationResponse with counts of updated records.
    """
    logger.info(f"Generating embeddings for patient_id={patient_id}, regenerate={regenerate}")

    embedding_service = get_embedding_service()

    with Session(get_sync_engine()) as session:
        # Get facts for patient
        if regenerate:
            fact_stmt = select(ClinicalFactModel).where(ClinicalFactModel.patient_id == patient_id)
        else:
            fact_stmt = select(ClinicalFactModel).where(
                ClinicalFactModel.patient_id == patient_id,
                ClinicalFactModel.embedding.is_(None),
            )

        result = session.execute(fact_stmt)
        facts = result.scalars().all()

        # Generate fact embeddings
        facts_updated = 0
        if facts:
            texts = [f.concept_name for f in facts]
            embeddings = embedding_service.encode_batch(texts)

            for fact, embedding in zip(facts, embeddings):
                fact.embedding = embedding
                facts_updated += 1

            session.flush()
            logger.info(f"Generated embeddings for {facts_updated} facts")

        # Get nodes for patient
        if regenerate:
            node_stmt = select(KGNode).where(KGNode.patient_id == patient_id)
        else:
            node_stmt = select(KGNode).where(
                KGNode.patient_id == patient_id,
                KGNode.embedding.is_(None),
            )

        result = session.execute(node_stmt)
        nodes = result.scalars().all()

        # Generate node embeddings
        nodes_updated = 0
        if nodes:
            texts = [n.label for n in nodes]
            embeddings = embedding_service.encode_batch(texts)

            for node, embedding in zip(nodes, embeddings):
                node.embedding = embedding
                nodes_updated += 1

            session.flush()
            logger.info(f"Generated embeddings for {nodes_updated} nodes")

        session.commit()

        return EmbeddingGenerationResponse(
            facts_updated=facts_updated,
            nodes_updated=nodes_updated,
            message=f"Generated embeddings for {facts_updated} facts and {nodes_updated} nodes",
        )


@router.get(
    "/similar/{concept_id}",
    response_model=SemanticSearchResponse,
    summary="Find similar OMOP concepts",
    description="Find semantically similar OMOP concepts to a given concept.",
)
def find_similar_concepts(
    concept_id: int,
    top_k: Annotated[int, Query(ge=1, le=100)] = 10,
    threshold: Annotated[float, Query(ge=0.0, le=1.0)] = 0.5,
) -> SemanticSearchResponse:
    """Find OMOP concepts semantically similar to a given concept.

    Uses the concept name to find similar concepts in the vocabulary.

    Args:
        concept_id: The OMOP concept ID to find similar concepts for.
        top_k: Maximum number of results.
        threshold: Minimum similarity score.

    Returns:
        SemanticSearchResponse with similar concepts.

    Raises:
        HTTPException: 404 if concept not found.
    """
    logger.info(f"Finding concepts similar to concept_id={concept_id}")

    embedding_service = get_embedding_service()

    with Session(get_sync_engine()) as session:
        # Get the source concept name
        from sqlalchemy import text
        result = session.execute(
            text("SELECT concept_name, domain_id FROM concepts WHERE concept_id = :id"),
            {"id": concept_id},
        )
        row = result.fetchone()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Concept {concept_id} not found",
            )

        concept_name, domain_id = row[0], row[1]
        query_embedding = embedding_service.encode(concept_name)

        # Get candidate concepts from same domain
        candidates_result = session.execute(
            text("""
                SELECT concept_id, concept_name, domain_id, vocabulary_id
                FROM concepts
                WHERE standard_concept = 'S'
                AND domain_id = :domain_id
                AND concept_id != :concept_id
                LIMIT 5000
            """),
            {"domain_id": domain_id, "concept_id": concept_id},
        )
        candidates = candidates_result.fetchall()

        if not candidates:
            return SemanticSearchResponse(
                query=concept_name,
                results=[],
                total=0,
            )

        # Generate embeddings for candidates
        candidate_texts = [c[1] for c in candidates]
        candidate_embeddings = embedding_service.encode_batch(candidate_texts)

        # Find similar
        similar_indices = embedding_service.find_similar(
            query_embedding,
            candidate_embeddings,
            top_k=top_k,
            threshold=threshold,
        )

        # Build results
        results = []
        for idx, score in similar_indices:
            candidate = candidates[idx]
            results.append(SearchResult(
                id=str(candidate[0]),
                text=candidate[1],
                score=round(score, 4),
                domain=candidate[2],
                omop_concept_id=candidate[0],
                metadata={"vocabulary_id": candidate[3]},
            ))

        return SemanticSearchResponse(
            query=concept_name,
            results=results,
            total=len(results),
        )
