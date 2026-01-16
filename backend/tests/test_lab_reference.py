"""Tests for Lab Reference Service.

Tests the lab reference range lookup and interpretation functionality.
"""

import pytest

from app.services.lab_reference import (
    LabReferenceService,
    LabCategory,
    InterpretationLevel,
    get_lab_reference_service,
    reset_lab_reference_service,
    LAB_REFERENCE_RANGES,
)


# ============================================================================
# Database Content Tests
# ============================================================================


class TestDatabaseContent:
    """Test the lab reference database content."""

    def test_database_not_empty(self):
        """Test that database has reference ranges."""
        assert len(LAB_REFERENCE_RANGES) > 0

    def test_has_chemistry_tests(self):
        """Test that database has chemistry tests."""
        chemistry = [r for r in LAB_REFERENCE_RANGES if r.category == LabCategory.CHEMISTRY]
        assert len(chemistry) > 0

    def test_has_hematology_tests(self):
        """Test that database has hematology tests."""
        hematology = [r for r in LAB_REFERENCE_RANGES if r.category == LabCategory.HEMATOLOGY]
        assert len(hematology) > 0

    def test_references_have_required_fields(self):
        """Test that all references have required fields."""
        for ref in LAB_REFERENCE_RANGES:
            assert ref.test_name
            assert ref.test_code
            assert ref.category
            assert ref.unit
            assert ref.low_normal is not None
            assert ref.high_normal is not None

    def test_common_tests_present(self):
        """Test that common tests are in the database."""
        service = LabReferenceService()

        # Common tests should be findable
        assert service.get_reference("Na") is not None
        assert service.get_reference("K") is not None
        assert service.get_reference("Glucose") is not None
        assert service.get_reference("WBC") is not None
        assert service.get_reference("Hgb") is not None


# ============================================================================
# Service Initialization Tests
# ============================================================================


class TestServiceInit:
    """Test service initialization."""

    def setup_method(self):
        """Reset singleton before each test."""
        reset_lab_reference_service()

    def test_service_creation(self):
        """Test basic service creation."""
        service = LabReferenceService()
        assert service is not None

    def test_singleton_pattern(self):
        """Test singleton pattern works."""
        service1 = get_lab_reference_service()
        service2 = get_lab_reference_service()
        assert service1 is service2

    def test_singleton_reset(self):
        """Test singleton can be reset."""
        service1 = get_lab_reference_service()
        reset_lab_reference_service()
        service2 = get_lab_reference_service()
        assert service1 is not service2


# ============================================================================
# Reference Lookup Tests
# ============================================================================


class TestReferenceLookup:
    """Test reference range lookup."""

    def setup_method(self):
        """Create service for testing."""
        reset_lab_reference_service()
        self.service = LabReferenceService()

    def test_lookup_by_code(self):
        """Test looking up by test code."""
        ref = self.service.get_reference("Na")
        assert ref is not None
        assert ref.test_name == "Sodium"

    def test_lookup_by_alias(self):
        """Test looking up by alias."""
        ref = self.service.get_reference("sodium")
        assert ref is not None
        assert ref.test_code == "Na"

    def test_lookup_case_insensitive(self):
        """Test case insensitive lookup."""
        ref1 = self.service.get_reference("NA")
        ref2 = self.service.get_reference("na")
        ref3 = self.service.get_reference("Na")
        assert ref1 == ref2 == ref3

    def test_lookup_unknown_test(self):
        """Test looking up unknown test."""
        ref = self.service.get_reference("unknowntest123")
        assert ref is None


# ============================================================================
# Interpretation Tests
# ============================================================================


