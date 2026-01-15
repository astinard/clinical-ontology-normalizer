"""SQLAlchemy models for KGNode and KGEdge."""

from sqlalchemy import Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.schemas.knowledge_graph import EdgeType, NodeType


class KGNode(Base):
    """Knowledge graph node representing an entity.

    Nodes can be:
    - Patient nodes (central node for each patient)
    - Condition nodes (diagnoses, symptoms)
    - Drug nodes (medications)
    - Measurement nodes (labs, vitals)
    - Procedure nodes (surgeries, interventions)

    Properties store node-specific data like assertion status.
    """

    __tablename__ = "kg_nodes"

    patient_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    node_type: Mapped[NodeType] = mapped_column(
        Enum(NodeType, name="node_type", create_constraint=True),
        nullable=False,
        index=True,
    )
    omop_concept_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
    )
    label: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    properties: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # Relationships for edges
    outgoing_edges = relationship(
        "KGEdge",
        foreign_keys="KGEdge.source_node_id",
        back_populates="source_node",
        cascade="all, delete-orphan",
    )
    incoming_edges = relationship(
        "KGEdge",
        foreign_keys="KGEdge.target_node_id",
        back_populates="target_node",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<KGNode(id={self.id}, type={self.node_type}, label='{self.label}')>"

    @property
    def is_patient_node(self) -> bool:
        """Check if this is a patient node."""
        return self.node_type == NodeType.PATIENT


class KGEdge(Base):
    """Knowledge graph edge representing a relationship.

    Edges connect nodes with typed relationships:
    - has_condition: Patient → Condition
    - takes_drug: Patient → Drug
    - has_measurement: Patient → Measurement
    - condition_treated_by: Condition → Drug

    Properties store edge-specific data like temporal info.
    """

    __tablename__ = "kg_edges"

    patient_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    source_node_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("kg_nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_node_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("kg_nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    edge_type: Mapped[EdgeType] = mapped_column(
        Enum(EdgeType, name="edge_type", create_constraint=True),
        nullable=False,
        index=True,
    )
    fact_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("clinical_facts.id", ondelete="SET NULL"),
        nullable=True,
    )
    properties: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # Relationships
    source_node = relationship(
        "KGNode",
        foreign_keys=[source_node_id],
        back_populates="outgoing_edges",
    )
    target_node = relationship(
        "KGNode",
        foreign_keys=[target_node_id],
        back_populates="incoming_edges",
    )
    fact = relationship("ClinicalFact")

    def __repr__(self) -> str:
        return f"<KGEdge(id={self.id}, type={self.edge_type}, {self.source_node_id} → {self.target_node_id})>"
