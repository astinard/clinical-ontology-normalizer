"""Tests for clinical note section parser."""

from uuid import uuid4

import pytest

from app.services.section_parser import (
    ClinicalSection,
    SectionParser,
    SectionSpan,
    get_section_parser,
)
from app.services.nlp_rule_based import RuleBasedNLPService


class TestSectionParser:
    """Tests for SectionParser basic functionality."""

    @pytest.fixture
    def parser(self) -> SectionParser:
        """Create a section parser."""
        return SectionParser()

    def test_parser_instantiation(self, parser: SectionParser) -> None:
        """Test parser can be instantiated."""
        assert parser is not None

    def test_parse_empty_text(self, parser: SectionParser) -> None:
        """Test parsing empty text returns empty list."""
        sections = parser.parse("")
        assert sections == []

    def test_parse_no_sections(self, parser: SectionParser) -> None:
        """Test parsing text without section headers."""
        text = "Patient presents with chest pain and shortness of breath."
        sections = parser.parse(text)
        assert sections == []


class TestSectionDetection:
    """Tests for detecting various section headers."""

    @pytest.fixture
    def parser(self) -> SectionParser:
        return SectionParser()

    def test_detect_chief_complaint(self, parser: SectionParser) -> None:
        """Test detecting Chief Complaint section."""
        text = "CHIEF COMPLAINT: Chest pain\n\nHPI: Patient reports..."
        sections = parser.parse(text)
        assert len(sections) >= 1
        assert sections[0].section == ClinicalSection.CHIEF_COMPLAINT

    def test_detect_cc_abbreviation(self, parser: SectionParser) -> None:
        """Test detecting CC abbreviation for Chief Complaint."""
        text = "CC: Shortness of breath\n\nThe patient is a 65 yo male..."
        sections = parser.parse(text)
        assert len(sections) >= 1
        assert sections[0].section == ClinicalSection.CHIEF_COMPLAINT

    def test_detect_hpi(self, parser: SectionParser) -> None:
        """Test detecting History of Present Illness."""
        text = "HISTORY OF PRESENT ILLNESS:\nPatient reports 3 days of symptoms."
        sections = parser.parse(text)
        assert len(sections) >= 1
        assert sections[0].section == ClinicalSection.HPI

    def test_detect_hpi_abbreviation(self, parser: SectionParser) -> None:
        """Test detecting HPI abbreviation."""
        text = "HPI: Patient is a 72 year old female..."
        sections = parser.parse(text)
        assert len(sections) >= 1
        assert sections[0].section == ClinicalSection.HPI

    def test_detect_past_medical_history(self, parser: SectionParser) -> None:
        """Test detecting Past Medical History."""
        text = "PAST MEDICAL HISTORY:\n1. Hypertension\n2. Diabetes"
        sections = parser.parse(text)
        assert len(sections) >= 1
        assert sections[0].section == ClinicalSection.PAST_MEDICAL_HISTORY

    def test_detect_pmh_abbreviation(self, parser: SectionParser) -> None:
        """Test detecting PMH abbreviation."""
        text = "PMH: HTN, DM2, CAD s/p CABG"
        sections = parser.parse(text)
        assert len(sections) >= 1
        assert sections[0].section == ClinicalSection.PAST_MEDICAL_HISTORY

    def test_detect_medications(self, parser: SectionParser) -> None:
        """Test detecting Medications section."""
        text = "MEDICATIONS:\n- Metformin 1000mg BID\n- Lisinopril 10mg daily"
        sections = parser.parse(text)
        assert len(sections) >= 1
        assert sections[0].section == ClinicalSection.MEDICATIONS

    def test_detect_allergies(self, parser: SectionParser) -> None:
        """Test detecting Allergies section."""
        text = "ALLERGIES: Penicillin (rash)"
        sections = parser.parse(text)
        assert len(sections) >= 1
        assert sections[0].section == ClinicalSection.ALLERGIES

    def test_detect_physical_exam(self, parser: SectionParser) -> None:
        """Test detecting Physical Exam section."""
        text = "PHYSICAL EXAM:\nGeneral: Alert, no acute distress"
        sections = parser.parse(text)
        assert len(sections) >= 1
        assert sections[0].section == ClinicalSection.PHYSICAL_EXAM

    def test_detect_labs(self, parser: SectionParser) -> None:
        """Test detecting Labs section."""
        text = "LABS:\nWBC 8.5, Hgb 12.4, Plt 250"
        sections = parser.parse(text)
        assert len(sections) >= 1
        assert sections[0].section == ClinicalSection.LABS

    def test_detect_assessment_plan(self, parser: SectionParser) -> None:
        """Test detecting Assessment and Plan combined."""
        text = "ASSESSMENT AND PLAN:\n1. CHF exacerbation - diuresis"
        sections = parser.parse(text)
        assert len(sections) >= 1
        assert sections[0].section == ClinicalSection.ASSESSMENT_PLAN

    def test_detect_ap_abbreviation(self, parser: SectionParser) -> None:
        """Test detecting A/P abbreviation."""
        text = "A/P:\n1. Pneumonia - antibiotics"
        sections = parser.parse(text)
        assert len(sections) >= 1
        assert sections[0].section == ClinicalSection.ASSESSMENT_PLAN


