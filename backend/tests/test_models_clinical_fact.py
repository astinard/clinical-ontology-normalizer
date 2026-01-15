"""Tests for ClinicalFact and FactEvidence models."""

from app.models import ClinicalFact, FactEvidence
from app.schemas.base import Assertion, Domain, Experiencer, Temporality
from app.schemas.clinical_fact import EvidenceType


class TestClinicalFactModel:
    """Test ClinicalFact model class."""

    def test_clinical_fact_inherits_base(self) -> None:
        """Test that ClinicalFact inherits from Base."""
        from app.core.database import Base

        assert issubclass(ClinicalFact, Base)

    def test_clinical_fact_tablename(self) -> None:
        """Test ClinicalFact has correct table name."""
        assert ClinicalFact.__tablename__ == "clinical_facts"

    def test_clinical_fact_has_required_columns(self) -> None:
        """Test ClinicalFact has all required columns."""
        columns = ClinicalFact.__table__.c
        required_columns = [
            "id",
            "created_at",
            "patient_id",
            "domain",
            "omop_concept_id",
            "concept_name",
            "assertion",
            "temporality",
            "experiencer",
            "confidence",
            "value",
            "unit",
            "start_date",
            "end_date",
        ]
        for col in required_columns:
            assert col in columns, f"Missing column: {col}"

    def test_clinical_fact_patient_id_indexed(self) -> None:
        """Test patient_id column is indexed."""
        patient_id_col = ClinicalFact.__table__.c.patient_id
        assert patient_id_col.index is True

    def test_clinical_fact_domain_indexed(self) -> None:
        """Test domain column is indexed."""
        domain_col = ClinicalFact.__table__.c.domain
        assert domain_col.index is True

    def test_clinical_fact_omop_concept_id_indexed(self) -> None:
        """Test omop_concept_id column is indexed."""
        concept_id_col = ClinicalFact.__table__.c.omop_concept_id
        assert concept_id_col.index is True

    def test_clinical_fact_assertion_indexed(self) -> None:
        """Test assertion column is indexed."""
        assertion_col = ClinicalFact.__table__.c.assertion
        assert assertion_col.index is True

    def test_create_clinical_fact_condition(self) -> None:
        """Test creating a ClinicalFact for a condition."""
        fact = ClinicalFact(
            patient_id="P001",
            domain=Domain.CONDITION,
            omop_concept_id=233604007,
            concept_name="Pneumonia",
            assertion=Assertion.ABSENT,
            temporality=Temporality.CURRENT,
            experiencer=Experiencer.PATIENT,
            confidence=0.95,
        )
        assert fact.patient_id == "P001"
        assert fact.domain == Domain.CONDITION
        assert fact.is_negated is True

    def test_create_clinical_fact_measurement(self) -> None:
        """Test creating a ClinicalFact for a measurement."""
        fact = ClinicalFact(
            patient_id="P001",
            domain=Domain.MEASUREMENT,
            omop_concept_id=4548,
            concept_name="Hemoglobin A1c",
            value="7.2",
            unit="%",
        )
        assert fact.domain == Domain.MEASUREMENT
        assert fact.value == "7.2"
        assert fact.unit == "%"

    def test_clinical_fact_is_negated_property(self) -> None:
        """Test is_negated property."""
        negated_fact = ClinicalFact(
            patient_id="P001",
            domain=Domain.CONDITION,
            omop_concept_id=1,
            concept_name="Test",
            assertion=Assertion.ABSENT,
        )
        assert negated_fact.is_negated is True

        present_fact = ClinicalFact(
            patient_id="P001",
            domain=Domain.CONDITION,
            omop_concept_id=1,
            concept_name="Test",
            assertion=Assertion.PRESENT,
        )
        assert present_fact.is_negated is False

    def test_clinical_fact_is_uncertain_property(self) -> None:
        """Test is_uncertain property."""
        uncertain_fact = ClinicalFact(
            patient_id="P001",
            domain=Domain.CONDITION,
            omop_concept_id=1,
            concept_name="Test",
            assertion=Assertion.POSSIBLE,
        )
        assert uncertain_fact.is_uncertain is True

    def test_clinical_fact_is_family_history_property(self) -> None:
        """Test is_family_history property."""
        family_fact = ClinicalFact(
            patient_id="P001",
            domain=Domain.CONDITION,
            omop_concept_id=93761005,
            concept_name="Colon cancer",
            experiencer=Experiencer.FAMILY,
        )
        assert family_fact.is_family_history is True

        patient_fact = ClinicalFact(
            patient_id="P001",
            domain=Domain.CONDITION,
            omop_concept_id=1,
            concept_name="Test",
            experiencer=Experiencer.PATIENT,
        )
        assert patient_fact.is_family_history is False

    def test_clinical_fact_default_assertion(self) -> None:
        """Test ClinicalFact assertion column has PRESENT as default."""
        assertion_col = ClinicalFact.__table__.c.assertion
        assert assertion_col.default is not None
        assert assertion_col.default.arg == Assertion.PRESENT

    def test_clinical_fact_value_nullable(self) -> None:
        """Test value column is nullable."""
        value_col = ClinicalFact.__table__.c.value
        assert value_col.nullable is True

    def test_clinical_fact_repr(self) -> None:
        """Test ClinicalFact __repr__ method."""
        fact = ClinicalFact(
            id="550e8400-e29b-41d4-a716-446655440000",
            patient_id="P001",
            domain=Domain.CONDITION,
            omop_concept_id=233604007,
            concept_name="Pneumonia",
            assertion=Assertion.ABSENT,
        )
        repr_str = repr(fact)
        assert "ClinicalFact" in repr_str
        assert "P001" in repr_str
        assert "Pneumonia" in repr_str


