"""Add embedding column to concepts for semantic search.

Revision ID: 012
Revises: 011
Create Date: 2026-01-15

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "012"
down_revision: str | None = "011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Embedding dimension for all-MiniLM-L6-v2 model
EMBEDDING_DIM = 384


def upgrade() -> None:
    # Add embedding column to concepts table for semantic search
    # ARRAY type stores the 384-dimensional embedding vector
    op.add_column(
        "concepts",
        sa.Column(
            "embedding",
            postgresql.ARRAY(sa.Float()),
            nullable=True,
        ),
    )

    # Add index for efficient embedding lookups
    # Using a partial index to only index concepts that have embeddings
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_concepts_embedding_not_null
        ON concepts (concept_id)
        WHERE embedding IS NOT NULL
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_concepts_embedding_not_null")
    op.drop_column("concepts", "embedding")