class TestMultipleSections:
    """Tests for parsing multiple sections."""

    @pytest.fixture
    def parser(self) -> SectionParser:
        return SectionParser()

    def test_parse_multiple_sections(self, parser: SectionParser) -> None:
        """Test parsing text with multiple sections."""
        text = """
CHIEF COMPLAINT: Chest pain

HPI: 65 yo male with history of CAD presents with chest pain.

PAST MEDICAL HISTORY:
1. CAD s/p CABG 2019
2. HTN
3. DM2

MEDICATIONS:
- Aspirin 81mg
- Metoprolol 50mg BID

ASSESSMENT/PLAN:
1. Chest pain - rule out ACS
        """
        sections = parser.parse(text)

        # Should find at least 5 sections
        assert len(sections) >= 5

        # Verify section order
        section_types = [s.section for s in sections]
        assert ClinicalSection.CHIEF_COMPLAINT in section_types
        assert ClinicalSection.HPI in section_types
        assert ClinicalSection.PAST_MEDICAL_HISTORY in section_types
        assert ClinicalSection.MEDICATIONS in section_types
        assert ClinicalSection.ASSESSMENT_PLAN in section_types

    def test_section_boundaries(self, parser: SectionParser) -> None:
        """Test that section end boundaries are correct."""
        text = "HPI: First text here.\n\nPMH: Second text here."
        sections = parser.parse(text)

        assert len(sections) == 2
        # First section should end where second begins
        assert sections[0].end == sections[1].start


class TestSectionAtOffset:
    """Tests for getting section at specific offset."""

    @pytest.fixture
    def parser(self) -> SectionParser:
        return SectionParser()

    def test_get_section_at_start(self, parser: SectionParser) -> None:
        """Test getting section at document start."""
        text = "HPI: Patient presents with chest pain."
        section = parser.get_section_at(text, 5)
        assert section == ClinicalSection.HPI

    def test_get_section_at_middle(self, parser: SectionParser) -> None:
        """Test getting section in middle of document."""
        text = "HPI: First.\n\nPMH: Second.\n\nMEDICATIONS: Third."
        # Offset in PMH section
        pmh_start = text.find("PMH")
        section = parser.get_section_at(text, pmh_start + 10)
        assert section == ClinicalSection.PAST_MEDICAL_HISTORY

    def test_unknown_section_before_first_header(self, parser: SectionParser) -> None:
        """Test that text before first header returns UNKNOWN."""
        text = "Some intro text.\n\nHPI: Patient presents..."
        section = parser.get_section_at(text, 5)
        assert section == ClinicalSection.UNKNOWN


class TestDomainAffinity:
    """Tests for section-domain affinity scoring."""

    @pytest.fixture
    def parser(self) -> SectionParser:
        return SectionParser()

    def test_medications_drug_affinity(self, parser: SectionParser) -> None:
        """Test high affinity for drugs in medications section."""
        affinity = parser.get_domain_affinity(ClinicalSection.MEDICATIONS, "Drug")
        assert affinity == 1.0

    def test_medications_condition_affinity(self, parser: SectionParser) -> None:
        """Test low affinity for conditions in medications section."""
        affinity = parser.get_domain_affinity(ClinicalSection.MEDICATIONS, "Condition")
        assert affinity < 0.5

    def test_pmh_condition_affinity(self, parser: SectionParser) -> None:
        """Test high affinity for conditions in PMH section."""
        affinity = parser.get_domain_affinity(
            ClinicalSection.PAST_MEDICAL_HISTORY, "Condition"
        )
        assert affinity == 1.0

    def test_labs_measurement_affinity(self, parser: SectionParser) -> None:
        """Test high affinity for measurements in labs section."""
        affinity = parser.get_domain_affinity(ClinicalSection.LABS, "Measurement")
        assert affinity == 1.0


