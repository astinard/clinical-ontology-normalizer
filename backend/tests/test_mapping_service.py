"""Tests for mapping service interface."""

import pytest

from app.schemas.base import Domain
from app.services import (
    BaseMappingService,
    ConceptCandidate,
    MappingMethod,
    MappingServiceInterface,
)


class TestConceptCandidate:
    """Tests for ConceptCandidate dataclass."""

    def test_create_candidate(self) -> None:
        """Test creating a ConceptCandidate with required fields."""
        candidate = ConceptCandidate(
            omop_concept_id=255848,
            concept_name="Pneumonia",
            concept_code="233604007",
            vocabulary_id="SNOMED",
            domain_id=Domain.CONDITION,
            score=0.95,
            method=MappingMethod.EXACT,
        )
        assert candidate.omop_concept_id == 255848
        assert candidate.concept_name == "Pneumonia"
        assert candidate.domain_id == Domain.CONDITION
        assert candidate.score == 0.95
        assert candidate.method == MappingMethod.EXACT
        assert candidate.rank == 1  # Default

    def test_custom_rank(self) -> None:
        """Test creating a candidate with custom rank."""
        candidate = ConceptCandidate(
            omop_concept_id=255848,
            concept_name="Pneumonia",
            concept_code="233604007",
            vocabulary_id="SNOMED",
            domain_id=Domain.CONDITION,
            score=0.85,
            method=MappingMethod.FUZZY,
            rank=2,
        )
        assert candidate.rank == 2

    def test_is_high_confidence_true(self) -> None:
        """Test is_high_confidence property when score >= 0.9."""
        candidate = ConceptCandidate(
            omop_concept_id=255848,
            concept_name="Pneumonia",
            concept_code="233604007",
            vocabulary_id="SNOMED",
            domain_id=Domain.CONDITION,
            score=0.95,
            method=MappingMethod.EXACT,
        )
        assert candidate.is_high_confidence is True

    def test_is_high_confidence_false(self) -> None:
        """Test is_high_confidence property when score < 0.9."""
        candidate = ConceptCandidate(
            omop_concept_id=255848,
            concept_name="Pneumonia",
            concept_code="233604007",
            vocabulary_id="SNOMED",
            domain_id=Domain.CONDITION,
            score=0.85,
            method=MappingMethod.FUZZY,
        )
        assert candidate.is_high_confidence is False

    def test_is_exact_match_true(self) -> None:
        """Test is_exact_match property when method is EXACT."""
        candidate = ConceptCandidate(
            omop_concept_id=255848,
            concept_name="Pneumonia",
            concept_code="233604007",
            vocabulary_id="SNOMED",
            domain_id=Domain.CONDITION,
            score=0.95,
            method=MappingMethod.EXACT,
        )
        assert candidate.is_exact_match is True

    def test_is_exact_match_false(self) -> None:
        """Test is_exact_match property when method is not EXACT."""
        candidate = ConceptCandidate(
            omop_concept_id=255848,
            concept_name="Pneumonia",
            concept_code="233604007",
            vocabulary_id="SNOMED",
            domain_id=Domain.CONDITION,
            score=0.85,
            method=MappingMethod.FUZZY,
        )
        assert candidate.is_exact_match is False


class TestMappingMethod:
    """Tests for MappingMethod enum."""

    def test_exact_value(self) -> None:
        """Test EXACT enum value."""
        assert MappingMethod.EXACT.value == "exact"

    def test_fuzzy_value(self) -> None:
        """Test FUZZY enum value."""
        assert MappingMethod.FUZZY.value == "fuzzy"

    def test_ml_value(self) -> None:
        """Test ML enum value."""
        assert MappingMethod.ML.value == "ml"


class TestMappingServiceInterface:
    """Tests for MappingServiceInterface abstract class."""

    def test_interface_is_abstract(self) -> None:
        """Test that MappingServiceInterface cannot be instantiated directly."""
        with pytest.raises(TypeError):
            MappingServiceInterface()  # type: ignore[abstract]

    def test_concrete_implementation_required(self) -> None:
        """Test that a concrete implementation must implement all methods."""

        class IncompleteService(MappingServiceInterface):
            pass

        with pytest.raises(TypeError):
            IncompleteService()  # type: ignore[abstract]


class TestBaseMappingService:
    """Tests for BaseMappingService base class."""

    def test_can_instantiate(self) -> None:
        """Test that BaseMappingService can be instantiated."""
        service = BaseMappingService()
        assert service is not None

    def test_map_mention_returns_empty_list(self) -> None:
        """Test that default map_mention returns empty list."""
        service = BaseMappingService()
        result = service.map_mention("pneumonia")
        assert result == []

    def test_get_best_match_returns_none(self) -> None:
        """Test that default get_best_match returns None."""
        service = BaseMappingService()
        result = service.get_best_match("pneumonia")
        assert result is None

    def test_get_concept_by_id_returns_none(self) -> None:
        """Test that default get_concept_by_id returns None."""
        service = BaseMappingService()
        result = service.get_concept_by_id(255848)
        assert result is None

    def test_normalize_text_lowercase(self) -> None:
        """Test normalize_text converts to lowercase."""
        service = BaseMappingService()
        result = service.normalize_text("Pneumonia")
        assert result == "pneumonia"

    def test_normalize_text_removes_extra_whitespace(self) -> None:
        """Test normalize_text removes extra whitespace."""
        service = BaseMappingService()
        result = service.normalize_text("community   acquired   pneumonia")
        assert result == "community acquired pneumonia"

    def test_normalize_text_strips_punctuation(self) -> None:
        """Test normalize_text strips leading/trailing punctuation."""
        service = BaseMappingService()
        result = service.normalize_text("(pneumonia)")
        assert result == "pneumonia"

    def test_calculate_similarity_exact_match(self) -> None:
        """Test calculate_similarity for identical texts."""
        service = BaseMappingService()
        result = service.calculate_similarity("pneumonia", "pneumonia")
        assert result == 1.0

    def test_calculate_similarity_no_match(self) -> None:
        """Test calculate_similarity for completely different texts."""
        service = BaseMappingService()
        result = service.calculate_similarity("pneumonia", "aspirin")
        assert result == 0.0

    def test_calculate_similarity_partial_match(self) -> None:
        """Test calculate_similarity for partial overlap."""
        service = BaseMappingService()
        result = service.calculate_similarity(
            "community acquired pneumonia",
            "hospital acquired pneumonia",
        )
        # "acquired" and "pneumonia" overlap, so > 0 but < 1
        assert 0.0 < result < 1.0

    def test_calculate_similarity_empty_text(self) -> None:
        """Test calculate_similarity with empty text."""
        service = BaseMappingService()
        result = service.calculate_similarity("", "pneumonia")
        assert result == 0.0


class TestMappingServiceExports:
    """Tests for mapping service module exports."""

    def test_mapping_interface_exported(self) -> None:
        """Test that MappingServiceInterface is exported from services."""
        from app.services import MappingServiceInterface

        assert MappingServiceInterface is not None

    def test_base_mapping_service_exported(self) -> None:
        """Test that BaseMappingService is exported from services."""
        from app.services import BaseMappingService

        assert BaseMappingService is not None

    def test_concept_candidate_exported(self) -> None:
        """Test that ConceptCandidate is exported from services."""
        from app.services import ConceptCandidate

        assert ConceptCandidate is not None

    def test_mapping_method_exported(self) -> None:
        """Test that MappingMethod is exported from services."""
        from app.services import MappingMethod

        assert MappingMethod is not None