class TestInterpretation:
    """Test lab value interpretation."""

    def setup_method(self):
        """Create service for testing."""
        reset_lab_reference_service()
        self.service = LabReferenceService()

    def test_interpret_normal_sodium(self):
        """Test interpreting normal sodium."""
        result = self.service.interpret("Na", 140)
        assert result is not None
        assert result.level == InterpretationLevel.NORMAL
        assert not result.is_critical

    def test_interpret_low_sodium(self):
        """Test interpreting low sodium."""
        result = self.service.interpret("Na", 130)
        assert result is not None
        assert result.level == InterpretationLevel.LOW
        assert not result.is_critical

    def test_interpret_critical_low_sodium(self):
        """Test interpreting critically low sodium."""
        result = self.service.interpret("Na", 115)
        assert result is not None
        assert result.level == InterpretationLevel.CRITICAL_LOW
        assert result.is_critical

    def test_interpret_high_potassium(self):
        """Test interpreting high potassium."""
        result = self.service.interpret("K", 5.5)
        assert result is not None
        assert result.level == InterpretationLevel.HIGH
        assert not result.is_critical

    def test_interpret_critical_high_potassium(self):
        """Test interpreting critically high potassium."""
        result = self.service.interpret("K", 7.0)
        assert result is not None
        assert result.level == InterpretationLevel.CRITICAL_HIGH
        assert result.is_critical

    def test_interpret_includes_causes(self):
        """Test that interpretation includes possible causes."""
        result = self.service.interpret("K", 6.0)
        assert result is not None
        assert len(result.possible_causes) > 0

    def test_interpret_includes_actions(self):
        """Test that abnormal values include recommended actions."""
        result = self.service.interpret("K", 7.0)
        assert result is not None
        assert len(result.recommended_actions) > 0

    def test_interpret_unknown_test(self):
        """Test interpreting unknown test."""
        result = self.service.interpret("unknowntest", 100)
        assert result is None


# ============================================================================
# Gender-Specific Tests
# ============================================================================


class TestGenderSpecific:
    """Test gender-specific reference ranges."""

    def setup_method(self):
        """Create service for testing."""
        reset_lab_reference_service()
        self.service = LabReferenceService()

    def test_hemoglobin_male_normal(self):
        """Test male hemoglobin interpretation."""
        result = self.service.interpret("Hgb", 14.0, gender="male")
        assert result is not None
        assert result.level == InterpretationLevel.NORMAL

    def test_hemoglobin_male_low(self):
        """Test male hemoglobin low threshold."""
        result = self.service.interpret("Hgb", 12.5, gender="male")
        assert result is not None
        assert result.level == InterpretationLevel.LOW

    def test_hemoglobin_female_normal(self):
        """Test female hemoglobin at same value is normal."""
        result = self.service.interpret("Hgb", 12.5, gender="female")
        assert result is not None
        assert result.level == InterpretationLevel.NORMAL

    def test_creatinine_gender_difference(self):
        """Test creatinine gender-specific ranges."""
        # 1.2 mg/dL is normal for males but may be high for females
        male_result = self.service.interpret("Cr", 1.2, gender="male")
        female_result = self.service.interpret("Cr", 1.2, gender="female")

        assert male_result is not None
        assert female_result is not None

        # Male should be normal, female may be high
        assert male_result.level == InterpretationLevel.NORMAL


# ============================================================================
# Panel Interpretation Tests
# ============================================================================


class TestPanelInterpretation:
    """Test multiple lab interpretation."""

    def setup_method(self):
        """Create service for testing."""
        reset_lab_reference_service()
        self.service = LabReferenceService()

    def test_interpret_bmp(self):
        """Test interpreting a basic metabolic panel."""
        values = {
            "Na": 138,
            "K": 4.2,
            "Cl": 102,
            "CO2": 24,
            "BUN": 15,
            "Cr": 1.0,
            "Glucose": 95,
        }
        results = self.service.interpret_panel(values)
        assert len(results) == 7

        # All should be normal in this panel
        for r in results:
            assert r.level == InterpretationLevel.NORMAL

    def test_interpret_abnormal_panel(self):
        """Test interpreting panel with abnormalities."""
        values = {
            "Na": 128,  # Low
            "K": 5.8,   # High
            "Glucose": 250,  # High
        }
        results = self.service.interpret_panel(values)

        # Should have abnormal values
        abnormal = [r for r in results if r.level != InterpretationLevel.NORMAL]
        assert len(abnormal) == 3

    def test_interpret_panel_skips_unknown(self):
        """Test that unknown tests are skipped."""
        values = {
            "Na": 140,
            "unknown_test": 100,
        }
        results = self.service.interpret_panel(values)
        assert len(results) == 1


# ============================================================================
# Search Tests
# ============================================================================


