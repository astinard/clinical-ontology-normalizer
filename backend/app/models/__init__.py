"""SQLAlchemy ORM models for Clinical Ontology Normalizer.

All models inherit from Base which provides:
- id: UUID primary key
- created_at: Timestamp

Models:
- Document, StructuredResource (task 2.3)
- Mention, MentionConceptCandidate (task 2.4) - pending
- ClinicalFact, FactEvidence (task 2.5) - pending
- KGNode, KGEdge (task 2.6) - pending
"""

from app.core.database import Base
from app.models.document import Document, StructuredResource

__all__ = ["Base", "Document", "StructuredResource"]
