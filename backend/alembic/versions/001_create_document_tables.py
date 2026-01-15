"""Create document and structured_resource tables.

Revision ID: 001
Revises: None
Create Date: 2026-01-14

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create job_status enum type
    job_status_enum = postgresql.ENUM(
        "queued",
        "processing",
        "completed",
        "failed",
        name="job_status",
        create_type=False,
    )
    job_status_enum.create(op.get_bind(), checkfirst=True)

    # Create resource_type enum type
    resource_type_enum = postgresql.ENUM(
        "fhir_bundle",
        "csv",
        name="resource_type",
        create_type=False,
    )
    resource_type_enum.create(op.get_bind(), checkfirst=True)

    # Create documents table
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("patient_id", sa.String(255), nullable=False),
        sa.Column("note_type", sa.String(100), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column(
            "status",
            job_status_enum,
            nullable=False,
            server_default="queued",
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_documents_patient_id", "documents", ["patient_id"])
    op.create_index("ix_documents_status", "documents", ["status"])

    # Create structured_resources table
    op.create_table(
        "structured_resources",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("patient_id", sa.String(255), nullable=False),
        sa.Column("resource_type", resource_type_enum, nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column(
            "status",
            job_status_enum,
            nullable=False,
            server_default="queued",
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_structured_resources_patient_id", "structured_resources", ["patient_id"])
    op.create_index("ix_structured_resources_status", "structured_resources", ["status"])


def downgrade() -> None:
    op.drop_table("structured_resources")
    op.drop_table("documents")

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS resource_type")
    op.execute("DROP TYPE IF EXISTS job_status")
