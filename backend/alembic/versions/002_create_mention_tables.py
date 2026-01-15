"""Create mention and mention_concept_candidates tables.

Revision ID: 002
Revises: 001
Create Date: 2026-01-14

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create assertion_type enum
    assertion_enum = postgresql.ENUM(
        "present",
        "absent",
        "possible",
        name="assertion_type",
        create_type=False,
    )
    assertion_enum.create(op.get_bind(), checkfirst=True)

    # Create temporality_type enum
    temporality_enum = postgresql.ENUM(
        "current",
        "past",
        "future",
        name="temporality_type",
        create_type=False,
    )
    temporality_enum.create(op.get_bind(), checkfirst=True)

    # Create experiencer_type enum
    experiencer_enum = postgresql.ENUM(
        "patient",
        "family",
        "other",
        name="experiencer_type",
        create_type=False,
    )
    experiencer_enum.create(op.get_bind(), checkfirst=True)

    # Create domain_type enum
    domain_enum = postgresql.ENUM(
        "condition",
        "drug",
        "measurement",
        "procedure",
        "observation",
        "device",
        "visit",
        name="domain_type",
        create_type=False,
    )
    domain_enum.create(op.get_bind(), checkfirst=True)

    # Create mentions table
    op.create_table(
        "mentions",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("start_offset", sa.Integer(), nullable=False),
        sa.Column("end_offset", sa.Integer(), nullable=False),
        sa.Column("lexical_variant", sa.String(500), nullable=False),
        sa.Column("section", sa.String(255), nullable=True),
        sa.Column("assertion", assertion_enum, nullable=False, server_default="present"),
        sa.Column("temporality", temporality_enum, nullable=False, server_default="current"),
        sa.Column("experiencer", experiencer_enum, nullable=False, server_default="patient"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
    )
    op.create_index("ix_mentions_document_id", "mentions", ["document_id"])
    op.create_index("ix_mentions_assertion", "mentions", ["assertion"])

    # Create mention_concept_candidates table
    op.create_table(
        "mention_concept_candidates",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "mention_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("mentions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("omop_concept_id", sa.Integer(), nullable=False),
        sa.Column("concept_name", sa.String(500), nullable=False),
        sa.Column("concept_code", sa.String(100), nullable=False),
        sa.Column("vocabulary_id", sa.String(50), nullable=False),
        sa.Column("domain_id", domain_enum, nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("method", sa.String(50), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
    )
    op.create_index(
        "ix_mention_concept_candidates_mention_id", "mention_concept_candidates", ["mention_id"]
    )
    op.create_index(
        "ix_mention_concept_candidates_omop_concept_id",
        "mention_concept_candidates",
        ["omop_concept_id"],
    )


def downgrade() -> None:
    op.drop_table("mention_concept_candidates")
    op.drop_table("mentions")

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS domain_type")
    op.execute("DROP TYPE IF EXISTS experiencer_type")
    op.execute("DROP TYPE IF EXISTS temporality_type")
    op.execute("DROP TYPE IF EXISTS assertion_type")
