"""Tests for Drug Safety Service.

Tests the drug safety checking functionality.
"""

import pytest

from app.services.drug_safety import (
    DrugSafetyService,
    DrugSafetyProfile,
    SafetyLevel,
    PregnancyCategory,
    LactationSafety,
    get_drug_safety_service,
    reset_drug_safety_service,
    DRUG_SAFETY_PROFILES,
    DRUG_ALIASES,
)


# ============================================================================
# Service Tests
# ============================================================================


class TestServiceInit:
    """Test service initialization."""

    def setup_method(self):
        """Reset singleton before each test."""
        reset_drug_safety_service()

    def test_service_creation(self):
        """Test basic service creation."""
        service = DrugSafetyService()
        assert service is not None

    def test_singleton_pattern(self):
        """Test singleton pattern works."""
        service1 = get_drug_safety_service()
        service2 = get_drug_safety_service()
        assert service1 is service2

    def test_singleton_reset(self):
        """Test singleton can be reset."""
        service1 = get_drug_safety_service()
        reset_drug_safety_service()
        service2 = get_drug_safety_service()
        assert service1 is not service2


# ============================================================================
# Database Content Tests
# ============================================================================


class TestDatabaseContent:
    """Test the drug safety database content."""

    def test_database_not_empty(self):
        """Test that database has profiles."""
        assert len(DRUG_SAFETY_PROFILES) > 0

    def test_profiles_have_required_fields(self):
        """Test that all profiles have required fields."""
        for profile in DRUG_SAFETY_PROFILES:
            assert profile.drug_name
            assert profile.generic_name
            assert profile.drug_class

    def test_has_black_box_warnings(self):
        """Test that some drugs have black box warnings."""
        with_bbw = [p for p in DRUG_SAFETY_PROFILES if p.black_box_warnings]
        assert len(with_bbw) > 0

    def test_has_contraindications(self):
        """Test that drugs have contraindications."""
        with_ci = [p for p in DRUG_SAFETY_PROFILES if p.contraindications]
        assert len(with_ci) > 0

    def test_has_category_x_drugs(self):
        """Test that database has Category X drugs."""
        cat_x = [p for p in DRUG_SAFETY_PROFILES if p.pregnancy_category == PregnancyCategory.X]
        assert len(cat_x) > 0

    def test_aliases_exist(self):
        """Test that drug aliases are defined."""
        assert len(DRUG_ALIASES) > 0
        assert "coumadin" in DRUG_ALIASES


# ============================================================================
# Drug Name Normalization Tests
# ============================================================================


class TestDrugNameNormalization:
    """Test drug name normalization."""

    def setup_method(self):
        """Create service for testing."""
        reset_drug_safety_service()
        self.service = DrugSafetyService()

    def test_normalize_generic(self):
        """Test normalizing generic name."""
        assert self.service.normalize_drug_name("Warfarin") == "warfarin"
        assert self.service.normalize_drug_name("WARFARIN") == "warfarin"

    def test_normalize_brand(self):
        """Test normalizing brand name to generic."""
        assert self.service.normalize_drug_name("Coumadin") == "warfarin"
        assert self.service.normalize_drug_name("Motrin") == "ibuprofen"
        assert self.service.normalize_drug_name("Zoloft") == "sertraline"

    def test_normalize_unknown(self):
        """Test normalizing unknown drug."""
        assert self.service.normalize_drug_name("UnknownDrug") == "unknowndrug"


# ============================================================================
# Profile Lookup Tests
# ============================================================================


class TestProfileLookup:
    """Test profile lookup functionality."""

    def setup_method(self):
        """Create service for testing."""
        reset_drug_safety_service()
        self.service = DrugSafetyService()

    def test_get_profile_generic(self):
        """Test getting profile by generic name."""
        profile = self.service.get_profile("warfarin")
        assert profile is not None
        assert profile.drug_name == "Warfarin"

    def test_get_profile_brand(self):
        """Test getting profile by brand name."""
        profile = self.service.get_profile("Coumadin")
        assert profile is not None
        assert profile.generic_name == "warfarin"

    def test_get_profile_unknown(self):
        """Test getting profile for unknown drug."""
        profile = self.service.get_profile("unknowndrug123")
        assert profile is None


# ============================================================================
# Safety Check Tests
# ============================================================================


