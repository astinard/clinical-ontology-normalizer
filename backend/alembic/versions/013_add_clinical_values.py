"""Add clinical_values table for extracted numeric data.

Revision ID: 013
Revises: 012
Create Date: 2026-01-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "013"
down_revision: str | None = "012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create enum for value types
    value_type_enum = postgresql.ENUM(
        "lab_result",
        "vital_sign",
        "medication_dose",
        "measurement",
        "score",
        name="value_type",
        create_type=False,
    )
    value_type_enum.create(op.get_bind(), checkfirst=True)

    # Create clinical_values table
    op.create_table(
        "clinical_values",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("patient_id", sa.String(255), nullable=False),
        sa.Column("value_type", value_type_enum, nullable=False),
        sa.Column("text", sa.String(500), nullable=False),
        sa.Column("start_offset", sa.Integer(), nullable=False),
        sa.Column("end_offset", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("value", sa.Float(), nullable=True),
        sa.Column("value_secondary", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("unit_normalized", sa.String(50), nullable=True),
        sa.Column("frequency", sa.String(50), nullable=True),
        sa.Column("route", sa.String(50), nullable=True),
        sa.Column("omop_concept_id", sa.Integer(), nullable=True),
        sa.Column("interpretation", sa.String(50), nullable=True),
        sa.Column("reference_low", sa.Float(), nullable=True),
        sa.Column("reference_high", sa.Float(), nullable=True),
        sa.Column("section", sa.String(100), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.8"),
        sa.Column("metadata", postgresql.JSONB(), nullable=True, server_default="{}"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
    )

    # Create indexes
    op.create_index("ix_clinical_values_document_id", "clinical_values", ["document_id"])
    op.create_index("ix_clinical_values_patient_id", "clinical_values", ["patient_id"])
    op.create_index("ix_clinical_values_value_type", "clinical_values", ["value_type"])
    op.create_index("ix_clinical_values_name", "clinical_values", ["name"])
    op.create_index("ix_clinical_values_omop_concept_id", "clinical_values", ["omop_concept_id"])


def downgrade() -> None:
    op.drop_table("clinical_values")
    op.execute("DROP TYPE IF EXISTS value_type")
