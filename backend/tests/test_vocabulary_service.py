"""Tests for VocabularyService."""

import json
import tempfile
from pathlib import Path

import pytest

from app.schemas.base import Domain
from app.services.vocabulary import OMOPConcept, VocabularyService


class TestOMOPConcept:
    """Test OMOPConcept dataclass."""

    def test_create_concept(self) -> None:
        """Test creating an OMOP concept."""
        concept = OMOPConcept(
            concept_id=255848,
            concept_name="Pneumonia",
            concept_code="233604007",
            vocabulary_id="SNOMED",
            domain_id="Condition",
            synonyms=["pneumonia", "lung infection"],
        )
        assert concept.concept_id == 255848
        assert concept.concept_name == "Pneumonia"
        assert concept.vocabulary_id == "SNOMED"
        assert len(concept.synonyms) == 2

    def test_concept_domain_property(self) -> None:
        """Test domain property converts string to enum."""
        concept = OMOPConcept(
            concept_id=1,
            concept_name="Test",
            concept_code="123",
            vocabulary_id="SNOMED",
            domain_id="Condition",
        )
        assert concept.domain == Domain.CONDITION

    def test_concept_domain_drug(self) -> None:
        """Test domain property for drug."""
        concept = OMOPConcept(
            concept_id=1,
            concept_name="Test Drug",
            concept_code="123",
            vocabulary_id="RxNorm",
            domain_id="Drug",
        )
        assert concept.domain == Domain.DRUG

    def test_concept_domain_measurement(self) -> None:
        """Test domain property for measurement."""
        concept = OMOPConcept(
            concept_id=1,
            concept_name="Test Measurement",
            concept_code="123",
            vocabulary_id="LOINC",
            domain_id="Measurement",
        )
        assert concept.domain == Domain.MEASUREMENT

    def test_concept_domain_procedure(self) -> None:
        """Test domain property for procedure."""
        concept = OMOPConcept(
            concept_id=1,
            concept_name="Test Procedure",
            concept_code="123",
            vocabulary_id="SNOMED",
            domain_id="Procedure",
        )
        assert concept.domain == Domain.PROCEDURE


