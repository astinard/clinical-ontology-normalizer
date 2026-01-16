"""Add advanced KG properties for AI scribe and billing.

Revision ID: 011
Revises: 010
Create Date: 2026-01-15

Adds 10 advanced properties:
1. OMOP Standardization - Already exists (omop_concept_id)
2. Temporal Modeling - onset_date, resolved_date, duration_days
3. Negation Handling - Enhanced assertion types
4. Vector Embeddings - embedding column for semantic search
5. Hierarchical Entities - concept_ancestor table
6. Provenance Tracking - author, document_section
7. Clinical Reasoning Chains - supporting_fact_ids, reasoning_notes
8. Real-time Processing - Architecture (not schema)
9. Uncertainty Propagation - confidence_lower, confidence_upper
10. Billing Properties - icd10_codes, cpt_codes, is_billable, medical_necessity_link
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSON, UUID


# revision identifiers, used by Alembic.
revision = "011"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # =========================================================================
    # CLINICAL FACTS ENHANCEMENTS
    # =========================================================================

    # Temporal Modeling
    op.add_column("clinical_facts", sa.Column("onset_date", sa.DateTime(timezone=True), nullable=True))
    op.add_column("clinical_facts", sa.Column("resolved_date", sa.DateTime(timezone=True), nullable=True))
    op.add_column("clinical_facts", sa.Column("duration_days", sa.Integer(), nullable=True))

    # Severity and Body Site
    op.add_column("clinical_facts", sa.Column("severity", sa.String(50), nullable=True))  # mild/moderate/severe
    op.add_column("clinical_facts", sa.Column("body_site", sa.String(100), nullable=True))  # left/right/bilateral
    op.add_column("clinical_facts", sa.Column("body_site_concept_id", sa.Integer(), nullable=True))

    # Lab-specific: reference range and abnormality
    op.add_column("clinical_facts", sa.Column("reference_range_low", sa.Float(), nullable=True))
    op.add_column("clinical_facts", sa.Column("reference_range_high", sa.Float(), nullable=True))
    op.add_column("clinical_facts", sa.Column("is_abnormal", sa.Boolean(), nullable=True))
    op.add_column("clinical_facts", sa.Column("trend", sa.String(50), nullable=True))  # improving/worsening/stable

    # Uncertainty Propagation
    op.add_column("clinical_facts", sa.Column("confidence_lower", sa.Float(), nullable=True))
    op.add_column("clinical_facts", sa.Column("confidence_upper", sa.Float(), nullable=True))

    # Provenance Enhancement
    op.add_column("clinical_facts", sa.Column("author_id", sa.String(255), nullable=True))
    op.add_column("clinical_facts", sa.Column("document_section", sa.String(100), nullable=True))

    # Clinical Reasoning Chains
    op.add_column("clinical_facts", sa.Column("supporting_fact_ids", ARRAY(UUID(as_uuid=False)), nullable=True))
    op.add_column("clinical_facts", sa.Column("reasoning_notes", sa.Text(), nullable=True))

    # Billing Properties
    op.add_column("clinical_facts", sa.Column("icd10_codes", ARRAY(sa.String(20)), nullable=True))
    op.add_column("clinical_facts", sa.Column("cpt_codes", ARRAY(sa.String(20)), nullable=True))
    op.add_column("clinical_facts", sa.Column("is_billable", sa.Boolean(), default=False, nullable=True))
    op.add_column("clinical_facts", sa.Column("is_primary_diagnosis", sa.Boolean(), default=False, nullable=True))
    op.add_column("clinical_facts", sa.Column("medical_necessity_fact_id", UUID(as_uuid=False), nullable=True))

    # Vector Embedding for semantic search
    # Using pgvector extension if available, otherwise JSON fallback
    op.add_column("clinical_facts", sa.Column("embedding", ARRAY(sa.Float()), nullable=True))

    # =========================================================================
    # KG NODE ENHANCEMENTS
    # =========================================================================

    # Vector embedding for nodes
    op.add_column("kg_nodes", sa.Column("embedding", ARRAY(sa.Float()), nullable=True))

    # Parent concept for hierarchy
    op.add_column("kg_nodes", sa.Column("parent_concept_id", sa.Integer(), nullable=True))

    # =========================================================================
    # KG EDGE ENHANCEMENTS
    # =========================================================================

    # Reasoning support
    op.add_column("kg_edges", sa.Column("reasoning_type", sa.String(50), nullable=True))  # inferred/explicit/causal
    op.add_column("kg_edges", sa.Column("confidence", sa.Float(), default=1.0, nullable=True))

    # =========================================================================
    # CONCEPT ANCESTOR TABLE (Hierarchical Entities)
    # =========================================================================

    op.create_table(
        "concept_ancestors",
        sa.Column("id", UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("ancestor_concept_id", sa.Integer(), nullable=False, index=True),
        sa.Column("descendant_concept_id", sa.Integer(), nullable=False, index=True),
        sa.Column("min_levels_of_separation", sa.Integer(), nullable=False),
        sa.Column("max_levels_of_separation", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # Composite index for hierarchy queries
    op.create_index(
        "ix_concept_ancestors_hierarchy",
        "concept_ancestors",
        ["ancestor_concept_id", "descendant_concept_id"],
        unique=True,
    )

    # =========================================================================
    # CONCEPT RELATIONSHIPS TABLE (for TREATS, CAUSES, etc.)
    # =========================================================================

    op.create_table(
        "concept_relationships",
        sa.Column("id", UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("concept_id_1", sa.Integer(), nullable=False, index=True),
        sa.Column("concept_id_2", sa.Integer(), nullable=False, index=True),
        sa.Column("relationship_id", sa.String(50), nullable=False, index=True),  # e.g., "Is a", "Mapped from", "Treats"
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # Index for relationship queries
    op.create_index(
        "ix_concept_relationships_lookup",
        "concept_relationships",
        ["concept_id_1", "relationship_id"],
    )

    # =========================================================================
    # BILLING CODES TABLE (for ICD10 <-> SNOMED mapping)
    # =========================================================================

    op.create_table(
        "billing_code_mappings",
        sa.Column("id", UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("snomed_concept_id", sa.Integer(), nullable=False, index=True),
        sa.Column("icd10_code", sa.String(20), nullable=True, index=True),
        sa.Column("cpt_code", sa.String(20), nullable=True, index=True),
        sa.Column("hcpcs_code", sa.String(20), nullable=True, index=True),
        sa.Column("mapping_type", sa.String(50), nullable=False),  # exact/approximate/broader/narrower
        sa.Column("priority", sa.Integer(), default=1),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )


def downgrade() -> None:
    # Drop new tables
    op.drop_table("billing_code_mappings")
    op.drop_table("concept_relationships")
    op.drop_table("concept_ancestors")

    # Drop KG edge columns
    op.drop_column("kg_edges", "confidence")
    op.drop_column("kg_edges", "reasoning_type")

    # Drop KG node columns
    op.drop_column("kg_nodes", "parent_concept_id")
    op.drop_column("kg_nodes", "embedding")

    # Drop clinical facts columns
    op.drop_column("clinical_facts", "embedding")
    op.drop_column("clinical_facts", "medical_necessity_fact_id")
    op.drop_column("clinical_facts", "is_primary_diagnosis")
    op.drop_column("clinical_facts", "is_billable")
    op.drop_column("clinical_facts", "cpt_codes")
    op.drop_column("clinical_facts", "icd10_codes")
    op.drop_column("clinical_facts", "reasoning_notes")
    op.drop_column("clinical_facts", "supporting_fact_ids")
    op.drop_column("clinical_facts", "document_section")
    op.drop_column("clinical_facts", "author_id")
    op.drop_column("clinical_facts", "confidence_upper")
    op.drop_column("clinical_facts", "confidence_lower")
    op.drop_column("clinical_facts", "trend")
    op.drop_column("clinical_facts", "is_abnormal")
    op.drop_column("clinical_facts", "reference_range_high")
    op.drop_column("clinical_facts", "reference_range_low")
    op.drop_column("clinical_facts", "body_site_concept_id")
    op.drop_column("clinical_facts", "body_site")
    op.drop_column("clinical_facts", "severity")
    op.drop_column("clinical_facts", "duration_days")
    op.drop_column("clinical_facts", "resolved_date")
    op.drop_column("clinical_facts", "onset_date")
