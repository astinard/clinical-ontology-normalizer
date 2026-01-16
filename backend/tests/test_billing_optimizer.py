"""Tests for Billing Optimization Engine.

Tests the billing optimization functionality including E/M optimization,
bundling checks, medical necessity, and missed service detection.
"""

import pytest

from app.services.billing_optimizer import (
    BillingOptimizationService,
    ConfidenceLevel,
    EncounterCodes,
    EncounterContext,
    OptimizationCategory,
    SeverityLevel,
    get_billing_optimization_service,
    reset_billing_optimization_service,
)


# ============================================================================
# Service Tests
# ============================================================================


class TestServiceInit:
    """Test service initialization."""

    def setup_method(self):
        """Reset singleton before each test."""
        reset_billing_optimization_service()

    def test_service_creation(self):
        """Test basic service creation."""
        service = BillingOptimizationService()
        assert service is not None

    def test_singleton_pattern(self):
        """Test singleton pattern works."""
        service1 = get_billing_optimization_service()
        service2 = get_billing_optimization_service()
        assert service1 is service2

    def test_singleton_reset(self):
        """Test singleton can be reset."""
        service1 = get_billing_optimization_service()
        reset_billing_optimization_service()
        service2 = get_billing_optimization_service()
        assert service1 is not service2


# ============================================================================
# E/M Optimization Tests
# ============================================================================


class TestEMOptimization:
    """Test E/M code optimization functionality."""

    def setup_method(self):
        """Create service for testing."""
        reset_billing_optimization_service()
        self.service = BillingOptimizationService()

    def test_em_upcoding_by_time(self):
        """Test E/M upcoding opportunity based on time."""
        codes = EncounterCodes(
            cpt_codes=["99213"],  # Low complexity
            icd10_codes=["I10"],
        )
        context = EncounterContext(
            time_spent=35,  # Supports 99214 (30+ min)
            patient_type="established",
        )

        result = self.service.analyze_encounter(codes, context)

        # Should find upcoding opportunity
        upcode_findings = [
            f for f in result.findings
            if f.category == OptimizationCategory.UPCODING_OPPORTUNITY
        ]
        assert len(upcode_findings) >= 1

        # Check the recommendation
        finding = upcode_findings[0]
        assert finding.current_code == "99213"
        assert finding.recommended_code == "99214"
        assert finding.revenue_impact > 0

    def test_em_upcoding_by_mdm(self):
        """Test E/M upcoding opportunity based on MDM."""
        codes = EncounterCodes(
            cpt_codes=["99213"],
            icd10_codes=["I10", "E11.9"],
        )
        context = EncounterContext(
            mdm_complexity="moderate",  # Supports 99214
            patient_type="established",
        )

        result = self.service.analyze_encounter(codes, context)

        upcode_findings = [
            f for f in result.findings
            if f.category == OptimizationCategory.UPCODING_OPPORTUNITY
        ]
        assert len(upcode_findings) >= 1

    def test_no_upcoding_when_appropriate(self):
        """Test no upcoding suggested when code is appropriate."""
        codes = EncounterCodes(
            cpt_codes=["99214"],
            icd10_codes=["I10"],
        )
        context = EncounterContext(
            time_spent=32,  # Appropriate for 99214
            mdm_complexity="moderate",
            patient_type="established",
        )

        result = self.service.analyze_encounter(codes, context)

        # Should not suggest upcoding to 99215 (needs 40+ min)
        upcode_findings = [
            f for f in result.findings
            if f.category == OptimizationCategory.UPCODING_OPPORTUNITY
        ]
        assert len(upcode_findings) == 0


# ============================================================================
# Bundling Tests
# ============================================================================


