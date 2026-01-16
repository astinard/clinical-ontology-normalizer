"""Tests for CPT-4 Code Suggester Service with CER Framework.

Tests the CPT code suggestion functionality and CER citations.
"""

import pytest

from app.services.cpt_suggester import (
    CERCitation,
    ConfidenceLevel,
    CPTCategory,
    CPTCode,
    CPTSuggesterService,
    CPT_CODES,
    SYNONYM_TO_CPT,
    get_cpt_suggester_service,
    reset_cpt_suggester_service,
)


# ============================================================================
# Service Tests
# ============================================================================


class TestServiceInit:
    """Test service initialization."""

    def setup_method(self):
        """Reset singleton before each test."""
        reset_cpt_suggester_service()

    def test_service_creation(self):
        """Test basic service creation."""
        service = CPTSuggesterService()
        assert service is not None

    def test_singleton_pattern(self):
        """Test singleton pattern works."""
        service1 = get_cpt_suggester_service()
        service2 = get_cpt_suggester_service()
        assert service1 is service2

    def test_singleton_reset(self):
        """Test singleton can be reset."""
        service1 = get_cpt_suggester_service()
        reset_cpt_suggester_service()
        service2 = get_cpt_suggester_service()
        assert service1 is not service2


# ============================================================================
# Database Content Tests
# ============================================================================


class TestDatabaseContent:
    """Test the CPT code database content."""

    def test_database_not_empty(self):
        """Test that database has codes."""
        assert len(CPT_CODES) > 0

    def test_codes_have_required_fields(self):
        """Test that all codes have required fields."""
        for code in CPT_CODES:
            assert code.code
            assert code.description
            assert code.category

    def test_has_multiple_categories(self):
        """Test that database covers multiple categories."""
        categories = set(code.category for code in CPT_CODES)
        assert len(categories) >= 3

    def test_synonym_index_exists(self):
        """Test that synonym index is populated."""
        assert len(SYNONYM_TO_CPT) > 0

    def test_em_codes_present(self):
        """Test that E/M codes are in the database."""
        service = CPTSuggesterService()

        # Should find common E/M codes
        assert service.get_code("99213") is not None
        assert service.get_code("99214") is not None
        assert service.get_code("99215") is not None


# ============================================================================
# Code Lookup Tests
# ============================================================================


class TestCodeLookup:
    """Test code lookup functionality."""

    def setup_method(self):
        """Create service for testing."""
        reset_cpt_suggester_service()
        self.service = CPTSuggesterService()

    def test_get_code_exact(self):
        """Test getting code by exact code."""
        code = self.service.get_code("99213")
        assert code is not None
        assert "established patient" in code.description.lower()

    def test_get_code_not_found(self):
        """Test getting nonexistent code."""
        code = self.service.get_code("00000")
        assert code is None


# ============================================================================
# Code Suggestion Tests
# ============================================================================


class TestCodeSuggestion:
    """Test code suggestion functionality."""

    def setup_method(self):
        """Create service for testing."""
        reset_cpt_suggester_service()
        self.service = CPTSuggesterService()

    def test_suggest_by_synonym(self):
        """Test suggesting by exact synonym."""
        result = self.service.suggest_codes("follow up visit")
        assert len(result.suggestions) > 0
        codes = [s.code for s in result.suggestions]
        # Should find established patient E/M codes
        assert any(c.startswith("992") for c in codes)

    def test_suggest_ecg(self):
        """Test suggesting ECG code."""
        result = self.service.suggest_codes("ecg")
        codes = [s.code for s in result.suggestions]
        assert "93000" in codes

    def test_suggest_chest_xray(self):
        """Test suggesting chest x-ray code."""
        result = self.service.suggest_codes("chest xray")
        codes = [s.code for s in result.suggestions]
        assert "71046" in codes

    def test_suggest_injection(self):
        """Test suggesting injection code."""
        result = self.service.suggest_codes("im injection")
        codes = [s.code for s in result.suggestions]
        assert "96372" in codes

    def test_suggest_no_matches(self):
        """Test suggesting with no matches."""
        result = self.service.suggest_codes("xyz123notaprocedure")
        assert len(result.suggestions) == 0

    def test_suggest_limit(self):
        """Test suggestion limit."""
        result = self.service.suggest_codes("visit", max_suggestions=3)
        assert len(result.suggestions) <= 3


# ============================================================================
# CER Citation Tests
# ============================================================================


