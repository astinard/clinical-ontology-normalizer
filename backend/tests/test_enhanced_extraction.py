"""Tests for Enhanced Extraction Service.

Tests the entity extraction, normalization, deduplication,
caching, and retry functionality.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.enhanced_extraction import (
    EnhancedExtractionService,
    EntityNormalizer,
    EntityDeduplicator,
    ExtractionCache,
    ExtractedEntity,
    get_enhanced_extraction_service,
    reset_enhanced_extraction_service,
    with_retry,
)


class TestEntityNormalizer:
    """Tests for entity normalization."""

    def test_normalize_condition_abbreviation(self):
        """Test normalizing abbreviated conditions."""
        assert EntityNormalizer.normalize_condition("htn") == "hypertension"
        assert EntityNormalizer.normalize_condition("dm2") == "type 2 diabetes mellitus"
        assert EntityNormalizer.normalize_condition("afib") == "atrial fibrillation"
        assert EntityNormalizer.normalize_condition("ckd") == "chronic kidney disease"

    def test_normalize_condition_full_name(self):
        """Test that full names are preserved."""
        assert EntityNormalizer.normalize_condition("hypertension") == "hypertension"
        assert EntityNormalizer.normalize_condition("diabetes mellitus") == "type 2 diabetes mellitus"

    def test_normalize_condition_case_insensitive(self):
        """Test case insensitivity."""
        assert EntityNormalizer.normalize_condition("HTN") == "hypertension"
        assert EntityNormalizer.normalize_condition("Afib") == "atrial fibrillation"

    def test_normalize_drug_brand_to_generic(self):
        """Test normalizing brand names to generic."""
        assert EntityNormalizer.normalize_drug("lantus") == "insulin glargine"
        assert EntityNormalizer.normalize_drug("lasix") == "furosemide"
        assert EntityNormalizer.normalize_drug("lipitor") == "atorvastatin"

    def test_normalize_drug_generic_preserved(self):
        """Test that generic names are preserved."""
        assert EntityNormalizer.normalize_drug("metformin") == "metformin"
        assert EntityNormalizer.normalize_drug("lisinopril") == "lisinopril"


class TestEntityDeduplicator:
    """Tests for entity deduplication."""

    def test_deduplicate_identical_entities(self):
        """Test removing duplicate entities."""
        entities = [
            ExtractedEntity(text="htn", normalized_text="hypertension", entity_type="condition", confidence=0.8),
            ExtractedEntity(text="HTN", normalized_text="hypertension", entity_type="condition", confidence=0.9),
            ExtractedEntity(text="hypertension", normalized_text="hypertension", entity_type="condition", confidence=0.7),
        ]

        result = EntityDeduplicator.deduplicate(entities)

        assert len(result) == 1
        assert result[0].normalized_text == "hypertension"
        assert result[0].confidence == 0.9  # Highest confidence kept

    def test_deduplicate_different_types(self):
        """Test that different entity types are not deduplicated."""
        entities = [
            ExtractedEntity(text="metformin", normalized_text="metformin", entity_type="drug", confidence=0.9),
            ExtractedEntity(text="metformin", normalized_text="metformin", entity_type="condition", confidence=0.8),
        ]

        result = EntityDeduplicator.deduplicate(entities)

        assert len(result) == 2

    def test_deduplicate_preserves_attributes(self):
        """Test that attributes from duplicates are merged."""
        entities = [
            ExtractedEntity(text="glucose", normalized_text="glucose", entity_type="measurement", confidence=0.9, value="120"),
            ExtractedEntity(text="glucose", normalized_text="glucose", entity_type="measurement", confidence=0.8, unit="mg/dL"),
        ]

        result = EntityDeduplicator.deduplicate(entities)

        assert len(result) == 1
        assert result[0].value == "120"
        assert result[0].unit == "mg/dL"


class TestExtractionCache:
    """Tests for extraction caching."""

    def test_cache_miss(self):
        """Test cache miss returns None."""
        cache = ExtractionCache(max_size=100)
        result = cache.get("some text")
        assert result is None

    def test_cache_hit(self):
        """Test cache hit returns stored result."""
        from app.services.enhanced_extraction import ExtractionResult

        cache = ExtractionCache(max_size=100)
        result = ExtractionResult(document_id="test", entities=[], processing_time_ms=10.0)

        cache.put("some text", result)
        cached = cache.get("some text")

        assert cached is not None
        assert cached.document_id == "test"

    def test_cache_eviction(self):
        """Test LRU eviction when cache is full."""
        from app.services.enhanced_extraction import ExtractionResult

        cache = ExtractionCache(max_size=2)

        cache.put("text1", ExtractionResult(document_id="1", entities=[], processing_time_ms=1.0))
        cache.put("text2", ExtractionResult(document_id="2", entities=[], processing_time_ms=2.0))
        cache.put("text3", ExtractionResult(document_id="3", entities=[], processing_time_ms=3.0))

        # First entry should be evicted
        assert cache.get("text1") is None
        assert cache.get("text2") is not None
        assert cache.get("text3") is not None

    def test_cache_stats(self):
        """Test cache statistics tracking."""
        from app.services.enhanced_extraction import ExtractionResult

        cache = ExtractionCache(max_size=100)
        result = ExtractionResult(document_id="test", entities=[], processing_time_ms=10.0)

        cache.put("text", result)
        cache.get("text")  # Hit
        cache.get("other")  # Miss

        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.5


class TestEnhancedExtractionService:
    """Tests for the extraction service."""

    def test_extract_conditions(self):
        """Test condition extraction."""
        service = EnhancedExtractionService(min_confidence=0.0, enable_cache=False)

        result = service.extract("test", "Patient has hypertension and type 2 diabetes mellitus.")

        conditions = [e for e in result.entities if e.entity_type == "condition"]
        normalized = {e.normalized_text for e in conditions}

        assert "hypertension" in normalized
        assert "type 2 diabetes mellitus" in normalized

    def test_extract_drugs(self):
        """Test drug extraction."""
        service = EnhancedExtractionService(min_confidence=0.0, enable_cache=False)

        result = service.extract("test", "Patient takes metformin 1000mg and lisinopril 10mg daily.")

        drugs = [e for e in result.entities if e.entity_type == "drug"]
        normalized = {e.normalized_text for e in drugs}

        assert "metformin" in normalized
        assert "lisinopril" in normalized

    def test_extract_measurements(self):
        """Test measurement extraction."""
        service = EnhancedExtractionService(min_confidence=0.0, enable_cache=False)

        result = service.extract("test", "BP: 140/90, HbA1c: 7.2%")

        measurements = [e for e in result.entities if e.entity_type == "measurement"]

        bp = next((e for e in measurements if e.normalized_text == "blood pressure"), None)
        hba1c = next((e for e in measurements if e.normalized_text == "hba1c"), None)

        assert bp is not None
        assert bp.value == "140/90"

        assert hba1c is not None
        assert hba1c.value == "7.2"

    def test_confidence_filtering(self):
        """Test that low confidence entities are filtered."""
        service = EnhancedExtractionService(min_confidence=0.8, enable_cache=False)

        # This text should have some lower confidence matches
        result = service.extract("test", "Patient has headache and nausea")

        # All entities should meet confidence threshold
        for entity in result.entities:
            assert entity.confidence >= 0.8 or result.low_confidence_filtered > 0

    def test_deduplication_in_extraction(self):
        """Test that extraction deduplicates entities."""
        service = EnhancedExtractionService(min_confidence=0.0, enable_cache=False)

        # Text with repeated mentions
        result = service.extract("test", "HTN. Hypertension. HTN controlled. Hypertension stable.")

        conditions = [e for e in result.entities if e.entity_type == "condition"]
        htn_count = sum(1 for e in conditions if "hypertension" in e.normalized_text)

        assert htn_count == 1  # Should be deduplicated

    def test_caching_enabled(self):
        """Test that caching improves performance."""
        service = EnhancedExtractionService(enable_cache=True, cache_size=100)

        text = "Patient has diabetes and hypertension."

        # First extraction
        result1 = service.extract("test1", text)
        time1 = result1.processing_time_ms

        # Second extraction (should be cached)
        result2 = service.extract("test2", text)
        time2 = result2.processing_time_ms

        # Cached result should be much faster (essentially 0)
        assert time2 < time1 or time2 < 1.0

    def test_singleton_pattern(self):
        """Test singleton pattern works correctly."""
        reset_enhanced_extraction_service()

        service1 = get_enhanced_extraction_service()
        service2 = get_enhanced_extraction_service()

        assert service1 is service2


class TestRetryLogic:
    """Tests for retry functionality."""

    def test_retry_succeeds_on_first_try(self):
        """Test function that succeeds immediately."""
        call_count = 0

        def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"

        retry_func = with_retry(successful_func, max_retries=3)
        result = retry_func()

        assert result == "success"
        assert call_count == 1

    def test_retry_succeeds_after_failures(self):
        """Test function that succeeds after some failures."""
        call_count = 0

        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"

        retry_func = with_retry(flaky_func, max_retries=3, initial_delay=0.01)
        result = retry_func()

        assert result == "success"
        assert call_count == 3

    def test_retry_exhausted(self):
        """Test function that always fails."""
        def failing_func():
            raise ValueError("Permanent failure")

        retry_func = with_retry(failing_func, max_retries=2, initial_delay=0.01)

        with pytest.raises(ValueError, match="Permanent failure"):
            retry_func()


class TestComplexClinicalNote:
    """Integration tests with realistic clinical notes."""

    def test_diabetes_htn_note(self):
        """Test extraction from a diabetes/HTN progress note."""
        service = EnhancedExtractionService(min_confidence=0.0, enable_cache=False)

        note = """
        PROGRESS NOTE
        Patient: John Smith
        62-year-old male with Type 2 Diabetes Mellitus and Essential Hypertension.

        MEDICATIONS:
        - Metformin 1000mg twice daily
        - Lisinopril 20mg daily
        - Atorvastatin 40mg daily

        LABS:
        HbA1c: 7.4%
        BP: 142/88 mmHg
        Creatinine: 1.1 mg/dL

        ASSESSMENT:
        1. Type 2 Diabetes - suboptimally controlled
        2. Hypertension - not at goal
        3. Hyperlipidemia - controlled
        """

        result = service.extract("test", note)

        # Check conditions
        conditions = {e.normalized_text for e in result.entities if e.entity_type == "condition"}
        assert "type 2 diabetes mellitus" in conditions or "diabetes mellitus" in conditions
        assert "hypertension" in conditions
        assert "hyperlipidemia" in conditions

        # Check drugs
        drugs = {e.normalized_text for e in result.entities if e.entity_type == "drug"}
        assert "metformin" in drugs
        assert "lisinopril" in drugs
        assert "atorvastatin" in drugs

        # Check measurements
        measurements = {e.normalized_text for e in result.entities if e.entity_type == "measurement"}
        assert "hba1c" in measurements
        assert "blood pressure" in measurements
        assert "creatinine" in measurements


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