class TestBundling:
    """Test CCI bundling compliance checks."""

    def setup_method(self):
        """Create service for testing."""
        reset_billing_optimization_service()
        self.service = BillingOptimizationService()

    def test_detect_bundling_issue(self):
        """Test detection of CCI bundling edit."""
        codes = EncounterCodes(
            cpt_codes=["99214", "99211"],  # Can't bill both E/M levels
            icd10_codes=["I10"],
        )
        context = EncounterContext()

        result = self.service.analyze_encounter(codes, context)

        bundling_findings = [
            f for f in result.findings
            if f.category == OptimizationCategory.BUNDLING_ISSUE
        ]
        assert len(bundling_findings) >= 1

        finding = bundling_findings[0]
        assert finding.severity == SeverityLevel.HIGH

    def test_no_bundling_issue_when_clean(self):
        """Test no bundling issue when codes are appropriate."""
        codes = EncounterCodes(
            cpt_codes=["99214", "93000"],  # E/M + ECG is fine
            icd10_codes=["I10"],
        )
        context = EncounterContext()

        result = self.service.analyze_encounter(codes, context)

        bundling_findings = [
            f for f in result.findings
            if f.category == OptimizationCategory.BUNDLING_ISSUE
        ]
        # 99214 + 93000 should not trigger bundling
        # (unless we have that specific rule)
        assert len(bundling_findings) == 0


# ============================================================================
# Medical Necessity Tests
# ============================================================================


class TestMedicalNecessity:
    """Test medical necessity checking."""

    def setup_method(self):
        """Create service for testing."""
        reset_billing_optimization_service()
        self.service = BillingOptimizationService()

    def test_detect_missing_necessity(self):
        """Test detection of missing medical necessity."""
        codes = EncounterCodes(
            cpt_codes=["93000"],  # ECG
            icd10_codes=["Z00.00"],  # General exam - not typical ECG indication
        )
        context = EncounterContext()

        result = self.service.analyze_encounter(codes, context)

        necessity_findings = [
            f for f in result.findings
            if f.category == OptimizationCategory.MEDICAL_NECESSITY
        ]
        assert len(necessity_findings) >= 1

    def test_no_necessity_issue_when_supported(self):
        """Test no issue when diagnosis supports procedure."""
        codes = EncounterCodes(
            cpt_codes=["93000"],  # ECG
            icd10_codes=["I48.91"],  # Atrial fibrillation - supports ECG
        )
        context = EncounterContext()

        result = self.service.analyze_encounter(codes, context)

        necessity_findings = [
            f for f in result.findings
            if f.category == OptimizationCategory.MEDICAL_NECESSITY
        ]
        assert len(necessity_findings) == 0


# ============================================================================
# Missed Service Tests
# ============================================================================


class TestMissedServices:
    """Test missed billable service detection."""

    def setup_method(self):
        """Create service for testing."""
        reset_billing_optimization_service()
        self.service = BillingOptimizationService()

    def test_detect_missed_tobacco_counseling(self):
        """Test detection of missed tobacco cessation counseling."""
        codes = EncounterCodes(
            cpt_codes=["99214"],
            icd10_codes=["F17.210"],  # Nicotine dependence
        )
        context = EncounterContext(
            diagnoses=["smoking cessation counseling provided"],
        )

        result = self.service.analyze_encounter(codes, context)

        missed_findings = [
            f for f in result.findings
            if f.category == OptimizationCategory.MISSED_SERVICE
        ]
        assert len(missed_findings) >= 1

        # Should suggest 99406
        tobacco_finding = next(
            (f for f in missed_findings if "99406" in str(f.recommended_code)),
            None
        )
        assert tobacco_finding is not None

    def test_no_missed_when_coded(self):
        """Test no missed service when already coded."""
        codes = EncounterCodes(
            cpt_codes=["99214", "99406"],  # E/M + tobacco counseling
            icd10_codes=["F17.210"],
        )
        context = EncounterContext(
            diagnoses=["smoking cessation counseling"],
        )

        result = self.service.analyze_encounter(codes, context)

        missed_findings = [
            f for f in result.findings
            if f.category == OptimizationCategory.MISSED_SERVICE
            and "99406" in str(f.recommended_code)
        ] if result.findings else []
        assert len(missed_findings) == 0


# ============================================================================
# Modifier Tests
# ============================================================================


