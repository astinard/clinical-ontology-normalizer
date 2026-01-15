"""Tests for Mention and MentionConceptCandidate models."""

from app.models import Mention, MentionConceptCandidate
from app.schemas.base import Assertion, Domain, Experiencer, Temporality


class TestMentionModel:
    """Test Mention model class."""

    def test_mention_inherits_base(self) -> None:
        """Test that Mention inherits from Base."""
        from app.core.database import Base

        assert issubclass(Mention, Base)

    def test_mention_tablename(self) -> None:
        """Test Mention has correct table name."""
        assert Mention.__tablename__ == "mentions"

    def test_mention_has_required_columns(self) -> None:
        """Test Mention has all required columns."""
        columns = Mention.__table__.c
        required_columns = [
            "id", "created_at", "document_id", "text", "start_offset",
            "end_offset", "lexical_variant", "section", "assertion",
            "temporality", "experiencer", "confidence"
        ]
        for col in required_columns:
            assert col in columns, f"Missing column: {col}"

    def test_mention_document_id_indexed(self) -> None:
        """Test document_id column is indexed."""
        doc_id_col = Mention.__table__.c.document_id
        assert doc_id_col.index is True

    def test_mention_assertion_indexed(self) -> None:
        """Test assertion column is indexed."""
        assertion_col = Mention.__table__.c.assertion
        assert assertion_col.index is True

    def test_create_mention_instance(self) -> None:
        """Test creating a Mention instance."""
        mention = Mention(
            document_id="550e8400-e29b-41d4-a716-446655440000",
            text="pneumonia",
            start_offset=10,
            end_offset=19,
            lexical_variant="pneumonia",
            assertion=Assertion.ABSENT,
            temporality=Temporality.CURRENT,
            experiencer=Experiencer.PATIENT,
            confidence=0.95,
        )
        assert mention.text == "pneumonia"
        assert mention.assertion == Assertion.ABSENT
        assert mention.is_negated is True

    def test_mention_default_assertion(self) -> None:
        """Test Mention assertion column has PRESENT as default."""
        assertion_col = Mention.__table__.c.assertion
        assert assertion_col.default is not None
        assert assertion_col.default.arg == Assertion.PRESENT

    def test_mention_default_temporality(self) -> None:
        """Test Mention temporality column has CURRENT as default."""
        temporality_col = Mention.__table__.c.temporality
        assert temporality_col.default is not None
        assert temporality_col.default.arg == Temporality.CURRENT

    def test_mention_default_experiencer(self) -> None:
        """Test Mention experiencer column has PATIENT as default."""
        experiencer_col = Mention.__table__.c.experiencer
        assert experiencer_col.default is not None
        assert experiencer_col.default.arg == Experiencer.PATIENT

    def test_mention_is_negated_property(self) -> None:
        """Test is_negated property."""
        mention_negated = Mention(
            document_id="550e8400-e29b-41d4-a716-446655440000",
            text="chest pain",
            start_offset=0,
            end_offset=10,
            lexical_variant="chest pain",
            assertion=Assertion.ABSENT,
        )
        assert mention_negated.is_negated is True

        mention_present = Mention(
            document_id="550e8400-e29b-41d4-a716-446655440000",
            text="chest pain",
            start_offset=0,
            end_offset=10,
            lexical_variant="chest pain",
            assertion=Assertion.PRESENT,
        )
        assert mention_present.is_negated is False

    def test_mention_section_nullable(self) -> None:
        """Test section is nullable."""
        section_col = Mention.__table__.c.section
        assert section_col.nullable is True

    def test_mention_repr(self) -> None:
        """Test Mention __repr__ method."""
        mention = Mention(
            id="550e8400-e29b-41d4-a716-446655440000",
            document_id="660e8400-e29b-41d4-a716-446655440000",
            text="congestive heart failure",
            start_offset=0,
            end_offset=24,
            lexical_variant="CHF",
            assertion=Assertion.PRESENT,
        )
        repr_str = repr(mention)
        assert "Mention" in repr_str
        assert "congestive heart failure" in repr_str

    def test_mention_has_foreign_key(self) -> None:
        """Test document_id has foreign key to documents."""
        doc_id_col = Mention.__table__.c.document_id
        fk = list(doc_id_col.foreign_keys)[0]
        assert str(fk.column) == "documents.id"