class TestConfidenceModifier:
    """Tests for confidence modifier calculation."""

    @pytest.fixture
    def parser(self) -> SectionParser:
        return SectionParser()

    def test_high_affinity_boosts_confidence(self, parser: SectionParser) -> None:
        """Test that high affinity boosts confidence."""
        modifier = parser.calculate_confidence_modifier(
            ClinicalSection.MEDICATIONS, "Drug"
        )
        assert modifier >= 1.0

    def test_low_affinity_reduces_confidence(self, parser: SectionParser) -> None:
        """Test that low affinity reduces confidence."""
        modifier = parser.calculate_confidence_modifier(
            ClinicalSection.MEDICATIONS, "Condition"
        )
        assert modifier < 1.0

    def test_modifier_within_bounds(self, parser: SectionParser) -> None:
        """Test that modifiers stay within expected bounds."""
        for section in ClinicalSection:
            for domain in ["Condition", "Drug", "Measurement", "Procedure", "Observation"]:
                modifier = parser.calculate_confidence_modifier(section, domain)
                assert 0.8 <= modifier <= 1.1


class TestSingletonParser:
    """Tests for singleton parser instance."""

    def test_singleton_returns_same_instance(self) -> None:
        """Test that get_section_parser returns same instance."""
        parser1 = get_section_parser()
        parser2 = get_section_parser()
        assert parser1 is parser2


class TestSectionAwareExtraction:
    """Integration tests for section-aware NLP extraction."""

    @pytest.fixture
    def nlp_service(self) -> RuleBasedNLPService:
        return RuleBasedNLPService()

    def test_medication_in_medications_section(self, nlp_service: RuleBasedNLPService) -> None:
        """Test medication extraction in Medications section has high confidence."""
        text = """
MEDICATIONS:
- Metformin 1000mg BID
- Lisinopril 20mg daily
        """
        mentions = nlp_service.extract_mentions(text, uuid4())

        # Find metformin mention
        metformin = next((m for m in mentions if "metformin" in m.lexical_variant.lower()), None)
        assert metformin is not None
        assert metformin.section == "Medications"
        # Confidence should be boosted for drug in medications section
        assert metformin.confidence >= 0.8

    def test_condition_in_pmh_section(self, nlp_service: RuleBasedNLPService) -> None:
        """Test condition extraction in PMH section has high confidence."""
        text = """
PAST MEDICAL HISTORY:
1. Hypertension
2. Type 2 Diabetes
3. CAD with prior CABG
        """
        mentions = nlp_service.extract_mentions(text, uuid4())

        # Find CAD mention
        cad = next((m for m in mentions if "cad" in m.lexical_variant.lower()), None)
        assert cad is not None
        assert cad.section == "Past Medical History"
        # Confidence should be boosted for condition in PMH
        assert cad.confidence >= 0.8

    def test_section_detection_in_full_note(self, nlp_service: RuleBasedNLPService) -> None:
        """Test section detection across a full clinical note."""
        text = """
CHIEF COMPLAINT: Shortness of breath

HPI: 64 yo male with HFrEF presents with dyspnea.

PAST MEDICAL HISTORY:
1. HFrEF
2. CKD stage 4
3. HTN

MEDICATIONS:
- Furosemide 80mg BID
- Carvedilol 25mg BID

LABS:
BNP 1850, Cr 3.8

ASSESSMENT/PLAN:
1. CHF exacerbation - IV Lasix
        """
        mentions = nlp_service.extract_mentions(text, uuid4())

        # Verify sections are properly detected
        sections_found = set(m.section for m in mentions if m.section)

        # Should have mentions from multiple sections
        assert len(sections_found) >= 3

    def test_family_history_section_affects_experiencer(self, nlp_service: RuleBasedNLPService) -> None:
        """Test that mentions in Family History section are handled correctly."""
        text = """
FAMILY HISTORY:
Mother with HTN and DM2
Father died of MI at age 55
        """
        mentions = nlp_service.extract_mentions(text, uuid4())

        # Find HTN mention
        htn = next((m for m in mentions if "htn" in m.lexical_variant.lower()), None)
        assert htn is not None
        assert htn.section == "Family History"