class TestSearch:
    """Test reference range search."""

    def setup_method(self):
        """Create service for testing."""
        reset_lab_reference_service()
        self.service = LabReferenceService()

    def test_search_by_name(self):
        """Test searching by test name."""
        results = self.service.search("sodium")
        assert len(results) > 0
        assert any("Sodium" in r.test_name for r in results)

    def test_search_by_alias(self):
        """Test searching by alias."""
        results = self.service.search("blood sugar")
        assert len(results) > 0

    def test_search_limit(self):
        """Test search limit."""
        results = self.service.search("", limit=5)
        assert len(results) <= 5

    def test_search_no_results(self):
        """Test search with no matches."""
        results = self.service.search("xyznonexistent123")
        assert len(results) == 0


# ============================================================================
# Category Filter Tests
# ============================================================================


class TestCategoryFilter:
    """Test filtering by category."""

    def setup_method(self):
        """Create service for testing."""
        reset_lab_reference_service()
        self.service = LabReferenceService()

    def test_filter_by_category(self):
        """Test filtering by category."""
        cardiac = self.service.get_all_references(LabCategory.CARDIAC)
        assert len(cardiac) > 0
        assert all(r.category == LabCategory.CARDIAC for r in cardiac)

    def test_no_filter_returns_all(self):
        """Test that no filter returns all references."""
        all_refs = self.service.get_all_references()
        assert len(all_refs) == len(LAB_REFERENCE_RANGES)


# ============================================================================
# Statistics Tests
# ============================================================================


class TestStatistics:
    """Test database statistics."""

    def setup_method(self):
        """Create service for testing."""
        reset_lab_reference_service()
        self.service = LabReferenceService()

    def test_get_stats(self):
        """Test getting database statistics."""
        stats = self.service.get_stats()

        assert "total_tests" in stats
        assert "by_category" in stats
        assert "gender_specific_count" in stats
        assert "with_critical_ranges" in stats
        assert "total_aliases" in stats

    def test_stats_count_correct(self):
        """Test that stats counts are correct."""
        stats = self.service.get_stats()

        # Total should match database size
        assert stats["total_tests"] == len(LAB_REFERENCE_RANGES)

        # Category counts should sum to total
        category_sum = sum(stats["by_category"].values())
        assert category_sum == stats["total_tests"]


# ============================================================================
# Clinical Scenario Tests
# ============================================================================


class TestClinicalScenarios:
    """Test realistic clinical scenarios."""

    def setup_method(self):
        """Create service for testing."""
        reset_lab_reference_service()
        self.service = LabReferenceService()

    def test_diabetic_patient_panel(self):
        """Test interpreting a diabetic patient's labs."""
        values = {
            "Glucose": 180,   # Elevated
            "HbA1c": 8.5,     # Elevated
            "Cr": 1.5,        # Slightly elevated
            "K": 5.2,         # High normal
        }
        results = self.service.interpret_panel(values)

        glucose = next((r for r in results if r.test_name == "Glucose"), None)
        assert glucose is not None
        assert glucose.level == InterpretationLevel.HIGH

        hba1c = next((r for r in results if r.test_name == "Hemoglobin A1c"), None)
        assert hba1c is not None
        assert hba1c.level == InterpretationLevel.HIGH

    def test_anemic_patient(self):
        """Test interpreting an anemic patient's labs."""
        values = {
            "Hgb": 8.5,     # Low
            "Hct": 26,      # Low
            "MCV": 70,      # Low - microcytic
        }
        results = self.service.interpret_panel(values)

        hgb = next((r for r in results if r.test_name == "Hemoglobin"), None)
        assert hgb is not None
        assert hgb.level == InterpretationLevel.LOW

        mcv = next((r for r in results if r.test_name == "Mean Corpuscular Volume"), None)
        assert mcv is not None
        assert mcv.level == InterpretationLevel.LOW

    def test_cardiac_patient(self):
        """Test interpreting cardiac markers."""
        values = {
            "TnI": 0.8,     # Elevated - above critical threshold of 0.5
            "BNP": 1000,    # Elevated - above critical threshold of 900
        }
        results = self.service.interpret_panel(values)

        troponin = next((r for r in results if "Troponin" in r.test_name), None)
        assert troponin is not None
        assert troponin.level == InterpretationLevel.CRITICAL_HIGH
        assert troponin.is_critical