class TestFactEvidenceModel:
    """Test FactEvidence model class."""

    def test_fact_evidence_inherits_base(self) -> None:
        """Test that FactEvidence inherits from Base."""
        from app.core.database import Base

        assert issubclass(FactEvidence, Base)

    def test_fact_evidence_tablename(self) -> None:
        """Test FactEvidence has correct table name."""
        assert FactEvidence.__tablename__ == "fact_evidence"

    def test_fact_evidence_has_required_columns(self) -> None:
        """Test FactEvidence has all required columns."""
        columns = FactEvidence.__table__.c
        required_columns = [
            "id",
            "created_at",
            "fact_id",
            "evidence_type",
            "source_id",
            "source_table",
            "weight",
            "notes",
        ]
        for col in required_columns:
            assert col in columns, f"Missing column: {col}"

    def test_fact_evidence_fact_id_indexed(self) -> None:
        """Test fact_id column is indexed."""
        fact_id_col = FactEvidence.__table__.c.fact_id
        assert fact_id_col.index is True

    def test_create_fact_evidence_mention(self) -> None:
        """Test creating FactEvidence from a mention."""
        evidence = FactEvidence(
            fact_id="550e8400-e29b-41d4-a716-446655440000",
            evidence_type=EvidenceType.MENTION,
            source_id="660e8400-e29b-41d4-a716-446655440000",
            source_table="mentions",
            weight=0.9,
        )
        assert evidence.evidence_type == EvidenceType.MENTION
        assert evidence.source_table == "mentions"

    def test_create_fact_evidence_structured(self) -> None:
        """Test creating FactEvidence from structured data."""
        evidence = FactEvidence(
            fact_id="550e8400-e29b-41d4-a716-446655440000",
            evidence_type=EvidenceType.STRUCTURED,
            source_id="660e8400-e29b-41d4-a716-446655440000",
            source_table="structured_resources",
            weight=1.0,
        )
        assert evidence.evidence_type == EvidenceType.STRUCTURED

    def test_fact_evidence_has_foreign_key(self) -> None:
        """Test fact_id has foreign key to clinical_facts."""
        fact_id_col = FactEvidence.__table__.c.fact_id
        fk = list(fact_id_col.foreign_keys)[0]
        assert str(fk.column) == "clinical_facts.id"

    def test_fact_evidence_notes_nullable(self) -> None:
        """Test notes column is nullable."""
        notes_col = FactEvidence.__table__.c.notes
        assert notes_col.nullable is True

    def test_fact_evidence_default_weight(self) -> None:
        """Test weight has default value."""
        weight_col = FactEvidence.__table__.c.weight
        assert weight_col.default is not None
        assert weight_col.default.arg == 1.0

    def test_fact_evidence_repr(self) -> None:
        """Test FactEvidence __repr__ method."""
        evidence = FactEvidence(
            id="550e8400-e29b-41d4-a716-446655440000",
            fact_id="660e8400-e29b-41d4-a716-446655440000",
            evidence_type=EvidenceType.MENTION,
            source_id="770e8400-e29b-41d4-a716-446655440000",
            source_table="mentions",
        )
        repr_str = repr(evidence)
        assert "FactEvidence" in repr_str
        assert "mentions" in repr_str


class TestClinicalFactModelExports:
    """Test model exports from package."""

    def test_clinical_fact_exported(self) -> None:
        """Test ClinicalFact is exported from models package."""
        from app.models import ClinicalFact

        assert ClinicalFact is not None

    def test_fact_evidence_exported(self) -> None:
        """Test FactEvidence is exported from models package."""
        from app.models import FactEvidence

        assert FactEvidence is not None

    def test_all_exports(self) -> None:
        """Test __all__ contains expected exports."""
        from app import models

        assert "ClinicalFact" in models.__all__
        assert "FactEvidence" in models.__all__