class TestMentionConceptCandidateModel:
    """Test MentionConceptCandidate model class."""

    def test_concept_candidate_inherits_base(self) -> None:
        """Test that MentionConceptCandidate inherits from Base."""
        from app.core.database import Base

        assert issubclass(MentionConceptCandidate, Base)

    def test_concept_candidate_tablename(self) -> None:
        """Test MentionConceptCandidate has correct table name."""
        assert MentionConceptCandidate.__tablename__ == "mention_concept_candidates"

    def test_concept_candidate_has_required_columns(self) -> None:
        """Test MentionConceptCandidate has all required columns."""
        columns = MentionConceptCandidate.__table__.c
        required_columns = [
            "id", "created_at", "mention_id", "omop_concept_id",
            "concept_name", "concept_code", "vocabulary_id",
            "domain_id", "score", "method", "rank"
        ]
        for col in required_columns:
            assert col in columns, f"Missing column: {col}"

    def test_concept_candidate_mention_id_indexed(self) -> None:
        """Test mention_id column is indexed."""
        mention_id_col = MentionConceptCandidate.__table__.c.mention_id
        assert mention_id_col.index is True

    def test_concept_candidate_omop_concept_id_indexed(self) -> None:
        """Test omop_concept_id column is indexed."""
        concept_id_col = MentionConceptCandidate.__table__.c.omop_concept_id
        assert concept_id_col.index is True

    def test_create_concept_candidate_instance(self) -> None:
        """Test creating a MentionConceptCandidate instance."""
        candidate = MentionConceptCandidate(
            mention_id="550e8400-e29b-41d4-a716-446655440000",
            omop_concept_id=233604007,
            concept_name="Pneumonia",
            concept_code="233604007",
            vocabulary_id="SNOMED",
            domain_id=Domain.CONDITION,
            score=0.95,
            method="exact",
            rank=1,
        )
        assert candidate.omop_concept_id == 233604007
        assert candidate.concept_name == "Pneumonia"
        assert candidate.domain_id == Domain.CONDITION
        assert candidate.rank == 1

    def test_concept_candidate_has_foreign_key(self) -> None:
        """Test mention_id has foreign key to mentions."""
        mention_id_col = MentionConceptCandidate.__table__.c.mention_id
        fk = list(mention_id_col.foreign_keys)[0]
        assert str(fk.column) == "mentions.id"

    def test_concept_candidate_repr(self) -> None:
        """Test MentionConceptCandidate __repr__ method."""
        candidate = MentionConceptCandidate(
            id="550e8400-e29b-41d4-a716-446655440000",
            mention_id="660e8400-e29b-41d4-a716-446655440000",
            omop_concept_id=233604007,
            concept_name="Pneumonia",
            concept_code="233604007",
            vocabulary_id="SNOMED",
            domain_id=Domain.CONDITION,
            score=0.95,
            method="exact",
            rank=1,
        )
        repr_str = repr(candidate)
        assert "MentionConceptCandidate" in repr_str
        assert "Pneumonia" in repr_str


class TestMentionModelExports:
    """Test model exports from package."""

    def test_mention_exported(self) -> None:
        """Test Mention is exported from models package."""
        from app.models import Mention

        assert Mention is not None

    def test_concept_candidate_exported(self) -> None:
        """Test MentionConceptCandidate is exported from models package."""
        from app.models import MentionConceptCandidate

        assert MentionConceptCandidate is not None

    def test_all_exports(self) -> None:
        """Test __all__ contains expected exports."""
        from app import models

        assert "Mention" in models.__all__
        assert "MentionConceptCandidate" in models.__all__
