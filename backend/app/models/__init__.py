"""SQLAlchemy ORM models for Clinical Ontology Normalizer.

All models inherit from Base which provides:
- id: UUID primary key
- created_at: Timestamp

Models will be added in subsequent tasks:
- Document, StructuredResource (task 2.3)
- Mention, MentionConceptCandidate (task 2.4)
- ClinicalFact, FactEvidence (task 2.5)
- KGNode, KGEdge (task 2.6)
"""

from app.core.database import Base

__all__ = ["Base"]
