"""Add job_id columns to documents and structured_resources.

Revision ID: 006
Revises: 005
Create Date: 2026-01-14
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add job_id column to documents and structured_resources tables."""
    # Add job_id to documents
    op.add_column(
        "documents",
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_documents_job_id", "documents", ["job_id"], unique=False)

    # Add job_id to structured_resources
    op.add_column(
        "structured_resources",
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        "ix_structured_resources_job_id", "structured_resources", ["job_id"], unique=False
    )


def downgrade() -> None:
    """Remove job_id columns."""
    op.drop_index("ix_structured_resources_job_id", table_name="structured_resources")
    op.drop_column("structured_resources", "job_id")

    op.drop_index("ix_documents_job_id", table_name="documents")
    op.drop_column("documents", "job_id")
