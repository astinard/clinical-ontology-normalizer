"""Create clinical_facts and fact_evidence tables.

Revision ID: 003
Revises: 002
Create Date: 2026-01-14

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create evidence_type enum
    evidence_type_enum = postgresql.ENUM(
        "mention",
        "structured",
        "inferred",
        name="evidence_type",
        create_type=False,
    )
    evidence_type_enum.create(op.get_bind(), checkfirst=True)

    # Create clinical_facts table
    op.create_table(
        "clinical_facts",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("patient_id", sa.String(255), nullable=False),
        sa.Column(
            "domain",
            sa.Enum(
                "condition",
                "drug",
                "measurement",
                "procedure",
                "observation",
                "device",
                "visit",
                name="domain_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("omop_concept_id", sa.Integer(), nullable=False),
        sa.Column("concept_name", sa.String(500), nullable=False),
        sa.Column(
            "assertion",
            sa.Enum("present", "absent", "possible", name="assertion_type", create_type=False),
            nullable=False,
            server_default="present",
        ),
        sa.Column(
            "temporality",
            sa.Enum("current", "past", "future", name="temporality_type", create_type=False),
            nullable=False,
            server_default="current",
        ),
        sa.Column(
            "experiencer",
            sa.Enum("patient", "family", "other", name="experiencer_type", create_type=False),
            nullable=False,
            server_default="patient",
        ),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("value", sa.String(255), nullable=True),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_clinical_facts_patient_id", "clinical_facts", ["patient_id"])
    op.create_index("ix_clinical_facts_domain", "clinical_facts", ["domain"])
    op.create_index("ix_clinical_facts_omop_concept_id", "clinical_facts", ["omop_concept_id"])
    op.create_index("ix_clinical_facts_assertion", "clinical_facts", ["assertion"])

    # Create fact_evidence table
    op.create_table(
        "fact_evidence",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "fact_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("clinical_facts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("evidence_type", evidence_type_enum, nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("source_table", sa.String(100), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_fact_evidence_fact_id", "fact_evidence", ["fact_id"])


def downgrade() -> None:
    op.drop_table("fact_evidence")
    op.drop_table("clinical_facts")

    # Drop enum type
    op.execute("DROP TYPE IF EXISTS evidence_type")