class TestCERCitation:
    """Test CER (Claim-Evidence-Reasoning) citation functionality."""

    def setup_method(self):
        """Create service for testing."""
        reset_cpt_suggester_service()
        self.service = CPTSuggesterService()

    def test_suggestions_have_cer(self):
        """Test that suggestions include CER citations."""
        result = self.service.suggest_codes("office visit")
        assert len(result.suggestions) > 0

        for suggestion in result.suggestions:
            assert suggestion.cer_citation is not None
            assert suggestion.cer_citation.claim
            assert suggestion.cer_citation.evidence
            assert suggestion.cer_citation.reasoning
            assert suggestion.cer_citation.strength

    def test_cer_claim_contains_code(self):
        """Test that CER claim references the code."""
        result = self.service.suggest_codes("ecg")
        if result.suggestions:
            suggestion = result.suggestions[0]
            assert suggestion.code in suggestion.cer_citation.claim

    def test_cer_evidence_has_items(self):
        """Test that CER evidence is populated."""
        result = self.service.suggest_codes(
            "follow up visit",
            clinical_context={
                "time_spent": "30",
                "mdm_complexity": "moderate",
            }
        )
        if result.suggestions:
            suggestion = result.suggestions[0]
            # Should have evidence from clinical context
            assert len(suggestion.cer_citation.evidence) >= 2

    def test_cer_strength_matches_confidence(self):
        """Test that CER strength aligns with confidence level."""
        result = self.service.suggest_codes("ecg")  # Exact match
        if result.suggestions:
            suggestion = result.suggestions[0]
            # Strength should match confidence
            assert suggestion.cer_citation.strength == suggestion.confidence

    def test_cer_with_clinical_context(self):
        """Test CER generation with clinical context."""
        result = self.service.suggest_codes(
            "office visit",
            clinical_context={
                "time_spent": "35",
                "mdm_complexity": "moderate",
                "new_patient": "false",
                "diagnoses": "I10, E11.9",
            }
        )
        if result.suggestions:
            suggestion = result.suggestions[0]
            evidence = suggestion.cer_citation.evidence
            # Should include time in evidence
            assert any("time" in e.lower() for e in evidence)


# ============================================================================
# Clinical Context Tests
# ============================================================================


class TestClinicalContext:
    """Test clinical context handling."""

    def setup_method(self):
        """Create service for testing."""
        reset_cpt_suggester_service()
        self.service = CPTSuggesterService()

    def test_context_captured_in_result(self):
        """Test that clinical context is captured in result."""
        context = {"time_spent": "30", "setting": "office"}
        result = self.service.suggest_codes("visit", clinical_context=context)
        assert result.clinical_context == context

    def test_documentation_gaps_identified(self):
        """Test that documentation gaps are identified."""
        result = self.service.suggest_codes("office visit")
        # Without clinical context, should identify gaps for E/M coding
        em_suggestions = [s for s in result.suggestions if "992" in s.code]
        if em_suggestions:
            assert len(result.documentation_gaps) > 0


# ============================================================================
# Search Tests
# ============================================================================


class TestSearch:
    """Test code search functionality."""

    def setup_method(self):
        """Create service for testing."""
        reset_cpt_suggester_service()
        self.service = CPTSuggesterService()

    def test_search_by_description(self):
        """Test searching by description."""
        results = self.service.search_codes("hospital")
        assert len(results) > 0
        assert any("hospital" in r.description.lower() for r in results)

    def test_search_by_synonym(self):
        """Test searching by synonym."""
        results = self.service.search_codes("cbc")
        assert len(results) > 0

    def test_search_limit(self):
        """Test search limit."""
        results = self.service.search_codes("", limit=5)
        assert len(results) <= 5


# ============================================================================
# Category Tests
# ============================================================================


class TestCategories:
    """Test category-based functionality."""

    def setup_method(self):
        """Create service for testing."""
        reset_cpt_suggester_service()
        self.service = CPTSuggesterService()

    def test_get_codes_by_category(self):
        """Test getting codes by category."""
        em_codes = self.service.get_codes_by_category(CPTCategory.EVALUATION_MANAGEMENT)
        assert len(em_codes) > 0
        assert all(c.category == CPTCategory.EVALUATION_MANAGEMENT for c in em_codes)

    def test_has_common_categories(self):
        """Test that common categories have codes."""
        assert len(self.service.get_codes_by_category(CPTCategory.EVALUATION_MANAGEMENT)) > 0
        assert len(self.service.get_codes_by_category(CPTCategory.MEDICINE)) > 0
        assert len(self.service.get_codes_by_category(CPTCategory.PATHOLOGY)) > 0


