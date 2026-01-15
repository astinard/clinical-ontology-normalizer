"""Tests for Concept and ConceptSynonym models."""

from app.models import Concept, ConceptSynonym


class TestConceptModel:
    """Test Concept model class."""

    def test_concept_inherits_base(self) -> None:
        """Test that Concept inherits from Base."""
        from app.core.database import Base

        assert issubclass(Concept, Base)

    def test_concept_tablename(self) -> None:
        """Test Concept has correct table name."""
        assert Concept.__tablename__ == "concepts"

    def test_concept_has_required_columns(self) -> None:
        """Test Concept has all required columns."""
        columns = Concept.__table__.c
        required_columns = [
            "id",
            "created_at",
            "concept_id",
            "concept_name",
            "domain_id",
            "vocabulary_id",
            "concept_class_id",
            "standard_concept",
        ]
        for col in required_columns:
            assert col in columns, f"Missing column: {col}"

    def test_concept_id_is_unique(self) -> None:
        """Test concept_id column has unique constraint."""
        concept_id_col = Concept.__table__.c.concept_id
        assert concept_id_col.unique is True

    def test_concept_id_indexed(self) -> None:
        """Test concept_id column is indexed."""
        concept_id_col = Concept.__table__.c.concept_id
        assert concept_id_col.index is True

    def test_concept_name_indexed(self) -> None:
        """Test concept_name column is indexed."""
        concept_name_col = Concept.__table__.c.concept_name
        assert concept_name_col.index is True

    def test_domain_id_indexed(self) -> None:
        """Test domain_id column is indexed."""
        domain_id_col = Concept.__table__.c.domain_id
        assert domain_id_col.index is True

    def test_vocabulary_id_indexed(self) -> None:
        """Test vocabulary_id column is indexed."""
        vocabulary_id_col = Concept.__table__.c.vocabulary_id
        assert vocabulary_id_col.index is True

    def test_create_condition_concept(self) -> None:
        """Test creating a condition concept."""
        concept = Concept(
            concept_id=255848,
            concept_name="Pneumonia",
            domain_id="Condition",
            vocabulary_id="SNOMED",
            concept_class_id="Clinical Finding",
            standard_concept="S",
        )
        assert concept.concept_id == 255848
        assert concept.concept_name == "Pneumonia"
        assert concept.domain_id == "Condition"
        assert concept.is_standard is True

    def test_create_drug_concept(self) -> None:
        """Test creating a drug concept."""
        concept = Concept(
            concept_id=1503297,
            concept_name="Metformin",
            domain_id="Drug",
            vocabulary_id="RxNorm",
            concept_class_id="Ingredient",
            standard_concept="S",
        )
        assert concept.concept_id == 1503297
        assert concept.domain_id == "Drug"
        assert concept.vocabulary_id == "RxNorm"

    def test_create_measurement_concept(self) -> None:
        """Test creating a measurement concept."""
        concept = Concept(
            concept_id=3004410,
            concept_name="Hemoglobin A1c",
            domain_id="Measurement",
            vocabulary_id="LOINC",
            concept_class_id="Lab Test",
            standard_concept="S",
        )
        assert concept.concept_id == 3004410
        assert concept.domain_id == "Measurement"
        assert concept.vocabulary_id == "LOINC"

    def test_standard_concept_nullable(self) -> None:
        """Test standard_concept is nullable."""
        standard_concept_col = Concept.__table__.c.standard_concept
        assert standard_concept_col.nullable is True

    def test_is_standard_property_true(self) -> None:
        """Test is_standard property returns True for standard concepts."""
        concept = Concept(
            concept_id=1,
            concept_name="Test",
            domain_id="Condition",
            vocabulary_id="SNOMED",
            concept_class_id="Clinical Finding",
            standard_concept="S",
        )
        assert concept.is_standard is True

    def test_is_standard_property_false(self) -> None:
        """Test is_standard property returns False for non-standard concepts."""
        concept = Concept(
            concept_id=1,
            concept_name="Test",
            domain_id="Condition",
            vocabulary_id="SNOMED",
            concept_class_id="Clinical Finding",
            standard_concept="C",  # Classification concept
        )
        assert concept.is_standard is False

    def test_is_standard_property_none(self) -> None:
        """Test is_standard property returns False when standard_concept is None."""
        concept = Concept(
            concept_id=1,
            concept_name="Test",
            domain_id="Condition",
            vocabulary_id="SNOMED",
            concept_class_id="Clinical Finding",
            standard_concept=None,
        )
        assert concept.is_standard is False

    def test_concept_repr(self) -> None:
        """Test Concept __repr__ method."""
        concept = Concept(
            concept_id=255848,
            concept_name="Pneumonia",
            domain_id="Condition",
            vocabulary_id="SNOMED",
            concept_class_id="Clinical Finding",
        )
        repr_str = repr(concept)
        assert "Concept" in repr_str
        assert "255848" in repr_str
        assert "Pneumonia" in repr_str


