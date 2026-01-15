"""SQLAlchemy models for OMOP vocabulary concepts."""

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Concept(Base):
    """OMOP Concept table (simplified for local development).

    This is a subset of the OMOP CDM CONCEPT table containing
    only the fields needed for concept lookup and mapping.

    Note: Uses UUID id from Base for internal tracking, but concept_id
    is the OMOP-standard identifier used for lookups and mapping.
    """

    __tablename__ = "concepts"

    concept_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        unique=True,
        index=True,
    )
    concept_name: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        index=True,
    )
    domain_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    vocabulary_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    concept_class_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    standard_concept: Mapped[str | None] = mapped_column(
        String(1),
        nullable=True,
    )

    # Relationship to synonyms
    synonyms = relationship(
        "ConceptSynonym",
        back_populates="concept",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Concept(concept_id={self.concept_id}, name='{self.concept_name}', domain='{self.domain_id}')>"

    @property
    def is_standard(self) -> bool:
        """Check if this is a standard concept."""
        return bool(self.standard_concept == "S")


class ConceptSynonym(Base):
    """OMOP Concept Synonym table for fuzzy matching.

    Stores alternative names for concepts to improve matching.
    """

    __tablename__ = "concept_synonyms"

    concept_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("concepts.concept_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    concept_synonym_name: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
        index=True,
    )
    language_concept_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=4180186,  # English
    )

    # Relationship to concept
    concept = relationship("Concept", back_populates="synonyms")

    def __repr__(self) -> str:
        return f"<ConceptSynonym(concept_id={self.concept_id}, name='{self.concept_synonym_name}')>"
