"""Add concept_relationships table for cross-vocabulary mapping.

Revision ID: 014
Revises: 013
Create Date: 2026-01-18

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "014"
down_revision: str | None = "013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create concept_relationships table
    op.create_table(
        "concept_relationships",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("concept_id_1", sa.Integer(), nullable=False),
        sa.Column("concept_id_2", sa.Integer(), nullable=False),
        sa.Column("relationship_id", sa.String(50), nullable=False),
        sa.Column("valid_start_date", sa.String(8), nullable=True),
        sa.Column("valid_end_date", sa.String(8), nullable=True),
        sa.Column("invalid_reason", sa.String(1), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Create indexes for efficient lookups
    op.create_index(
        "ix_concept_relationships_source",
        "concept_relationships",
        ["concept_id_1"],
    )
    op.create_index(
        "ix_concept_relationships_target",
        "concept_relationships",
        ["concept_id_2"],
    )
    op.create_index(
        "ix_concept_relationships_type",
        "concept_relationships",
        ["relationship_id"],
    )
    # Composite index for common query pattern: find mappings for a source concept
    op.create_index(
        "ix_concept_relationships_mapping",
        "concept_relationships",
        ["concept_id_1", "relationship_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_concept_relationships_mapping")
    op.drop_index("ix_concept_relationships_type")
    op.drop_index("ix_concept_relationships_target")
    op.drop_index("ix_concept_relationships_source")
    op.drop_table("concept_relationships")
