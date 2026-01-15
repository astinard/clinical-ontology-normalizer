"""Tests for NLP service interface."""

from uuid import uuid4

import pytest

from app.schemas.base import Assertion, Experiencer, Temporality
from app.services import BaseNLPService, ExtractedMention, NLPServiceInterface


class TestExtractedMention:
    """Tests for ExtractedMention dataclass."""

    def test_create_mention(self) -> None:
        """Test creating an ExtractedMention with required fields."""
        mention = ExtractedMention(
            text="pneumonia",
            start_offset=10,
            end_offset=19,
            lexical_variant="pneumonia",
        )
        assert mention.text == "pneumonia"
        assert mention.start_offset == 10
        assert mention.end_offset == 19
        assert mention.lexical_variant == "pneumonia"

    def test_default_values(self) -> None:
        """Test default values for optional fields."""
        mention = ExtractedMention(
            text="fever",
            start_offset=0,
            end_offset=5,
            lexical_variant="fever",
        )
        assert mention.section is None
        assert mention.assertion == Assertion.PRESENT
        assert mention.temporality == Temporality.CURRENT
        assert mention.experiencer == Experiencer.PATIENT
        assert mention.confidence == 1.0

    def test_custom_values(self) -> None:
        """Test custom values for all fields."""
        mention = ExtractedMention(
            text="denies chest pain",
            start_offset=50,
            end_offset=67,
            lexical_variant="chest pain",
            section="Review of Systems",
            assertion=Assertion.ABSENT,
            temporality=Temporality.CURRENT,
            experiencer=Experiencer.PATIENT,
            confidence=0.95,
        )
        assert mention.assertion == Assertion.ABSENT
        assert mention.section == "Review of Systems"
        assert mention.confidence == 0.95

    def test_is_negated_true(self) -> None:
        """Test is_negated property when assertion is ABSENT."""
        mention = ExtractedMention(
            text="no fever",
            start_offset=0,
            end_offset=8,
            lexical_variant="fever",
            assertion=Assertion.ABSENT,
        )
        assert mention.is_negated is True

    def test_is_negated_false(self) -> None:
        """Test is_negated property when assertion is PRESENT."""
        mention = ExtractedMention(
            text="fever",
            start_offset=0,
            end_offset=5,
            lexical_variant="fever",
            assertion=Assertion.PRESENT,
        )
        assert mention.is_negated is False

    def test_is_uncertain_true(self) -> None:
        """Test is_uncertain property when assertion is POSSIBLE."""
        mention = ExtractedMention(
            text="possible pneumonia",
            start_offset=0,
            end_offset=18,
            lexical_variant="pneumonia",
            assertion=Assertion.POSSIBLE,
        )
        assert mention.is_uncertain is True

    def test_is_uncertain_false(self) -> None:
        """Test is_uncertain property when assertion is PRESENT."""
        mention = ExtractedMention(
            text="pneumonia",
            start_offset=0,
            end_offset=9,
            lexical_variant="pneumonia",
            assertion=Assertion.PRESENT,
        )
        assert mention.is_uncertain is False

    def test_is_family_history_true(self) -> None:
        """Test is_family_history property when experiencer is FAMILY."""
        mention = ExtractedMention(
            text="mother had diabetes",
            start_offset=0,
            end_offset=19,
            lexical_variant="diabetes",
            experiencer=Experiencer.FAMILY,
        )
        assert mention.is_family_history is True

    def test_is_family_history_false(self) -> None:
        """Test is_family_history property when experiencer is PATIENT."""
        mention = ExtractedMention(
            text="diabetes",
            start_offset=0,
            end_offset=8,
            lexical_variant="diabetes",
            experiencer=Experiencer.PATIENT,
        )
        assert mention.is_family_history is False


