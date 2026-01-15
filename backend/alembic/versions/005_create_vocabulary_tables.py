"""Create concepts and concept_synonyms tables.

Revision ID: 005
Revises: 004
Create Date: 2026-01-14

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "005"
down_revision: str | None = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create concepts table (OMOP vocabulary subset)
    op.create_table(
        "concepts",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("concept_id", sa.Integer(), nullable=False, unique=True),
        sa.Column("concept_name", sa.String(500), nullable=False),
        sa.Column("domain_id", sa.String(50), nullable=False),
        sa.Column("vocabulary_id", sa.String(50), nullable=False),
        sa.Column("concept_class_id", sa.String(50), nullable=False),
        sa.Column("standard_concept", sa.String(1), nullable=True),
    )
    op.create_index("ix_concepts_concept_id", "concepts", ["concept_id"])
    op.create_index("ix_concepts_concept_name", "concepts", ["concept_name"])
    op.create_index("ix_concepts_domain_id", "concepts", ["domain_id"])
    op.create_index("ix_concepts_vocabulary_id", "concepts", ["vocabulary_id"])

    # Create concept_synonyms table with foreign key to concepts
    op.create_table(
        "concept_synonyms",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "concept_id",
            sa.Integer(),
            sa.ForeignKey("concepts.concept_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("concept_synonym_name", sa.String(1000), nullable=False),
        sa.Column("language_concept_id", sa.Integer(), nullable=False, server_default="4180186"),
    )
    op.create_index("ix_concept_synonyms_concept_id", "concept_synonyms", ["concept_id"])
    op.create_index("ix_concept_synonyms_concept_synonym_name", "concept_synonyms", ["concept_synonym_name"])


def downgrade() -> None:
    op.drop_table("concept_synonyms")
    op.drop_table("concepts")
