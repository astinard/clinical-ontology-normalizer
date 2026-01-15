"""Knowledge Graph schemas (KGNode, KGEdge)."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    """Types of nodes in the knowledge graph."""

    PATIENT = "patient"
    CONDITION = "condition"
    DRUG = "drug"
    MEASUREMENT = "measurement"
    PROCEDURE = "procedure"
    OBSERVATION = "observation"


class EdgeType(str, Enum):
    """Types of edges in the knowledge graph."""

    HAS_CONDITION = "has_condition"
    TAKES_DRUG = "takes_drug"
    HAS_MEASUREMENT = "has_measurement"
    HAS_PROCEDURE = "has_procedure"
    HAS_OBSERVATION = "has_observation"
    CONDITION_TREATED_BY = "condition_treated_by"
    DRUG_TREATS = "drug_treats"


class KGNodeCreate(BaseModel):
    """Schema for creating a knowledge graph node."""

    patient_id: str = Field(..., description="Patient this node belongs to")
    node_type: NodeType = Field(..., description="Type of node")
    omop_concept_id: int | None = Field(
        None, description="OMOP concept ID (null for patient nodes)"
    )
    label: str = Field(..., description="Human-readable label")
    properties: dict = Field(default_factory=dict, description="Node-specific properties")


class KGNode(BaseModel):
    """Schema for a knowledge graph node.

    Nodes represent entities in the patient's clinical knowledge graph:
    - Patient node: Central node for the patient
    - Condition nodes: Diagnoses, symptoms, findings
    - Drug nodes: Medications
    - Measurement nodes: Lab values, vitals
    - Procedure nodes: Surgeries, interventions

    Properties contain node-specific data like assertion status for conditions.
    """

    id: UUID = Field(..., description="Unique node identifier")
    patient_id: str = Field(..., description="Patient this node belongs to")
    node_type: NodeType = Field(..., description="Type of node")
    omop_concept_id: int | None = Field(None, description="OMOP concept ID")
    label: str = Field(..., description="Human-readable label")
    properties: dict = Field(default_factory=dict, description="Node properties")
    created_at: datetime = Field(..., description="When node was created")

    model_config = {"from_attributes": True}


class KGEdgeCreate(BaseModel):
    """Schema for creating a knowledge graph edge."""

    patient_id: str = Field(..., description="Patient this edge belongs to")
    source_node_id: UUID = Field(..., description="Source node ID")
    target_node_id: UUID = Field(..., description="Target node ID")
    edge_type: EdgeType = Field(..., description="Type of relationship")
    fact_id: UUID | None = Field(None, description="Source clinical fact ID")
    properties: dict = Field(default_factory=dict, description="Edge-specific properties")


class KGEdge(BaseModel):
    """Schema for a knowledge graph edge.

    Edges represent relationships between nodes:
    - has_condition: Patient → Condition
    - takes_drug: Patient → Drug
    - has_measurement: Patient → Measurement
    - condition_treated_by: Condition → Drug

    Properties may include temporal information, evidence strength, etc.
    """

    id: UUID = Field(..., description="Unique edge identifier")
    patient_id: str = Field(..., description="Patient this edge belongs to")
    source_node_id: UUID = Field(..., description="Source node ID")
    target_node_id: UUID = Field(..., description="Target node ID")
    edge_type: EdgeType = Field(..., description="Type of relationship")
    fact_id: UUID | None = Field(None, description="Source clinical fact ID")
    properties: dict = Field(default_factory=dict, description="Edge properties")
    created_at: datetime = Field(..., description="When edge was created")

    model_config = {"from_attributes": True}


class PatientGraph(BaseModel):
    """Schema for a complete patient knowledge graph.

    Used for API responses when fetching a patient's full graph.
    """

    patient_id: str = Field(..., description="Patient identifier")
    nodes: list[KGNode] = Field(default_factory=list, description="All nodes in the graph")
    edges: list[KGEdge] = Field(default_factory=list, description="All edges in the graph")
    node_count: int = Field(0, description="Total number of nodes")
    edge_count: int = Field(0, description="Total number of edges")

    def model_post_init(self, __context: dict) -> None:
        """Update counts after initialization."""
        object.__setattr__(self, "node_count", len(self.nodes))
        object.__setattr__(self, "edge_count", len(self.edges))
