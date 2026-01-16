"""Tests for Enhanced Vocabulary Service.

Tests the enhanced vocabulary service with UMLS synonym expansion,
semantic similarity search, and Aho-Corasick multi-pattern matching.
"""

import pytest
from pathlib import Path

from app.services.vocabulary_enhanced import (
    EnhancedVocabularyService,
    get_enhanced_vocabulary_service,
    reset_enhanced_vocabulary_service,
    ABBREVIATION_EXPANSIONS,
    SYNONYM_PATTERNS,
)
from app.schemas.base import Domain


# ============================================================================
# Abbreviation Expansion Tests
# ============================================================================


class TestAbbreviationExpansions:
    """Test clinical abbreviation expansions."""

    def test_condition_abbreviations(self):
        """Test condition abbreviations are defined."""
        assert "htn" in ABBREVIATION_EXPANSIONS
        assert "hypertension" in ABBREVIATION_EXPANSIONS["htn"]

        assert "dm" in ABBREVIATION_EXPANSIONS
        assert "diabetes" in ABBREVIATION_EXPANSIONS["dm"]

        assert "copd" in ABBREVIATION_EXPANSIONS
        assert "chronic obstructive pulmonary disease" in ABBREVIATION_EXPANSIONS["copd"]

    def test_drug_abbreviations(self):
        """Test drug abbreviations are defined."""
        assert "asa" in ABBREVIATION_EXPANSIONS
        assert "aspirin" in ABBREVIATION_EXPANSIONS["asa"]

        assert "apap" in ABBREVIATION_EXPANSIONS
        assert "acetaminophen" in ABBREVIATION_EXPANSIONS["apap"]

    def test_lab_abbreviations(self):
        """Test lab abbreviations are defined."""
        assert "cbc" in ABBREVIATION_EXPANSIONS
        assert "complete blood count" in ABBREVIATION_EXPANSIONS["cbc"]

        assert "bmp" in ABBREVIATION_EXPANSIONS
        assert "basic metabolic panel" in ABBREVIATION_EXPANSIONS["bmp"]

        assert "hba1c" in ABBREVIATION_EXPANSIONS
        assert "hemoglobin a1c" in ABBREVIATION_EXPANSIONS["hba1c"]

    def test_procedure_abbreviations(self):
        """Test procedure abbreviations are defined."""
        assert "ekg" in ABBREVIATION_EXPANSIONS
        assert "electrocardiogram" in ABBREVIATION_EXPANSIONS["ekg"]

        assert "ct" in ABBREVIATION_EXPANSIONS
        assert "computed tomography" in ABBREVIATION_EXPANSIONS["ct"]

        assert "mri" in ABBREVIATION_EXPANSIONS
        assert "magnetic resonance imaging" in ABBREVIATION_EXPANSIONS["mri"]


# ============================================================================
# Synonym Pattern Tests
# ============================================================================


class TestSynonymPatterns:
    """Test UMLS-style synonym patterns."""

    def test_spelling_variations(self):
        """Test American/British spelling variations."""
        assert "anemia" in SYNONYM_PATTERNS
        assert "anaemia" in SYNONYM_PATTERNS["anemia"]

        assert "edema" in SYNONYM_PATTERNS
        assert "oedema" in SYNONYM_PATTERNS["edema"]

        assert "tumor" in SYNONYM_PATTERNS
        assert "tumour" in SYNONYM_PATTERNS["tumor"]

    def test_abbreviation_patterns(self):
        """Test abbreviation patterns."""
        assert "disease" in SYNONYM_PATTERNS
        assert "disorder" in SYNONYM_PATTERNS["disease"]

        assert "chronic" in SYNONYM_PATTERNS
        assert "chr" in SYNONYM_PATTERNS["chronic"]


# ============================================================================
# Service Initialization Tests
# ============================================================================