class TestNLPServiceInterface:
    """Tests for NLPServiceInterface abstract class."""

    def test_interface_is_abstract(self) -> None:
        """Test that NLPServiceInterface cannot be instantiated directly."""
        with pytest.raises(TypeError):
            NLPServiceInterface()  # type: ignore[abstract]

    def test_extract_mentions_is_abstract(self) -> None:
        """Test that extract_mentions is an abstract method."""
        import inspect

        assert inspect.isabstract(NLPServiceInterface)

    def test_concrete_implementation_required(self) -> None:
        """Test that a concrete implementation must implement extract_mentions."""

        class IncompleteService(NLPServiceInterface):
            pass

        with pytest.raises(TypeError):
            IncompleteService()  # type: ignore[abstract]


class TestBaseNLPService:
    """Tests for BaseNLPService base class."""

    def test_can_instantiate(self) -> None:
        """Test that BaseNLPService can be instantiated."""
        service = BaseNLPService()
        assert service is not None

    def test_extract_mentions_returns_empty_list(self) -> None:
        """Test that default extract_mentions returns empty list."""
        service = BaseNLPService()
        doc_id = uuid4()
        result = service.extract_mentions("Test text", doc_id)
        assert result == []

    def test_normalize_text_removes_extra_whitespace(self) -> None:
        """Test normalize_text removes multiple whitespaces."""
        service = BaseNLPService()
        text = "Patient   has    fever   and   cough."
        result = service.normalize_text(text)
        assert result == "Patient has fever and cough."

    def test_normalize_text_strips_ends(self) -> None:
        """Test normalize_text strips leading and trailing whitespace."""
        service = BaseNLPService()
        text = "  Patient has fever.  "
        result = service.normalize_text(text)
        assert result == "Patient has fever."

    def test_normalize_text_handles_newlines(self) -> None:
        """Test normalize_text normalizes newlines and tabs."""
        service = BaseNLPService()
        text = "Patient\nhas\tfever."
        result = service.normalize_text(text)
        assert result == "Patient has fever."

    def test_get_section_name_finds_section(self) -> None:
        """Test get_section_name identifies section headers."""
        service = BaseNLPService()
        text = """Chief Complaint: Fever for 3 days.

        History of Present Illness: Patient is a 45 year old male with fever.

        Assessment: Viral syndrome.
        """
        # Offset in HPI section
        offset = 80
        result = service.get_section_name(text, offset)
        assert result == "History of Present Illness"

    def test_get_section_name_finds_assessment(self) -> None:
        """Test get_section_name finds Assessment section."""
        service = BaseNLPService()
        text = """Chief Complaint: Fever.

        Assessment: Pneumonia.

        Plan: Antibiotics.
        """
        # Find offset in Assessment section (after "Assessment:" but before "Plan")
        offset = text.find("Pneumonia")
        result = service.get_section_name(text, offset)
        assert result == "Assessment"

    def test_get_section_name_returns_none_for_start(self) -> None:
        """Test get_section_name returns None before any section header."""
        service = BaseNLPService()
        text = "Patient presents with fever."
        result = service.get_section_name(text, 10)
        assert result is None

    def test_get_section_name_handles_abbreviations(self) -> None:
        """Test get_section_name handles common abbreviations."""
        service = BaseNLPService()
        text = """CC: Fever.
        HPI: Patient has fever for 3 days.
        PMH: Hypertension.
        """
        # Find offset in HPI section (after "HPI:" but before "PMH")
        offset = text.find("Patient has fever")
        result = service.get_section_name(text, offset)
        assert result == "HPI"


class TestNLPServiceExports:
    """Tests for NLP service module exports."""

    def test_nlp_interface_exported(self) -> None:
        """Test that NLPServiceInterface is exported from services."""
        from app.services import NLPServiceInterface

        assert NLPServiceInterface is not None

    def test_base_nlp_service_exported(self) -> None:
        """Test that BaseNLPService is exported from services."""
        from app.services import BaseNLPService

        assert BaseNLPService is not None

    def test_extracted_mention_exported(self) -> None:
        """Test that ExtractedMention is exported from services."""
        from app.services import ExtractedMention

        assert ExtractedMention is not None
