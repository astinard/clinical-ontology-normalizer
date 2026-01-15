"""Tests for fact builder service interface."""

from uuid import uuid4

import pytest

from app.schemas.base import Assertion, Domain, Experiencer, Temporality
from app.schemas.clinical_fact import EvidenceType
from app.services import (
    BaseFactBuilderService,
    EvidenceInput,
    FactBuilderServiceInterface,
    FactInput,
    FactResult,
)


class TestFactInput:
    """Tests for FactInput dataclass."""

    def test_create_fact_input(self) -> None:
        """Test creating a FactInput with required fields."""
        fact_input = FactInput(
            patient_id="P001",
            domain=Domain.CONDITION,
            omop_concept_id=255848,
            concept_name="Pneumonia",
        )
        assert fact_input.patient_id == "P001"
        assert fact_input.domain == Domain.CONDITION
        assert fact_input.omop_concept_id == 255848
        assert fact_input.concept_name == "Pneumonia"
        assert fact_input.assertion == Assertion.PRESENT
        assert fact_input.temporality == Temporality.CURRENT
        assert fact_input.experiencer == Experiencer.PATIENT
        assert fact_input.confidence == 1.0

    def test_fact_input_with_all_fields(self) -> None:
        """Test creating a FactInput with all fields."""
        fact_input = FactInput(
            patient_id="P001",
            domain=Domain.MEASUREMENT,
            omop_concept_id=3000000,
            concept_name="Blood Pressure",
            assertion=Assertion.PRESENT,
            temporality=Temporality.CURRENT,
            experiencer=Experiencer.PATIENT,
            confidence=0.95,
            value="120/80",
            unit="mmHg",
        )
        assert fact_input.value == "120/80"
        assert fact_input.unit == "mmHg"

    def test_is_negated_property_true(self) -> None:
        """Test is_negated property when assertion is ABSENT."""
        fact_input = FactInput(
            patient_id="P001",
            domain=Domain.CONDITION,
            omop_concept_id=255848,
            concept_name="Pneumonia",
            assertion=Assertion.ABSENT,
        )
        assert fact_input.is_negated is True

    def test_is_negated_property_false(self) -> None:
        """Test is_negated property when assertion is PRESENT."""
        fact_input = FactInput(
            patient_id="P001",
            domain=Domain.CONDITION,
            omop_concept_id=255848,
            concept_name="Pneumonia",
            assertion=Assertion.PRESENT,
        )
        assert fact_input.is_negated is False

    def test_is_uncertain_property_true(self) -> None:
        """Test is_uncertain property when assertion is POSSIBLE."""
        fact_input = FactInput(
            patient_id="P001",
            domain=Domain.CONDITION,
            omop_concept_id=255848,
            concept_name="Pneumonia",
            assertion=Assertion.POSSIBLE,
        )
        assert fact_input.is_uncertain is True

    def test_is_uncertain_property_false(self) -> None:
        """Test is_uncertain property when assertion is PRESENT."""
        fact_input = FactInput(
            patient_id="P001",
            domain=Domain.CONDITION,
            omop_concept_id=255848,
            concept_name="Pneumonia",
            assertion=Assertion.PRESENT,
        )
        assert fact_input.is_uncertain is False


class TestEvidenceInput:
    """Tests for EvidenceInput dataclass."""

    def test_create_evidence_input(self) -> None:
        """Test creating an EvidenceInput with required fields."""
        evidence = EvidenceInput(
            evidence_type=EvidenceType.MENTION,
            source_id=uuid4(),
            source_table="mentions",
        )
        assert evidence.evidence_type == EvidenceType.MENTION
        assert evidence.source_table == "mentions"
        assert evidence.weight == 1.0

    def test_evidence_input_with_weight(self) -> None:
        """Test creating an EvidenceInput with custom weight."""
        evidence = EvidenceInput(
            evidence_type=EvidenceType.STRUCTURED,
            source_id=uuid4(),
            source_table="structured_resources",
            weight=0.8,
        )
        assert evidence.weight == 0.8

    def test_evidence_input_with_notes(self) -> None:
        """Test creating an EvidenceInput with notes."""
        evidence = EvidenceInput(
            evidence_type=EvidenceType.INFERRED,
            source_id=uuid4(),
            source_table="clinical_facts",
            notes="Inferred from related condition",
        )
        assert evidence.notes == "Inferred from related condition"


class TestFactResult:
    """Tests for FactResult dataclass."""

    def test_create_fact_result(self) -> None:
        """Test creating a FactResult."""
        fact_id = uuid4()
        result = FactResult(fact_id=fact_id)
        assert result.fact_id == fact_id
        assert result.evidence_ids == []
        assert result.is_new is True

    def test_fact_result_with_evidence_ids(self) -> None:
        """Test creating a FactResult with evidence IDs."""
        fact_id = uuid4()
        evidence_ids = [uuid4(), uuid4()]
        result = FactResult(fact_id=fact_id, evidence_ids=evidence_ids)
        assert len(result.evidence_ids) == 2

    def test_fact_result_not_new(self) -> None:
        """Test creating a FactResult for merged fact."""
        fact_id = uuid4()
        result = FactResult(fact_id=fact_id, is_new=False)
        assert result.is_new is False