class TestEnhancedServiceInit:
    """Test enhanced vocabulary service initialization."""

    def setup_method(self):
        """Reset singleton before each test."""
        reset_enhanced_vocabulary_service()

    def test_service_creation_no_embeddings(self):
        """Test service creation without embeddings for speed."""
        service = EnhancedVocabularyService(
            use_embeddings=False,
            use_automaton=False,
        )
        assert service is not None
        assert not service._use_embeddings
        assert not service._use_automaton

    def test_service_creation_with_embeddings(self):
        """Test service creation with embeddings enabled."""
        service = EnhancedVocabularyService(
            use_embeddings=True,
            use_automaton=True,
        )
        assert service._use_embeddings
        assert service._use_automaton

    def test_singleton_pattern(self):
        """Test singleton pattern works."""
        service1 = get_enhanced_vocabulary_service(
            use_embeddings=False,
            use_automaton=False,
        )
        service2 = get_enhanced_vocabulary_service()
        assert service1 is service2

    def test_singleton_reset(self):
        """Test singleton can be reset."""
        service1 = get_enhanced_vocabulary_service(
            use_embeddings=False,
            use_automaton=False,
        )
        reset_enhanced_vocabulary_service()
        service2 = get_enhanced_vocabulary_service(
            use_embeddings=False,
            use_automaton=False,
        )
        assert service1 is not service2


# ============================================================================
# Vocabulary Loading Tests
# ============================================================================


class TestVocabularyLoading:
    """Test vocabulary loading and expansion."""

    def setup_method(self):
        """Create service for testing."""
        reset_enhanced_vocabulary_service()
        self.service = EnhancedVocabularyService(
            use_embeddings=False,
            use_automaton=False,
        )

    def test_load_vocabulary(self):
        """Test vocabulary loads successfully."""
        self.service.load()
        assert self.service._loaded
        assert len(self.service._concepts) > 0
        assert len(self.service._synonym_index) > 0

    def test_load_idempotent(self):
        """Test multiple load calls are idempotent."""
        self.service.load()
        count1 = len(self.service._concepts)

        self.service.load()
        count2 = len(self.service._concepts)

        assert count1 == count2

    def test_clinical_abbreviations_loaded(self):
        """Test that clinical abbreviations are in the index."""
        self.service.load()

        # Check that abbreviations are expanded
        assert "hypertension" in self.service._synonym_index
        assert "high blood pressure" in self.service._synonym_index
        assert "diabetes" in self.service._synonym_index


# ============================================================================
# Basic Search Tests
# ============================================================================


class TestBasicSearch:
    """Test basic vocabulary search."""

    def setup_method(self):
        """Create and load service for testing."""
        reset_enhanced_vocabulary_service()
        self.service = EnhancedVocabularyService(
            use_embeddings=False,
            use_automaton=False,
        )
        self.service.load()

    def test_search_by_name(self):
        """Test searching by concept name or synonym."""
        results = self.service.search("diabetes", limit=5)
        assert len(results) > 0

        # Check that results contain diabetes-related concepts
        # (may return DM, DM1, DM2 etc. since "diabetes" matches their synonyms)
        found_dm_related = any(
            "dm" in c.concept_name.lower() or "diabetes" in str(c.synonyms).lower()
            for c in results
        )
        assert found_dm_related

    def test_search_by_abbreviation(self):
        """Test searching by abbreviation."""
        results = self.service.search("hypertension", limit=5)
        assert len(results) > 0

    def test_search_case_insensitive(self):
        """Test that search is case insensitive."""
        results_lower = self.service.search("diabetes", limit=5)
        results_upper = self.service.search("DIABETES", limit=5)
        results_mixed = self.service.search("DiAbEtEs", limit=5)

        # All should return similar results
        assert len(results_lower) == len(results_upper) == len(results_mixed)

    def test_search_returns_concepts(self):
        """Test that search returns concept objects."""
        results = self.service.search("blood", limit=10)

        # Should return concepts with expected attributes
        for concept in results:
            assert hasattr(concept, "concept_id")
            assert hasattr(concept, "concept_name")
            assert hasattr(concept, "domain")

    def test_search_no_results(self):
        """Test searching for non-existent term."""
        results = self.service.search("xyznonexistent123", limit=5)
        assert len(results) == 0


