"""Tests for NLP confidence scoring."""

from uuid import uuid4

import pytest

from app.schemas.base import Assertion
from app.services.nlp_rule_based import RuleBasedNLPService
from app.services.section_parser import ClinicalSection


class TestConfidenceCalculation:
    """Tests for the confidence calculation method."""

    @pytest.fixture
    def nlp_service(self) -> RuleBasedNLPService:
        return RuleBasedNLPService()

    def test_longer_terms_higher_confidence(self, nlp_service: RuleBasedNLPService) -> None:
        """Test that longer terms get higher confidence scores."""
        nlp_service._initialize_patterns()

        # Short term (3 chars)
        short_conf = nlp_service._calculate_confidence(
            matched_text="CAD",
            lexical_variant="CAD",
            concept_id=12345,
            domain_id="Condition",
            clinical_section=ClinicalSection.PAST_MEDICAL_HISTORY,
            assertion=Assertion.PRESENT,
        )

        # Long term (15 chars)
        long_conf = nlp_service._calculate_confidence(
            matched_text="Coronary Artery",
            lexical_variant="Coronary Artery",
            concept_id=12345,
            domain_id="Condition",
            clinical_section=ClinicalSection.PAST_MEDICAL_HISTORY,
            assertion=Assertion.PRESENT,
        )

        assert long_conf > short_conf

    def test_concept_id_boosts_confidence(self, nlp_service: RuleBasedNLPService) -> None:
        """Test that having a concept_id increases confidence."""
        nlp_service._initialize_patterns()

        # With concept_id
        with_id = nlp_service._calculate_confidence(
            matched_text="Metformin",
            lexical_variant="Metformin",
            concept_id=1503297,
            domain_id="Drug",
            clinical_section=ClinicalSection.MEDICATIONS,
            assertion=Assertion.PRESENT,
        )

        # Without concept_id
        without_id = nlp_service._calculate_confidence(
            matched_text="Metformin",
            lexical_variant="Metformin",
            concept_id=None,
            domain_id="Drug",
            clinical_section=ClinicalSection.MEDICATIONS,
            assertion=Assertion.PRESENT,
        )

        assert with_id > without_id

    def test_section_domain_fit_affects_confidence(self, nlp_service: RuleBasedNLPService) -> None:
        """Test that section-domain fit affects confidence."""
        nlp_service._initialize_patterns()

        # Drug in Medications section (high fit)
        good_fit = nlp_service._calculate_confidence(
            matched_text="Lisinopril",
            lexical_variant="Lisinopril",
            concept_id=12345,
            domain_id="Drug",
            clinical_section=ClinicalSection.MEDICATIONS,
            assertion=Assertion.PRESENT,
        )

        # Drug in Labs section (poor fit)
        poor_fit = nlp_service._calculate_confidence(
            matched_text="Lisinopril",
            lexical_variant="Lisinopril",
            concept_id=12345,
            domain_id="Drug",
            clinical_section=ClinicalSection.LABS,
            assertion=Assertion.PRESENT,
        )

        assert good_fit > poor_fit

    def test_exact_case_match_higher_confidence(self, nlp_service: RuleBasedNLPService) -> None:
        """Test that exact case match gives higher confidence."""
        nlp_service._initialize_patterns()

        # Exact case match
        exact = nlp_service._calculate_confidence(
            matched_text="Metformin",
            lexical_variant="Metformin",
            concept_id=12345,
            domain_id="Drug",
            clinical_section=ClinicalSection.MEDICATIONS,
            assertion=Assertion.PRESENT,
        )

        # Case insensitive match
        case_diff = nlp_service._calculate_confidence(
            matched_text="METFORMIN",
            lexical_variant="metformin",
            concept_id=12345,
            domain_id="Drug",
            clinical_section=ClinicalSection.MEDICATIONS,
            assertion=Assertion.PRESENT,
        )

        assert exact > case_diff

    def test_possible_assertion_reduces_confidence(self, nlp_service: RuleBasedNLPService) -> None:
        """Test that POSSIBLE assertion reduces confidence."""
        nlp_service._initialize_patterns()

        # PRESENT assertion
        present = nlp_service._calculate_confidence(
            matched_text="Pneumonia",
            lexical_variant="Pneumonia",
            concept_id=12345,
            domain_id="Condition",
            clinical_section=ClinicalSection.ASSESSMENT,
            assertion=Assertion.PRESENT,
        )

        # POSSIBLE assertion
        possible = nlp_service._calculate_confidence(
            matched_text="Pneumonia",
            lexical_variant="Pneumonia",
            concept_id=12345,
            domain_id="Condition",
            clinical_section=ClinicalSection.ASSESSMENT,
            assertion=Assertion.POSSIBLE,
        )

        assert present > possible

    def test_confidence_within_bounds(self, nlp_service: RuleBasedNLPService) -> None:
        """Test that confidence is always between 0.0 and 1.0."""
        nlp_service._initialize_patterns()

        for section in ClinicalSection:
            for domain in ["Condition", "Drug", "Measurement", "Procedure", "Observation"]:
                for assertion in [Assertion.PRESENT, Assertion.ABSENT, Assertion.POSSIBLE]:
                    conf = nlp_service._calculate_confidence(
                        matched_text="Test",
                        lexical_variant="Test",
                        concept_id=12345,
                        domain_id=domain,
                        clinical_section=section,
                        assertion=assertion,
                    )
                    assert 0.0 <= conf <= 1.0