class TestSafetyCheck:
    """Test drug safety checking."""

    def setup_method(self):
        """Create service for testing."""
        reset_drug_safety_service()
        self.service = DrugSafetyService()

    def test_check_no_conditions(self):
        """Test checking drug with no patient conditions."""
        result = self.service.check_safety("metformin")
        assert result.drug_name == "Metformin"
        assert result.profile is not None

    def test_check_contraindicated_condition(self):
        """Test checking drug with contraindicated condition."""
        result = self.service.check_safety(
            "warfarin",
            patient_conditions=["active bleeding"],
        )
        assert result.overall_safety == SafetyLevel.CONTRAINDICATED
        assert len(result.contraindicated_conditions) > 0

    def test_check_warning_condition(self):
        """Test checking drug with warning condition."""
        result = self.service.check_safety(
            "metoprolol",
            patient_conditions=["severe asthma"],
        )
        assert result.overall_safety in [SafetyLevel.WARNING, SafetyLevel.CONTRAINDICATED]

    def test_check_unknown_drug(self):
        """Test checking unknown drug."""
        result = self.service.check_safety("unknowndrug123")
        assert result.profile is None
        assert len(result.warnings) > 0


# ============================================================================
# Pregnancy Safety Tests
# ============================================================================


class TestPregnancySafety:
    """Test pregnancy safety checking."""

    def setup_method(self):
        """Create service for testing."""
        reset_drug_safety_service()
        self.service = DrugSafetyService()

    def test_category_x_in_pregnancy(self):
        """Test Category X drug in pregnancy."""
        result = self.service.check_safety("warfarin", pregnant=True)
        assert result.pregnancy_warning is not None
        assert "X" in result.pregnancy_warning
        assert result.overall_safety == SafetyLevel.CONTRAINDICATED

    def test_category_b_in_pregnancy(self):
        """Test Category B drug in pregnancy."""
        result = self.service.check_safety("amoxicillin", pregnant=True)
        assert result.pregnancy_warning is not None
        assert "B" in result.pregnancy_warning
        # Should not be contraindicated
        assert ("Pregnancy" not in [c[0] for c in result.contraindicated_conditions])

    def test_category_d_in_pregnancy(self):
        """Test Category D drug in pregnancy."""
        result = self.service.check_safety("lisinopril", pregnant=True)
        assert result.pregnancy_warning is not None
        assert "D" in result.pregnancy_warning


# ============================================================================
# Lactation Safety Tests
# ============================================================================


class TestLactationSafety:
    """Test lactation safety checking."""

    def setup_method(self):
        """Create service for testing."""
        reset_drug_safety_service()
        self.service = DrugSafetyService()

    def test_safe_in_lactation(self):
        """Test safe drug in lactation."""
        result = self.service.check_safety("amoxicillin", lactating=True)
        assert result.lactation_warning is not None
        assert "safe" in result.lactation_warning.lower()

    def test_hazardous_in_lactation(self):
        """Test potentially hazardous drug in lactation."""
        result = self.service.check_safety("oxycodone", lactating=True)
        assert result.lactation_warning is not None
        assert "hazardous" in result.lactation_warning.lower()


# ============================================================================
# Age-Based Tests
# ============================================================================


class TestAgeBased:
    """Test age-based considerations."""

    def setup_method(self):
        """Create service for testing."""
        reset_drug_safety_service()
        self.service = DrugSafetyService()

    def test_geriatric_considerations(self):
        """Test geriatric dosing considerations."""
        result = self.service.check_safety("warfarin", age=75)
        geriatric_notes = [d for d in result.dosing_considerations if "geriatric" in d.lower()]
        assert len(geriatric_notes) > 0

    def test_pediatric_considerations(self):
        """Test pediatric considerations."""
        result = self.service.check_safety("ciprofloxacin", age=10)
        pediatric_notes = [d for d in result.dosing_considerations if "pediatric" in d.lower()]
        assert len(pediatric_notes) > 0


# ============================================================================
# Renal Dosing Tests
# ============================================================================


class TestRenalDosing:
    """Test renal dosing considerations."""

    def setup_method(self):
        """Create service for testing."""
        reset_drug_safety_service()
        self.service = DrugSafetyService()

    def test_renal_impairment_metformin(self):
        """Test metformin renal dosing."""
        result = self.service.check_safety("metformin", egfr=35)
        renal_notes = [d for d in result.dosing_considerations if "renal" in d.lower()]
        assert len(renal_notes) > 0

    def test_renal_impairment_gabapentin(self):
        """Test gabapentin renal dosing."""
        result = self.service.check_safety("gabapentin", egfr=25)
        renal_notes = [d for d in result.dosing_considerations if "renal" in d.lower()]
        assert len(renal_notes) > 0


# ============================================================================
# Search Tests
# ============================================================================