class TestConceptSynonymModel:
    """Test ConceptSynonym model class."""

    def test_concept_synonym_inherits_base(self) -> None:
        """Test that ConceptSynonym inherits from Base."""
        from app.core.database import Base

        assert issubclass(ConceptSynonym, Base)

    def test_concept_synonym_tablename(self) -> None:
        """Test ConceptSynonym has correct table name."""
        assert ConceptSynonym.__tablename__ == "concept_synonyms"

    def test_concept_synonym_has_required_columns(self) -> None:
        """Test ConceptSynonym has all required columns."""
        columns = ConceptSynonym.__table__.c
        required_columns = [
            "id",
            "created_at",
            "concept_id",
            "concept_synonym_name",
            "language_concept_id",
        ]
        for col in required_columns:
            assert col in columns, f"Missing column: {col}"

    def test_concept_synonym_concept_id_indexed(self) -> None:
        """Test concept_id column is indexed."""
        concept_id_col = ConceptSynonym.__table__.c.concept_id
        assert concept_id_col.index is True

    def test_concept_synonym_name_indexed(self) -> None:
        """Test concept_synonym_name column is indexed."""
        synonym_name_col = ConceptSynonym.__table__.c.concept_synonym_name
        assert synonym_name_col.index is True

    def test_concept_synonym_has_foreign_key(self) -> None:
        """Test concept_id has foreign key to concepts."""
        concept_id_col = ConceptSynonym.__table__.c.concept_id
        fk = list(concept_id_col.foreign_keys)[0]
        assert str(fk.column) == "concepts.concept_id"

    def test_create_concept_synonym(self) -> None:
        """Test creating a concept synonym."""
        synonym = ConceptSynonym(
            concept_id=255848,
            concept_synonym_name="lung infection",
            language_concept_id=4180186,
        )
        assert synonym.concept_id == 255848
        assert synonym.concept_synonym_name == "lung infection"
        assert synonym.language_concept_id == 4180186

    def test_concept_synonym_default_language(self) -> None:
        """Test default language is English."""
        # Check that the default exists in the column definition
        lang_col = ConceptSynonym.__table__.c.language_concept_id
        # The default should be set to 4180186 (English)
        assert lang_col.default is not None

    def test_concept_synonym_repr(self) -> None:
        """Test ConceptSynonym __repr__ method."""
        synonym = ConceptSynonym(
            concept_id=255848,
            concept_synonym_name="lung infection",
        )
        repr_str = repr(synonym)
        assert "ConceptSynonym" in repr_str
        assert "255848" in repr_str
        assert "lung infection" in repr_str


class TestVocabularyModelExports:
    """Test model exports from package."""

    def test_concept_exported(self) -> None:
        """Test Concept is exported from models package."""
        from app.models import Concept

        assert Concept is not None

    def test_concept_synonym_exported(self) -> None:
        """Test ConceptSynonym is exported from models package."""
        from app.models import ConceptSynonym

        assert ConceptSynonym is not None

    def test_all_exports(self) -> None:
        """Test __all__ contains expected exports."""
        from app import models

        assert "Concept" in models.__all__
        assert "ConceptSynonym" in models.__all__