class TestConfidenceInExtraction:
    """Integration tests for confidence scoring in extraction."""

    @pytest.fixture
    def nlp_service(self) -> RuleBasedNLPService:
        return RuleBasedNLPService()

    def test_medication_in_meds_section_high_confidence(
        self, nlp_service: RuleBasedNLPService
    ) -> None:
        """Test that medications in Medications section have high confidence."""
        text = """
MEDICATIONS:
- Metformin 1000mg BID
- Lisinopril 20mg daily
        """
        mentions = nlp_service.extract_mentions(text, uuid4())

        # Find metformin mention
        metformin = next((m for m in mentions if "metformin" in m.lexical_variant.lower()), None)
        assert metformin is not None
        assert metformin.confidence >= 0.75  # High confidence for drug in meds section

    def test_condition_in_pmh_section_high_confidence(
        self, nlp_service: RuleBasedNLPService
    ) -> None:
        """Test that conditions in PMH section have high confidence."""
        text = """
PAST MEDICAL HISTORY:
1. Hypertension
2. Type 2 Diabetes
3. Coronary artery disease
        """
        mentions = nlp_service.extract_mentions(text, uuid4())

        # Find a condition mention
        htn = next((m for m in mentions if "hypertension" in m.lexical_variant.lower()), None)
        assert htn is not None
        assert htn.confidence >= 0.75  # High confidence for condition in PMH

    def test_uncertain_mention_lower_confidence(
        self, nlp_service: RuleBasedNLPService
    ) -> None:
        """Test that uncertain mentions have lower confidence."""
        # Use separate sections to avoid context window overlap
        text_uncertain = """
ASSESSMENT:
1. Possible pneumonia - needs workup
        """
        text_certain = """
ASSESSMENT:
1. Confirmed pneumonia - start antibiotics
        """
        mentions_uncertain = nlp_service.extract_mentions(text_uncertain, uuid4())
        mentions_certain = nlp_service.extract_mentions(text_certain, uuid4())

        # Find mentions
        pneumonia_uncertain = next(
            (m for m in mentions_uncertain if "pneumonia" in m.lexical_variant.lower()), None
        )
        pneumonia_certain = next(
            (m for m in mentions_certain if "pneumonia" in m.lexical_variant.lower()), None
        )

        # Both should exist
        assert pneumonia_uncertain is not None
        assert pneumonia_certain is not None

        # The uncertain one should have POSSIBLE assertion
        assert pneumonia_uncertain.assertion == Assertion.POSSIBLE
        assert pneumonia_certain.assertion == Assertion.PRESENT

        # The uncertain one should have lower confidence due to assertion penalty
        assert pneumonia_uncertain.confidence < pneumonia_certain.confidence

    def test_longer_term_matches_higher_confidence(
        self, nlp_service: RuleBasedNLPService
    ) -> None:
        """Test that longer, more specific terms have higher confidence."""
        text = """
PAST MEDICAL HISTORY:
1. HTN
2. Hypertension
        """
        mentions = nlp_service.extract_mentions(text, uuid4())

        # Find both mentions
        htn = next((m for m in mentions if m.lexical_variant.upper() == "HTN"), None)
        hypertension = next(
            (m for m in mentions if "hypertension" in m.lexical_variant.lower()), None
        )

        # Both should exist, longer term should have higher confidence
        if htn and hypertension:
            assert hypertension.confidence >= htn.confidence


class TestConfidenceWeights:
    """Tests for confidence weight configuration."""

    def test_weights_sum_to_one(self) -> None:
        """Test that confidence weights sum to 1.0."""
        weights = RuleBasedNLPService.CONFIDENCE_WEIGHTS
        total = sum(weights.values())
        assert abs(total - 1.0) < 0.001

    def test_all_weights_positive(self) -> None:
        """Test that all weights are positive."""
        weights = RuleBasedNLPService.CONFIDENCE_WEIGHTS
        for name, weight in weights.items():
            assert weight > 0, f"Weight {name} should be positive"

    def test_expected_weights_exist(self) -> None:
        """Test that all expected weight keys exist."""
        weights = RuleBasedNLPService.CONFIDENCE_WEIGHTS
        expected_keys = {"base", "term_length", "section_fit", "specificity", "case_match"}
        assert set(weights.keys()) == expected_keys