class TestSearch:
    """Test profile search functionality."""

    def setup_method(self):
        """Create service for testing."""
        reset_drug_safety_service()
        self.service = DrugSafetyService()

    def test_search_by_name(self):
        """Test searching by drug name."""
        results = self.service.search_profiles("warfarin")
        assert len(results) > 0
        assert any(r.generic_name == "warfarin" for r in results)

    def test_search_by_class(self):
        """Test searching by drug class."""
        results = self.service.search_profiles("NSAID")
        assert len(results) > 0

    def test_search_no_results(self):
        """Test search with no results."""
        results = self.service.search_profiles("xyz123notadrug")
        assert len(results) == 0

    def test_search_limit(self):
        """Test search limit."""
        results = self.service.search_profiles("", limit=3)
        assert len(results) <= 3


# ============================================================================
# Statistics Tests
# ============================================================================


class TestStatistics:
    """Test service statistics."""

    def setup_method(self):
        """Create service for testing."""
        reset_drug_safety_service()
        self.service = DrugSafetyService()

    def test_get_stats(self):
        """Test getting service statistics."""
        stats = self.service.get_stats()

        assert "total_drugs" in stats
        assert "by_class" in stats
        assert "with_black_box_warnings" in stats
        assert "pregnancy_category_d_or_x" in stats

    def test_stats_count_correct(self):
        """Test that stats counts are correct."""
        stats = self.service.get_stats()

        assert stats["total_drugs"] == len(DRUG_SAFETY_PROFILES)
        assert sum(stats["by_class"].values()) == stats["total_drugs"]


# ============================================================================
# Black Box Warning Tests
# ============================================================================


class TestBlackBoxWarnings:
    """Test black box warning detection."""

    def setup_method(self):
        """Create service for testing."""
        reset_drug_safety_service()
        self.service = DrugSafetyService()

    def test_warfarin_has_bbw(self):
        """Test warfarin has black box warning."""
        result = self.service.check_safety("warfarin")
        assert len([w for w in result.warnings if "bleeding" in w.lower()]) > 0

    def test_oxycodone_has_bbw(self):
        """Test oxycodone has black box warning."""
        result = self.service.check_safety("oxycodone")
        bbw_warnings = [w for w in result.warnings if "addiction" in w.lower() or "respiratory" in w.lower()]
        assert len(bbw_warnings) > 0

    def test_sertraline_has_bbw(self):
        """Test sertraline has black box warning."""
        result = self.service.check_safety("sertraline")
        bbw_warnings = [w for w in result.warnings if "suicidal" in w.lower()]
        assert len(bbw_warnings) > 0


# ============================================================================
# Clinical Scenario Tests
# ============================================================================


class TestClinicalScenarios:
    """Test realistic clinical scenarios."""

    def setup_method(self):
        """Create service for testing."""
        reset_drug_safety_service()
        self.service = DrugSafetyService()

    def test_elderly_patient_warfarin(self):
        """Test warfarin in elderly patient."""
        result = self.service.check_safety(
            "warfarin",
            age=82,
            patient_conditions=["falls risk"],
        )
        # Should have geriatric considerations
        assert any("geriatric" in d.lower() for d in result.dosing_considerations)

    def test_pregnant_patient_ace_inhibitor(self):
        """Test ACE inhibitor in pregnant patient."""
        result = self.service.check_safety(
            "lisinopril",
            pregnant=True,
        )
        # ACE inhibitors are Category D
        assert result.pregnancy_warning is not None
        assert "D" in result.pregnancy_warning

    def test_renal_patient_metformin(self):
        """Test metformin in patient with CKD."""
        result = self.service.check_safety(
            "metformin",
            patient_conditions=["chronic kidney disease"],
            egfr=25,
        )
        # Metformin is contraindicated in severe renal impairment
        assert result.overall_safety in [SafetyLevel.CONTRAINDICATED, SafetyLevel.WARNING]

    def test_asthmatic_patient_beta_blocker(self):
        """Test beta blocker in asthmatic patient."""
        result = self.service.check_safety(
            "metoprolol",
            patient_conditions=["asthma"],
        )
        # Should flag as warning
        assert result.overall_safety in [SafetyLevel.WARNING, SafetyLevel.CAUTION]

    def test_gi_bleeding_patient_nsaid(self):
        """Test NSAID in patient with GI bleeding history."""
        result = self.service.check_safety(
            "ibuprofen",
            patient_conditions=["history of GI bleeding"],
        )
        # Should flag as warning
        assert result.overall_safety in [SafetyLevel.WARNING, SafetyLevel.CAUTION]

    def test_multiple_conditions(self):
        """Test drug with multiple patient conditions."""
        result = self.service.check_safety(
            "ibuprofen",
            patient_conditions=["heart failure", "chronic kidney disease", "history of GI ulcer"],
            age=72,
        )
        # Should have multiple warnings
        assert result.overall_safety in [SafetyLevel.WARNING, SafetyLevel.CONTRAINDICATED]
        assert len(result.warnings) + len(result.cautions) + len(result.contraindicated_conditions) > 1
