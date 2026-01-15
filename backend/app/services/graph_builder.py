"""Graph builder service for knowledge graph materialization.

Converts ClinicalFacts into a patient knowledge graph with
nodes and edges.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from uuid import UUID

from app.schemas.base import Domain
from app.schemas.knowledge_graph import EdgeType, NodeType


@dataclass
class NodeInput:
    """Input data for creating a KGNode."""

    patient_id: str
    node_type: NodeType
    label: str
    omop_concept_id: int | None = None
    properties: dict = field(default_factory=dict)


@dataclass
class EdgeInput:
    """Input data for creating a KGEdge."""

    patient_id: str
    source_node_id: UUID
    target_node_id: UUID
    edge_type: EdgeType
    fact_id: UUID | None = None
    properties: dict = field(default_factory=dict)


@dataclass
class GraphResult:
    """Result of graph building operation."""

    patient_id: str
    node_count: int = 0
    edge_count: int = 0
    nodes_created: int = 0
    edges_created: int = 0


class GraphBuilderServiceInterface(ABC):
    """Interface for knowledge graph materialization services.

    Example usage:
        builder = MyGraphBuilder(session)
        builder.create_patient_node(patient_id)
        builder.project_fact_to_graph(fact)
        graph = builder.get_patient_graph(patient_id)
    """

    @abstractmethod
    def create_patient_node(self, patient_id: str) -> UUID:
        """Create a patient node in the graph.

        The patient node is the central node that all other nodes
        connect to.

        Args:
            patient_id: Patient identifier.

        Returns:
            UUID of the created patient node.
        """
        pass  # pragma: no cover

    @abstractmethod
    def get_patient_node(self, patient_id: str) -> UUID | None:
        """Get the patient node ID for a patient.

        Args:
            patient_id: Patient identifier.

        Returns:
            UUID of patient node or None if not found.
        """
        pass  # pragma: no cover

    @abstractmethod
    def create_node(self, node_input: NodeInput) -> UUID:
        """Create a node in the knowledge graph.

        Args:
            node_input: Node data.

        Returns:
            UUID of the created node.
        """
        pass  # pragma: no cover

    @abstractmethod
    def create_edge(self, edge_input: EdgeInput) -> UUID:
        """Create an edge in the knowledge graph.

        Args:
            edge_input: Edge data.

        Returns:
            UUID of the created edge.
        """
        pass  # pragma: no cover

    @abstractmethod
    def project_fact_to_graph(
        self,
        fact_id: UUID,
        patient_id: str,
        domain: Domain,
        omop_concept_id: int,
        concept_name: str,
        assertion: str,
        temporality: str,
        experiencer: str,
    ) -> UUID:
        """Project a ClinicalFact to a node in the graph.

        Creates a node for the fact and an edge connecting it
        to the patient node.

        Args:
            fact_id: UUID of the source fact.
            patient_id: Patient identifier.
            domain: OMOP domain.
            omop_concept_id: OMOP concept ID.
            concept_name: Human-readable name.
            assertion: Assertion status.
            temporality: Temporal context.
            experiencer: Who it applies to.

        Returns:
            UUID of the created node.
        """
        pass  # pragma: no cover

    @abstractmethod
    def get_node_by_id(self, node_id: UUID) -> NodeInput | None:
        """Get a node by ID.

        Args:
            node_id: Node UUID.

        Returns:
            NodeInput if found, None otherwise.
        """
        pass  # pragma: no cover

    @abstractmethod
    def get_nodes_for_patient(
        self,
        patient_id: str,
        node_type: NodeType | None = None,
    ) -> list[NodeInput]:
        """Get all nodes for a patient.

        Args:
            patient_id: Patient identifier.
            node_type: Optional filter by node type.

        Returns:
            List of NodeInput objects.
        """
        pass  # pragma: no cover

    @abstractmethod
    def get_edges_for_patient(
        self,
        patient_id: str,
        edge_type: EdgeType | None = None,
    ) -> list[EdgeInput]:
        """Get all edges for a patient.

        Args:
            patient_id: Patient identifier.
            edge_type: Optional filter by edge type.

        Returns:
            List of EdgeInput objects.
        """
        pass  # pragma: no cover

    @abstractmethod
    def build_graph_for_patient(self, patient_id: str) -> GraphResult:
        """Build complete graph for a patient from their facts.

        This method orchestrates:
        1. Creating the patient node (if needed)
        2. Projecting all facts to nodes
        3. Creating edges

        Args:
            patient_id: Patient identifier.

        Returns:
            GraphResult with statistics.
        """
        pass  # pragma: no cover


class BaseGraphBuilderService(GraphBuilderServiceInterface):
    """Base graph builder with common functionality."""

    def domain_to_node_type(self, domain: Domain) -> NodeType:
        """Convert OMOP domain to node type.

        Args:
            domain: OMOP domain.

        Returns:
            Corresponding NodeType.
        """
        mapping = {
            Domain.CONDITION: NodeType.CONDITION,
            Domain.DRUG: NodeType.DRUG,
            Domain.MEASUREMENT: NodeType.MEASUREMENT,
            Domain.PROCEDURE: NodeType.PROCEDURE,
            Domain.OBSERVATION: NodeType.OBSERVATION,
            Domain.DEVICE: NodeType.OBSERVATION,
        }
        return mapping.get(domain, NodeType.OBSERVATION)

    def domain_to_edge_type(self, domain: Domain) -> EdgeType:
        """Convert OMOP domain to edge type for patient connection.

        Args:
            domain: OMOP domain.

        Returns:
            Corresponding EdgeType for patient → node edge.
        """
        mapping = {
            Domain.CONDITION: EdgeType.HAS_CONDITION,
            Domain.DRUG: EdgeType.TAKES_DRUG,
            Domain.MEASUREMENT: EdgeType.HAS_MEASUREMENT,
            Domain.PROCEDURE: EdgeType.HAS_PROCEDURE,
            Domain.OBSERVATION: EdgeType.HAS_OBSERVATION,
            Domain.DEVICE: EdgeType.HAS_OBSERVATION,
        }
        return mapping.get(domain, EdgeType.HAS_OBSERVATION)

    def calculate_node_dedup_key(
        self,
        patient_id: str,
        node_type: NodeType,
        omop_concept_id: int | None,
    ) -> str:
        """Calculate deduplication key for a node.

        Args:
            patient_id: Patient identifier.
            node_type: Type of node.
            omop_concept_id: OMOP concept ID.

        Returns:
            Deduplication key string.
        """
        return f"{patient_id}:{node_type.value}:{omop_concept_id or 'patient'}"

    # Default implementations that raise NotImplementedError
    def create_patient_node(self, patient_id: str) -> UUID:
        raise NotImplementedError("Subclass must implement")

    def get_patient_node(self, patient_id: str) -> UUID | None:
        return None

    def create_node(self, node_input: NodeInput) -> UUID:
        raise NotImplementedError("Subclass must implement")

    def create_edge(self, edge_input: EdgeInput) -> UUID:
        raise NotImplementedError("Subclass must implement")

    def project_fact_to_graph(
        self,
        fact_id: UUID,
        patient_id: str,
        domain: Domain,
        omop_concept_id: int,
        concept_name: str,
        assertion: str,
        temporality: str,
        experiencer: str,
    ) -> UUID:
        raise NotImplementedError("Subclass must implement")

    def get_node_by_id(self, node_id: UUID) -> NodeInput | None:
        return None

    def get_nodes_for_patient(
        self,
        patient_id: str,
        node_type: NodeType | None = None,
    ) -> list[NodeInput]:
        return []

    def get_edges_for_patient(
        self,
        patient_id: str,
        edge_type: EdgeType | None = None,
    ) -> list[EdgeInput]:
        return []

    def build_graph_for_patient(self, patient_id: str) -> GraphResult:
        raise NotImplementedError("Subclass must implement")
