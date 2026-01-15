"""Create kg_nodes and kg_edges tables.

Revision ID: 004
Revises: 003
Create Date: 2026-01-14

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: str | None = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create node_type enum
    node_type_enum = postgresql.ENUM(
        "patient",
        "condition",
        "drug",
        "measurement",
        "procedure",
        "observation",
        name="node_type",
        create_type=False,
    )
    node_type_enum.create(op.get_bind(), checkfirst=True)

    # Create edge_type enum
    edge_type_enum = postgresql.ENUM(
        "has_condition",
        "takes_drug",
        "has_measurement",
        "has_procedure",
        "has_observation",
        "condition_treated_by",
        "drug_treats",
        name="edge_type",
        create_type=False,
    )
    edge_type_enum.create(op.get_bind(), checkfirst=True)

    # Create kg_nodes table
    op.create_table(
        "kg_nodes",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("patient_id", sa.String(255), nullable=False),
        sa.Column("node_type", node_type_enum, nullable=False),
        sa.Column("omop_concept_id", sa.Integer(), nullable=True),
        sa.Column("label", sa.String(500), nullable=False),
        sa.Column("properties", postgresql.JSONB(), nullable=False, server_default="{}"),
    )
    op.create_index("ix_kg_nodes_patient_id", "kg_nodes", ["patient_id"])
    op.create_index("ix_kg_nodes_node_type", "kg_nodes", ["node_type"])
    op.create_index("ix_kg_nodes_omop_concept_id", "kg_nodes", ["omop_concept_id"])

    # Create kg_edges table
    op.create_table(
        "kg_edges",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("patient_id", sa.String(255), nullable=False),
        sa.Column(
            "source_node_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("kg_nodes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "target_node_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("kg_nodes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("edge_type", edge_type_enum, nullable=False),
        sa.Column(
            "fact_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("clinical_facts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("properties", postgresql.JSONB(), nullable=False, server_default="{}"),
    )
    op.create_index("ix_kg_edges_patient_id", "kg_edges", ["patient_id"])
    op.create_index("ix_kg_edges_source_node_id", "kg_edges", ["source_node_id"])
    op.create_index("ix_kg_edges_target_node_id", "kg_edges", ["target_node_id"])
    op.create_index("ix_kg_edges_edge_type", "kg_edges", ["edge_type"])


def downgrade() -> None:
    op.drop_table("kg_edges")
    op.drop_table("kg_nodes")

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS edge_type")
    op.execute("DROP TYPE IF EXISTS node_type")