class TestVocabularyServiceLoading:
    """Test VocabularyService loading functionality."""

    def test_load_from_fixture(self) -> None:
        """Test loading concepts from the fixture file."""
        vocab = VocabularyService()
        vocab.load()
        assert vocab.concept_count > 0

    def test_load_idempotent(self) -> None:
        """Test that multiple load() calls are idempotent."""
        vocab = VocabularyService()
        vocab.load()
        count1 = vocab.concept_count
        vocab.load()
        count2 = vocab.concept_count
        assert count1 == count2

    def test_concepts_property_auto_loads(self) -> None:
        """Test that accessing concepts auto-loads the vocabulary."""
        vocab = VocabularyService()
        concepts = vocab.concepts
        assert len(concepts) > 0

    def test_load_from_custom_path(self) -> None:
        """Test loading from a custom fixture path includes custom concepts.

        Note: VocabularyService now always loads clinical_abbreviations.json
        in addition to the custom fixture path. This test verifies that
        custom concepts ARE included alongside clinical abbreviations.
        """
        # Create a temporary fixture file with a unique test concept
        fixture_data = {
            "concepts": [
                {
                    "concept_id": 999999,  # Unique ID unlikely to conflict
                    "concept_name": "UniqueTestConcept12345",
                    "concept_code": "TEST001",
                    "vocabulary_id": "TEST",
                    "domain_id": "Condition",
                    "synonyms": ["uniquetestsynonym12345"],
                }
            ]
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(fixture_data, f)
            temp_path = f.name

        try:
            vocab = VocabularyService(fixture_path=temp_path)
            vocab.load()
            # Should have clinical abbreviations PLUS the custom concept
            assert vocab.concept_count > 1
            # Verify the custom concept is included
            custom_concept = vocab.get_by_id(999999)
            assert custom_concept is not None
            assert custom_concept.concept_name == "UniqueTestConcept12345"
        finally:
            Path(temp_path).unlink()

    def test_load_missing_file_loads_abbreviations_only(self) -> None:
        """Test that a missing fixture file loads clinical abbreviations only.

        VocabularyService gracefully handles missing OMOP vocabulary fixture
        by loading only the clinical abbreviations.
        """
        vocab = VocabularyService(fixture_path="/nonexistent/path.json")
        vocab.load()
        # Should have loaded clinical abbreviations (>300 terms)
        assert vocab.concept_count >= 300
        # Verify clinical abbreviations are present
        results = vocab.search("hfref")
        assert len(results) > 0


class TestVocabularyServiceLookup:
    """Test VocabularyService lookup functionality."""

    @pytest.fixture
    def vocab(self) -> VocabularyService:
        """Create and load a vocabulary service."""
        v = VocabularyService()
        v.load()
        return v

    def test_get_by_id_existing(self, vocab: VocabularyService) -> None:
        """Test getting a concept by ID that exists."""
        # Pneumonia concept ID from fixture
        concept = vocab.get_by_id(255848)
        assert concept is not None
        assert concept.concept_name == "Pneumonia"

    def test_get_by_id_nonexistent(self, vocab: VocabularyService) -> None:
        """Test getting a concept by ID that doesn't exist."""
        concept = vocab.get_by_id(999999999)
        assert concept is None

    def test_search_exact_synonym(self, vocab: VocabularyService) -> None:
        """Test search finds exact synonym matches."""
        results = vocab.search("pneumonia")
        assert len(results) > 0
        # Pneumonia should be first result
        assert any(c.concept_name == "Pneumonia" for c in results)

    def test_search_case_insensitive(self, vocab: VocabularyService) -> None:
        """Test search is case insensitive."""
        results_lower = vocab.search("pneumonia")
        results_upper = vocab.search("PNEUMONIA")
        results_mixed = vocab.search("Pneumonia")
        assert len(results_lower) == len(results_upper) == len(results_mixed)

    def test_search_partial_match(self, vocab: VocabularyService) -> None:
        """Test search finds partial matches in synonyms.

        Note: Search returns concepts where synonyms contain the search term,
        not necessarily the concept_name. For example, searching "heart"
        matches HFrEF because its synonym is "heart failure with reduced ef".
        """
        results = vocab.search("heart")
        assert len(results) > 0
        # Should find concepts with "heart" in synonyms
        assert any(
            any("heart" in syn.lower() for syn in c.synonyms)
            for c in results
        )

    def test_search_respects_limit(self, vocab: VocabularyService) -> None:
        """Test search respects the limit parameter."""
        results = vocab.search("a", limit=3)
        assert len(results) <= 3

    def test_search_no_results(self, vocab: VocabularyService) -> None:
        """Test search returns empty list for no matches."""
        results = vocab.search("xyznonexistent123")
        assert results == []


class TestVocabularyServiceDomainFiltering:
    """Test VocabularyService domain filtering."""

    @pytest.fixture
    def vocab(self) -> VocabularyService:
        """Create and load a vocabulary service."""
        v = VocabularyService()
        v.load()
        return v

    def test_search_by_domain_condition(self, vocab: VocabularyService) -> None:
        """Test searching within condition domain."""
        results = vocab.search_by_domain("diabetes", Domain.CONDITION)
        assert len(results) > 0
        for concept in results:
            assert concept.domain == Domain.CONDITION

    def test_search_by_domain_drug(self, vocab: VocabularyService) -> None:
        """Test searching within drug domain."""
        results = vocab.search_by_domain("metformin", Domain.DRUG)
        assert len(results) > 0
        for concept in results:
            assert concept.domain == Domain.DRUG

    def test_search_by_domain_measurement(self, vocab: VocabularyService) -> None:
        """Test searching within measurement domain."""
        results = vocab.search_by_domain("blood pressure", Domain.MEASUREMENT)
        assert len(results) > 0
        for concept in results:
            assert concept.domain == Domain.MEASUREMENT

    def test_search_by_domain_procedure(self, vocab: VocabularyService) -> None:
        """Test searching within procedure domain."""
        results = vocab.search_by_domain("colonoscopy", Domain.PROCEDURE)
        assert len(results) > 0
        for concept in results:
            assert concept.domain == Domain.PROCEDURE

    def test_get_concepts_by_domain_condition(self, vocab: VocabularyService) -> None:
        """Test getting all concepts in condition domain."""
        conditions = vocab.get_concepts_by_domain(Domain.CONDITION)
        assert len(conditions) > 0
        for concept in conditions:
            assert concept.domain_id == "Condition"

    def test_get_concepts_by_domain_drug(self, vocab: VocabularyService) -> None:
        """Test getting all concepts in drug domain."""
        drugs = vocab.get_concepts_by_domain(Domain.DRUG)
        assert len(drugs) > 0
        for concept in drugs:
            assert concept.domain_id == "Drug"


class TestVocabularyFixtureContent:
    """Test that the vocabulary fixture has expected content."""

    @pytest.fixture
    def vocab(self) -> VocabularyService:
        """Create and load a vocabulary service."""
        v = VocabularyService()
        v.load()
        return v

    def test_fixture_has_conditions(self, vocab: VocabularyService) -> None:
        """Test fixture contains condition concepts."""
        conditions = vocab.get_concepts_by_domain(Domain.CONDITION)
        assert len(conditions) >= 5

    def test_fixture_has_drugs(self, vocab: VocabularyService) -> None:
        """Test fixture contains drug concepts."""
        drugs = vocab.get_concepts_by_domain(Domain.DRUG)
        assert len(drugs) >= 3

    def test_fixture_has_measurements(self, vocab: VocabularyService) -> None:
        """Test fixture contains measurement concepts."""
        measurements = vocab.get_concepts_by_domain(Domain.MEASUREMENT)
        assert len(measurements) >= 3

    def test_fixture_has_procedures(self, vocab: VocabularyService) -> None:
        """Test fixture contains procedure concepts."""
        procedures = vocab.get_concepts_by_domain(Domain.PROCEDURE)
        assert len(procedures) >= 2

    def test_fixture_covers_synthetic_notes(self, vocab: VocabularyService) -> None:
        """Test fixture covers concepts needed for synthetic notes."""
        # Key conditions from synthetic notes
        assert vocab.search("pneumonia")
        assert vocab.search("heart failure")
        assert vocab.search("diabetes")
        assert vocab.search("hypertension")
        # Key drugs
        assert vocab.search("metformin")
        assert vocab.search("lisinopril")
        # Key measurements
        assert vocab.search("hemoglobin a1c") or vocab.search("HbA1c")
        assert vocab.search("blood pressure")