class TestFactBuilderServiceInterface:
    """Tests for FactBuilderServiceInterface abstract class."""

    def test_interface_is_abstract(self) -> None:
        """Test that FactBuilderServiceInterface cannot be instantiated."""
        with pytest.raises(TypeError):
            FactBuilderServiceInterface()  # type: ignore[abstract]

    def test_concrete_implementation_required(self) -> None:
        """Test that a concrete implementation must implement all methods."""

        class IncompleteService(FactBuilderServiceInterface):
            pass

        with pytest.raises(TypeError):
            IncompleteService()  # type: ignore[abstract]


class TestBaseFactBuilderService:
    """Tests for BaseFactBuilderService base class."""

    def test_calculate_dedup_key(self) -> None:
        """Test deduplication key calculation."""
        service = BaseFactBuilderService()
        key = service.calculate_dedup_key(
            patient_id="P001",
            omop_concept_id=255848,
            assertion=Assertion.PRESENT,
            temporality=Temporality.CURRENT,
            experiencer=Experiencer.PATIENT,
        )
        assert key == "P001:255848:present:current:patient"

    def test_calculate_dedup_key_negated(self) -> None:
        """Test deduplication key for negated finding."""
        service = BaseFactBuilderService()
        key = service.calculate_dedup_key(
            patient_id="P001",
            omop_concept_id=255848,
            assertion=Assertion.ABSENT,
            temporality=Temporality.CURRENT,
            experiencer=Experiencer.PATIENT,
        )
        assert key == "P001:255848:absent:current:patient"

    def test_calculate_dedup_key_family(self) -> None:
        """Test deduplication key for family history."""
        service = BaseFactBuilderService()
        key = service.calculate_dedup_key(
            patient_id="P001",
            omop_concept_id=255848,
            assertion=Assertion.PRESENT,
            temporality=Temporality.PAST,
            experiencer=Experiencer.FAMILY,
        )
        assert key == "P001:255848:present:past:family"

    def test_merge_confidence_same(self) -> None:
        """Test merging confidence when both are same."""
        service = BaseFactBuilderService()
        result = service.merge_confidence(0.8, 0.8)
        # 1 - (0.2 * 0.2) = 1 - 0.04 = 0.96
        assert result == pytest.approx(0.96)

    def test_merge_confidence_different(self) -> None:
        """Test merging different confidence values."""
        service = BaseFactBuilderService()
        result = service.merge_confidence(0.9, 0.5)
        # 1 - (0.1 * 0.5) = 1 - 0.05 = 0.95
        assert result == pytest.approx(0.95)

    def test_merge_confidence_one_perfect(self) -> None:
        """Test merging when one confidence is 1.0."""
        service = BaseFactBuilderService()
        result = service.merge_confidence(1.0, 0.5)
        # 1 - (0.0 * 0.5) = 1.0
        assert result == 1.0

    def test_should_preserve_negation_absent(self) -> None:
        """Test that ABSENT findings should be preserved."""
        service = BaseFactBuilderService()
        assert service.should_preserve_negation(Assertion.ABSENT) is True

    def test_should_preserve_negation_present(self) -> None:
        """Test that PRESENT findings should not be marked for preservation."""
        service = BaseFactBuilderService()
        assert service.should_preserve_negation(Assertion.PRESENT) is False

    def test_should_preserve_negation_possible(self) -> None:
        """Test that POSSIBLE findings should not be marked for preservation."""
        service = BaseFactBuilderService()
        assert service.should_preserve_negation(Assertion.POSSIBLE) is False

    def test_create_fact_raises_not_implemented(self) -> None:
        """Test that base create_fact raises NotImplementedError."""
        service = BaseFactBuilderService()
        fact_input = FactInput(
            patient_id="P001",
            domain=Domain.CONDITION,
            omop_concept_id=255848,
            concept_name="Pneumonia",
        )
        with pytest.raises(NotImplementedError):
            service.create_fact(fact_input)

    def test_get_fact_by_id_returns_none(self) -> None:
        """Test that base get_fact_by_id returns None."""
        service = BaseFactBuilderService()
        result = service.get_fact_by_id(uuid4())
        assert result is None

    def test_get_facts_for_patient_returns_empty(self) -> None:
        """Test that base get_facts_for_patient returns empty list."""
        service = BaseFactBuilderService()
        result = service.get_facts_for_patient("P001")
        assert result == []


class TestFactBuilderExports:
    """Tests for fact builder module exports."""

    def test_fact_builder_interface_exported(self) -> None:
        """Test that FactBuilderServiceInterface is exported from services."""
        from app.services import FactBuilderServiceInterface

        assert FactBuilderServiceInterface is not None

    def test_base_fact_builder_exported(self) -> None:
        """Test that BaseFactBuilderService is exported from services."""
        from app.services import BaseFactBuilderService

        assert BaseFactBuilderService is not None

    def test_fact_input_exported(self) -> None:
        """Test that FactInput is exported from services."""
        from app.services import FactInput

        assert FactInput is not None

    def test_evidence_input_exported(self) -> None:
        """Test that EvidenceInput is exported from services."""
        from app.services import EvidenceInput

        assert EvidenceInput is not None

    def test_fact_result_exported(self) -> None:
        """Test that FactResult is exported from services."""
        from app.services import FactResult

        assert FactResult is not None