class TestModifiers:
    """Test modifier recommendation functionality."""

    def setup_method(self):
        """Create service for testing."""
        reset_billing_optimization_service()
        self.service = BillingOptimizationService()

    def test_suggest_modifier_25(self):
        """Test suggestion of modifier 25 for E/M with procedure."""
        codes = EncounterCodes(
            cpt_codes=["99214", "96372"],  # E/M + injection
            icd10_codes=["M54.5"],
        )
        context = EncounterContext()

        result = self.service.analyze_encounter(codes, context)

        modifier_findings = [
            f for f in result.findings
            if f.category == OptimizationCategory.MODIFIER_NEEDED
        ]
        assert len(modifier_findings) >= 1

        # Should suggest modifier 25
        mod25_finding = next(
            (f for f in modifier_findings if "25" in f.title),
            None
        )
        assert mod25_finding is not None

    def test_no_modifier_when_present(self):
        """Test no modifier suggestion when already present."""
        codes = EncounterCodes(
            cpt_codes=["99214", "96372"],
            icd10_codes=["M54.5"],
            modifiers=[("99214", "25")],  # Already has modifier 25
        )
        context = EncounterContext()

        result = self.service.analyze_encounter(codes, context)

        modifier_findings = [
            f for f in result.findings
            if f.category == OptimizationCategory.MODIFIER_NEEDED
            and "25" in f.title
        ]
        assert len(modifier_findings) == 0


# ============================================================================
# Documentation Gap Tests
# ============================================================================


class TestDocumentationGaps:
    """Test documentation gap detection."""

    def setup_method(self):
        """Create service for testing."""
        reset_billing_optimization_service()
        self.service = BillingOptimizationService()

    def test_detect_missing_time(self):
        """Test detection of missing time documentation."""
        codes = EncounterCodes(
            cpt_codes=["99214"],
            icd10_codes=["I10"],
        )
        context = EncounterContext(
            time_spent=None,  # No time documented
        )

        result = self.service.analyze_encounter(codes, context)

        doc_findings = [
            f for f in result.findings
            if f.category == OptimizationCategory.DOCUMENTATION_GAP
            and "time" in f.title.lower()
        ]
        assert len(doc_findings) >= 1

    def test_detect_missing_mdm(self):
        """Test detection of missing MDM documentation."""
        codes = EncounterCodes(
            cpt_codes=["99214"],
            icd10_codes=["I10"],
        )
        context = EncounterContext(
            mdm_complexity=None,  # No MDM documented
        )

        result = self.service.analyze_encounter(codes, context)

        doc_findings = [
            f for f in result.findings
            if f.category == OptimizationCategory.DOCUMENTATION_GAP
            and "mdm" in f.title.lower()
        ]
        assert len(doc_findings) >= 1


# ============================================================================
# CER Citation Tests
# ============================================================================


class TestCERCitations:
    """Test CER citations in findings."""

    def setup_method(self):
        """Create service for testing."""
        reset_billing_optimization_service()
        self.service = BillingOptimizationService()

    def test_findings_have_cer(self):
        """Test that findings include CER citations."""
        codes = EncounterCodes(
            cpt_codes=["99213"],
            icd10_codes=["I10"],
        )
        context = EncounterContext(
            time_spent=35,  # Triggers upcoding opportunity
        )

        result = self.service.analyze_encounter(codes, context)

        for finding in result.findings:
            assert finding.cer_citation is not None
            assert finding.cer_citation.claim
            assert len(finding.cer_citation.evidence) > 0
            assert finding.cer_citation.reasoning
            assert finding.cer_citation.strength in ConfidenceLevel

    def test_cer_has_regulatory_basis(self):
        """Test that CER includes regulatory basis."""
        codes = EncounterCodes(
            cpt_codes=["99214", "99211"],  # Bundling issue
            icd10_codes=["I10"],
        )
        context = EncounterContext()

        result = self.service.analyze_encounter(codes, context)

        for finding in result.findings:
            if finding.category == OptimizationCategory.BUNDLING_ISSUE:
                assert len(finding.cer_citation.regulatory_basis) > 0


# ============================================================================
# Result Metrics Tests
# ============================================================================