# ============================================================================
# Statistics Tests
# ============================================================================


class TestStatistics:
    """Test service statistics."""

    def setup_method(self):
        """Create service for testing."""
        reset_cpt_suggester_service()
        self.service = CPTSuggesterService()

    def test_get_stats(self):
        """Test getting service statistics."""
        stats = self.service.get_stats()

        assert "total_codes" in stats
        assert "total_synonyms" in stats
        assert "by_category" in stats

    def test_stats_count_correct(self):
        """Test that stats counts are correct."""
        stats = self.service.get_stats()

        # Service loads core codes + extended fixture, so count >= core codes
        assert stats["total_codes"] >= len(CPT_CODES)
        assert sum(stats["by_category"].values()) == stats["total_codes"]


# ============================================================================
# Clinical Scenario Tests
# ============================================================================


class TestClinicalScenarios:
    """Test realistic clinical scenarios."""

    def setup_method(self):
        """Create service for testing."""
        reset_cpt_suggester_service()
        self.service = CPTSuggesterService()

    def test_established_patient_visit(self):
        """Test coding for established patient visit."""
        result = self.service.suggest_codes(
            "routine follow up",
            clinical_context={
                "time_spent": "25",
                "mdm_complexity": "low",
                "new_patient": "false",
            }
        )
        codes = [s.code for s in result.suggestions]
        # 99213 is typical for low complexity established patient
        assert "99213" in codes or "99212" in codes

    def test_new_patient_visit(self):
        """Test coding for new patient visit."""
        result = self.service.suggest_codes(
            "new patient office visit",
            clinical_context={
                "time_spent": "45",
                "mdm_complexity": "moderate",
                "new_patient": "true",
            }
        )
        codes = [s.code for s in result.suggestions]
        # Should find new patient E/M codes
        assert any(c in ["99202", "99203", "99204", "99205"] for c in codes)

    def test_emergency_visit(self):
        """Test coding for emergency department visit."""
        result = self.service.suggest_codes("ed visit")
        codes = [s.code for s in result.suggestions]
        # Should find ED codes
        assert any(c.startswith("9928") for c in codes)

    def test_hospital_admission(self):
        """Test coding for hospital admission."""
        result = self.service.suggest_codes("hospital admission")
        codes = [s.code for s in result.suggestions]
        # Should find initial hospital care codes
        assert any(c in ["99221", "99222", "99223"] for c in codes)

    def test_lab_panel_suggestion(self):
        """Test suggesting lab panels."""
        result = self.service.suggest_codes("comprehensive metabolic panel")
        codes = [s.code for s in result.suggestions]
        assert "80053" in codes

    def test_telehealth_visit(self):
        """Test coding for telehealth visit."""
        result = self.service.suggest_codes("phone visit")
        codes = [s.code for s in result.suggestions]
        assert any(c in ["99441", "99442"] for c in codes)

    def test_smoking_cessation(self):
        """Test coding for smoking cessation."""
        result = self.service.suggest_codes("tobacco counseling")
        codes = [s.code for s in result.suggestions]
        assert "99406" in codes


# ============================================================================
# Documentation and Modifier Tests
# ============================================================================


class TestDocumentation:
    """Test documentation requirements and modifiers."""

    def setup_method(self):
        """Create service for testing."""
        reset_cpt_suggester_service()
        self.service = CPTSuggesterService()

    def test_suggestions_have_documentation_checklist(self):
        """Test that suggestions include documentation requirements."""
        result = self.service.suggest_codes("office visit")
        if result.suggestions:
            suggestion = result.suggestions[0]
            assert len(suggestion.documentation_checklist) > 0

    def test_suggestions_have_modifiers(self):
        """Test that applicable codes have modifier suggestions."""
        result = self.service.suggest_codes("ecg")
        ecg = next((s for s in result.suggestions if s.code == "93000"), None)
        if ecg:
            # ECG commonly has 26 (professional) modifier
            assert len(ecg.suggested_modifiers) > 0

    def test_suggestions_have_supporting_diagnoses(self):
        """Test that suggestions include supporting diagnoses."""
        result = self.service.suggest_codes("office visit")
        if result.suggestions:
            suggestion = result.suggestions[0]
            # E/M codes should have common diagnoses
            assert len(suggestion.supporting_diagnoses) > 0

    def test_coding_tips_generated(self):
        """Test that coding tips are generated."""
        result = self.service.suggest_codes("office visit")
        # E/M coding should generate tips
        if any("992" in s.code for s in result.suggestions):
            assert len(result.coding_tips) > 0
