"""Patient API endpoints."""

import logging

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_sync_engine
from app.models.clinical_fact import ClinicalFact
from app.models.knowledge_graph import KGNode
from app.schemas.knowledge_graph import PatientGraph
from app.services.graph_builder_db import DatabaseGraphBuilderService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/patients", tags=["Patients"])


@router.get(
    "/{patient_id}/graph",
    response_model=PatientGraph,
    summary="Get patient knowledge graph",
    description="Retrieve the complete knowledge graph for a patient, including all nodes and edges.",
)
def get_patient_graph(patient_id: str) -> PatientGraph:
    """Get the complete knowledge graph for a patient.

    This endpoint builds or retrieves the patient's knowledge graph,
    which contains:
    - A central patient node
    - Nodes for conditions, drugs, measurements, procedures
    - Edges connecting the patient to clinical facts

    Args:
        patient_id: The patient identifier.

    Returns:
        PatientGraph with all nodes and edges.

    Raises:
        HTTPException: 404 if patient has no data.
    """
    logger.info(f"Getting knowledge graph for patient_id={patient_id}")

    with Session(get_sync_engine()) as session:
        graph_service = DatabaseGraphBuilderService(session)

        # Check if patient has any data
        existing_nodes = (
            session.execute(select(KGNode).where(KGNode.patient_id == patient_id).limit(1))
            .scalars()
            .first()
        )

        # If no nodes exist, check if there are any facts and build the graph
        if existing_nodes is None:
            facts_exist = (
                session.execute(
                    select(ClinicalFact).where(ClinicalFact.patient_id == patient_id).limit(1)
                )
                .scalars()
                .first()
            )

            if facts_exist is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No data found for patient {patient_id}",
                )

            # Build graph from facts
            logger.info(f"Building knowledge graph for patient_id={patient_id}")
            graph_service.build_graph_for_patient(patient_id)
            session.commit()

        # Get the complete graph
        patient_graph = graph_service.get_patient_graph(patient_id)

        logger.info(
            f"Retrieved graph for patient_id={patient_id}: "
            f"nodes={patient_graph.node_count}, edges={patient_graph.edge_count}"
        )

        return patient_graph


@router.post(
    "/{patient_id}/graph/build",
    response_model=PatientGraph,
    status_code=status.HTTP_201_CREATED,
    summary="Build patient knowledge graph",
    description="Build or rebuild the knowledge graph for a patient from their clinical facts.",
)
def build_patient_graph(patient_id: str) -> PatientGraph:
    """Build the knowledge graph for a patient from clinical facts.

    This endpoint forces a rebuild of the patient's knowledge graph,
    projecting all clinical facts into nodes and edges.

    Args:
        patient_id: The patient identifier.

    Returns:
        PatientGraph with all nodes and edges.

    Raises:
        HTTPException: 404 if patient has no clinical facts.
    """
    logger.info(f"Building knowledge graph for patient_id={patient_id}")

    with Session(get_sync_engine()) as session:
        # Check if patient has any facts
        facts_exist = (
            session.execute(
                select(ClinicalFact).where(ClinicalFact.patient_id == patient_id).limit(1)
            )
            .scalars()
            .first()
        )

        if facts_exist is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No clinical facts found for patient {patient_id}",
            )

        graph_service = DatabaseGraphBuilderService(session)

        # Build the graph
        result = graph_service.build_graph_for_patient(patient_id)
        session.commit()

        logger.info(
            f"Built graph for patient_id={patient_id}: "
            f"nodes_created={result.nodes_created}, edges_created={result.edges_created}"
        )

        # Return the complete graph
        return graph_service.get_patient_graph(patient_id)