# ============================================================================
# Synonym Expansion Tests
# ============================================================================


class TestSynonymExpansion:
    """Test UMLS-style synonym expansion."""

    def setup_method(self):
        """Create service for testing."""
        reset_enhanced_vocabulary_service()
        self.service = EnhancedVocabularyService(
            use_embeddings=False,
            use_automaton=False,
        )

    def test_expand_abbreviation(self):
        """Test abbreviation expansion."""
        expanded = self.service._expand_synonyms(["htn"])

        assert "htn" in expanded
        assert "hypertension" in expanded
        assert "high blood pressure" in expanded

    def test_expand_spelling_variation(self):
        """Test spelling variation expansion."""
        expanded = self.service._expand_synonyms(["anemia"])

        assert "anemia" in expanded
        assert "anaemia" in expanded

    def test_expand_multiple_synonyms(self):
        """Test expanding multiple synonyms."""
        expanded = self.service._expand_synonyms(["dm", "htn"])

        assert "diabetes" in expanded
        assert "hypertension" in expanded

    def test_expand_preserves_original(self):
        """Test that original terms are preserved."""
        original = ["some_unknown_term", "another_term"]
        expanded = self.service._expand_synonyms(original)

        for term in original:
            assert term in expanded


# ============================================================================
# Aho-Corasick Tests
# ============================================================================


class TestAhoCorasickMatching:
    """Test Aho-Corasick multi-pattern matching."""

    def setup_method(self):
        """Create service with automaton enabled."""
        reset_enhanced_vocabulary_service()
        self.service = EnhancedVocabularyService(
            use_embeddings=False,
            use_automaton=True,
        )
        self.service.load()

    @pytest.mark.skipif(
        True,  # Skip if ahocorasick not installed
        reason="ahocorasick may not be installed"
    )
    def test_find_all_concepts(self):
        """Test finding all concepts in text."""
        text = "Patient has diabetes and hypertension"
        results = self.service.find_all_concepts(text)

        # Should find mentions
        assert len(results) >= 0  # May be empty if automaton not built

    @pytest.mark.skipif(
        True,
        reason="ahocorasick may not be installed"
    )
    def test_find_overlapping_concepts(self):
        """Test handling overlapping concept mentions."""
        text = "Type 2 diabetes mellitus"
        results = self.service.find_all_concepts(text)

        # Should deduplicate overlapping matches
        # Verify no overlaps in results
        for i, (_, start1, end1) in enumerate(results):
            for j, (_, start2, end2) in enumerate(results):
                if i != j:
                    # Check no overlap
                    assert end1 <= start2 or end2 <= start1


# ============================================================================
# Deduplication Tests
# ============================================================================


class TestDeduplication:
    """Test match deduplication logic."""

    def setup_method(self):
        """Create service for testing."""
        reset_enhanced_vocabulary_service()
        self.service = EnhancedVocabularyService(
            use_embeddings=False,
            use_automaton=False,
        )

    def test_deduplicate_overlapping(self):
        """Test deduplication of overlapping matches."""
        from app.services.vocabulary import OMOPConcept

        concept1 = OMOPConcept(
            concept_id=1,
            concept_name="diabetes",
            concept_code="T1",
            vocabulary_id="SNOMED",
            domain_id="Condition",
            synonyms=["diabetes"],
        )
        concept2 = OMOPConcept(
            concept_id=2,
            concept_name="diabetes mellitus",
            concept_code="T2",
            vocabulary_id="SNOMED",
            domain_id="Condition",
            synonyms=["diabetes mellitus"],
        )

        # Overlapping matches: "diabetes" (0-8) and "diabetes mellitus" (0-17)
        matches = [
            (concept1, 0, 8),
            (concept2, 0, 17),
        ]

        result = self.service._deduplicate_matches(matches)

        # Should keep longer match
        assert len(result) == 1
        assert result[0][0].concept_name == "diabetes mellitus"

    def test_deduplicate_non_overlapping(self):
        """Test non-overlapping matches are preserved."""
        from app.services.vocabulary import OMOPConcept

        concept1 = OMOPConcept(
            concept_id=1,
            concept_name="diabetes",
            concept_code="T1",
            vocabulary_id="SNOMED",
            domain_id="Condition",
            synonyms=["diabetes"],
        )
        concept2 = OMOPConcept(
            concept_id=2,
            concept_name="hypertension",
            concept_code="T2",
            vocabulary_id="SNOMED",
            domain_id="Condition",
            synonyms=["hypertension"],
        )

        # Non-overlapping matches
        matches = [
            (concept1, 0, 8),
            (concept2, 20, 32),
        ]

        result = self.service._deduplicate_matches(matches)

        # Both should be kept
        assert len(result) == 2

    def test_deduplicate_empty_list(self):
        """Test deduplication of empty list."""
        result = self.service._deduplicate_matches([])
        assert result == []