class TestResultMetrics:
    """Test result metrics and calculations."""

    def setup_method(self):
        """Create service for testing."""
        reset_billing_optimization_service()
        self.service = BillingOptimizationService()

    def test_rvu_calculation(self):
        """Test RVU calculation in results."""
        codes = EncounterCodes(
            cpt_codes=["99214"],
            icd10_codes=["I10"],
        )
        context = EncounterContext()

        result = self.service.analyze_encounter(codes, context)

        assert result.estimated_current_rvu > 0
        assert result.estimated_optimized_rvu >= result.estimated_current_rvu

    def test_compliance_score(self):
        """Test compliance score calculation."""
        # Clean encounter
        codes = EncounterCodes(
            cpt_codes=["99214"],
            icd10_codes=["I10"],
        )
        context = EncounterContext(
            time_spent=32,
            mdm_complexity="moderate",
        )

        result = self.service.analyze_encounter(codes, context)
        assert result.compliance_score >= 0
        assert result.compliance_score <= 100

    def test_by_category_counts(self):
        """Test findings are counted by category."""
        codes = EncounterCodes(
            cpt_codes=["99213"],
            icd10_codes=["I10"],
        )
        context = EncounterContext(
            time_spent=35,
        )

        result = self.service.analyze_encounter(codes, context)

        # Total should match sum of categories
        assert result.total_findings == sum(result.by_category.values())

    def test_priority_actions_generated(self):
        """Test priority actions are generated."""
        codes = EncounterCodes(
            cpt_codes=["99213"],
            icd10_codes=["I10"],
        )
        context = EncounterContext(
            time_spent=45,  # Multiple opportunities
        )

        result = self.service.analyze_encounter(codes, context)

        if result.findings:
            assert len(result.priority_actions) > 0
            assert len(result.priority_actions) <= 5


# ============================================================================
# Statistics Tests
# ============================================================================


class TestStatistics:
    """Test service statistics."""

    def setup_method(self):
        """Create service for testing."""
        reset_billing_optimization_service()
        self.service = BillingOptimizationService()

    def test_get_stats(self):
        """Test getting service statistics."""
        stats = self.service.get_stats()

        assert "cci_bundles_tracked" in stats
        assert "medical_necessity_rules" in stats
        assert "em_codes_tracked" in stats
        assert "missed_service_rules" in stats
        assert stats["cci_bundles_tracked"] > 0


# ============================================================================
# Clinical Scenario Tests
# ============================================================================


class TestClinicalScenarios:
    """Test realistic clinical scenarios."""

    def setup_method(self):
        """Create service for testing."""
        reset_billing_optimization_service()
        self.service = BillingOptimizationService()

    def test_complex_encounter_analysis(self):
        """Test analysis of a complex encounter."""
        codes = EncounterCodes(
            cpt_codes=["99213", "93000", "85025"],  # E/M + ECG + CBC
            icd10_codes=["I10", "R00.1"],  # HTN + Palpitations
        )
        context = EncounterContext(
            setting="office",
            patient_type="established",
            time_spent=40,
            mdm_complexity="moderate",
            diagnoses=["hypertension", "palpitations", "discussed smoking cessation"],
        )

        result = self.service.analyze_encounter(codes, context)

        # Should have multiple findings
        assert result.total_findings > 0

        # Should suggest E/M upcoding (40 min supports 99214 or 99215)
        upcode = [f for f in result.findings
                  if f.category == OptimizationCategory.UPCODING_OPPORTUNITY]
        assert len(upcode) > 0

        # Should have overall assessment
        assert len(result.overall_assessment) > 0

    def test_clean_encounter_no_issues(self):
        """Test that a properly coded encounter has minimal findings."""
        codes = EncounterCodes(
            cpt_codes=["99214"],
            icd10_codes=["I10", "E11.9"],
            modifiers=[],
        )
        context = EncounterContext(
            setting="office",
            patient_type="established",
            time_spent=32,
            mdm_complexity="moderate",
        )

        result = self.service.analyze_encounter(codes, context)

        # Should have good compliance
        assert result.compliance_score >= 70

        # High-severity findings should be minimal
        high_findings = [f for f in result.findings if f.severity == SeverityLevel.HIGH]
        assert len(high_findings) <= 1
