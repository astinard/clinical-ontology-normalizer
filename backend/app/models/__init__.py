"""SQLAlchemy ORM models for Clinical Ontology Normalizer.

All models inherit from Base which provides:
- id: UUID primary key
- created_at: Timestamp

Models:
- Document, StructuredResource (task 2.3)
- Mention, MentionConceptCandidate (task 2.4)
- ClinicalFact, FactEvidence (task 2.5)
- KGNode, KGEdge (task 2.6)
"""

from app.core.database import Base
from app.models.clinical_fact import ClinicalFact, FactEvidence
from app.models.document import Document, StructuredResource
from app.models.knowledge_graph import KGEdge, KGNode
from app.models.mention import Mention, MentionConceptCandidate

__all__ = [
    "Base",
    "Document",
    "StructuredResource",
    "Mention",
    "MentionConceptCandidate",
    "ClinicalFact",
    "FactEvidence",
    "KGNode",
    "KGEdge",
]