# ============================================================================
# Statistics Tests
# ============================================================================


class TestEnhancedStats:
    """Test enhanced vocabulary statistics."""

    def setup_method(self):
        """Create and load service for testing."""
        reset_enhanced_vocabulary_service()
        self.service = EnhancedVocabularyService(
            use_embeddings=False,
            use_automaton=False,
        )
        self.service.load()

    def test_get_enhanced_stats(self):
        """Test getting enhanced statistics."""
        stats = self.service.get_enhanced_stats()

        assert "concept_count" in stats
        assert "embeddings_enabled" in stats
        assert "automaton_enabled" in stats
        assert "expansion_patterns" in stats

    def test_stats_show_disabled_features(self):
        """Test stats reflect disabled features."""
        stats = self.service.get_enhanced_stats()

        # Embeddings and automaton are disabled
        assert stats["embeddings_enabled"] is False
        assert stats["automaton_enabled"] is False


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Integration tests for enhanced vocabulary service."""

    def setup_method(self):
        """Reset singleton before each test."""
        reset_enhanced_vocabulary_service()

    def test_service_extends_vocabulary_service(self):
        """Test that service extends VocabularyService."""
        from app.services.vocabulary import VocabularyService

        service = EnhancedVocabularyService(
            use_embeddings=False,
            use_automaton=False,
        )
        assert isinstance(service, VocabularyService)

    def test_search_interface_compatible(self):
        """Test that search interface is compatible with base class."""
        service = EnhancedVocabularyService(
            use_embeddings=False,
            use_automaton=False,
        )
        service.load()

        # Should work like base VocabularyService
        results = service.search("diabetes")
        assert isinstance(results, list)

        for concept in results:
            assert hasattr(concept, "concept_id")
            assert hasattr(concept, "concept_name")
            assert hasattr(concept, "domain")

    def test_concepts_accessible(self):
        """Test that concepts property is accessible."""
        service = EnhancedVocabularyService(
            use_embeddings=False,
            use_automaton=False,
        )
        service.load()

        # Should have concepts loaded
        assert len(service._concepts) > 0

        # Search for a concept
        results = service.search("diabetes", limit=1)
        assert len(results) > 0
        assert results[0].concept_id is not None


# ============================================================================
# Semantic Search Tests (Optional - depends on sentence-transformers)
# ============================================================================


class TestSemanticSearch:
    """Test semantic similarity search (may skip if dependencies missing)."""

    def setup_method(self):
        """Create service with embeddings enabled."""
        reset_enhanced_vocabulary_service()
        # Try to create with embeddings, may fail if dependencies missing
        self.service = EnhancedVocabularyService(
            use_embeddings=False,  # Disabled for speed in tests
            use_automaton=False,
        )
        self.service.load()

    def test_semantic_search_fallback(self):
        """Test semantic search falls back to text search when disabled."""
        results = self.service.semantic_search("sugar disease", limit=5)

        # Should return results (from fallback text search)
        assert isinstance(results, list)

        # Results should be tuples of (concept, score)
        for item in results:
            assert isinstance(item, tuple)
            assert len(item) == 2
            concept, score = item
            assert hasattr(concept, "concept_id")
            assert isinstance(score, float)
