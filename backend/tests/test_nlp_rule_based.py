"""Tests for rule-based NLP mention extraction."""

from uuid import uuid4

import pytest

from app.schemas.base import Assertion, Experiencer, Temporality
from app.services.nlp_rule_based import RuleBasedNLPService
from app.services.vocabulary import VocabularyService


class TestRuleBasedNLPService:
    """Tests for RuleBasedNLPService."""

    @pytest.fixture
    def vocab_service(self) -> VocabularyService:
        """Create vocabulary service for tests."""
        return VocabularyService()

    @pytest.fixture
    def nlp_service(self, vocab_service: VocabularyService) -> RuleBasedNLPService:
        """Create NLP service for tests."""
        return RuleBasedNLPService(vocab_service)

    def test_service_instantiation(self) -> None:
        """Test that service can be instantiated."""
        service = RuleBasedNLPService()
        assert service is not None

    def test_service_with_custom_vocabulary(
        self,
        vocab_service: VocabularyService,
    ) -> None:
        """Test service accepts custom vocabulary service."""
        service = RuleBasedNLPService(vocab_service)
        assert service is not None


class TestMentionExtraction:
    """Tests for basic mention extraction."""

    @pytest.fixture
    def nlp_service(self) -> RuleBasedNLPService:
        """Create NLP service for tests."""
        return RuleBasedNLPService()

    def test_extract_simple_mention(self, nlp_service: RuleBasedNLPService) -> None:
        """Test extracting a simple clinical term."""
        text = "Patient presents with fever."
        doc_id = uuid4()

        mentions = nlp_service.extract_mentions(text, doc_id)

        assert len(mentions) > 0
        fever_mention = next(
            (m for m in mentions if m.lexical_variant.lower() == "fever"),
            None,
        )
        assert fever_mention is not None
        assert fever_mention.text.lower() == "fever"

    def test_extract_multiple_mentions(self, nlp_service: RuleBasedNLPService) -> None:
        """Test extracting multiple clinical terms."""
        text = "Patient has fever and cough."
        doc_id = uuid4()

        mentions = nlp_service.extract_mentions(text, doc_id)

        lexical_variants = [m.lexical_variant.lower() for m in mentions]
        assert "fever" in lexical_variants
        assert "cough" in lexical_variants

    def test_extract_mention_offsets(self, nlp_service: RuleBasedNLPService) -> None:
        """Test that mention offsets are correct."""
        text = "Patient presents with pneumonia."
        doc_id = uuid4()

        mentions = nlp_service.extract_mentions(text, doc_id)

        pneumonia_mention = next(
            (m for m in mentions if m.lexical_variant.lower() == "pneumonia"),
            None,
        )
        assert pneumonia_mention is not None

        # Verify offsets point to correct text
        extracted_text = text[pneumonia_mention.start_offset : pneumonia_mention.end_offset]
        assert extracted_text.lower() == "pneumonia"

    def test_mentions_sorted_by_position(
        self,
        nlp_service: RuleBasedNLPService,
    ) -> None:
        """Test that mentions are sorted by position."""
        text = "Patient has cough, fever, and pneumonia."
        doc_id = uuid4()

        mentions = nlp_service.extract_mentions(text, doc_id)

        # Verify mentions are sorted by start_offset
        for i in range(len(mentions) - 1):
            assert mentions[i].start_offset <= mentions[i + 1].start_offset

    def test_case_insensitive_matching(
        self,
        nlp_service: RuleBasedNLPService,
    ) -> None:
        """Test that matching is case-insensitive."""
        text = "Patient has FEVER and Cough."
        doc_id = uuid4()

        mentions = nlp_service.extract_mentions(text, doc_id)

        lexical_variants = [m.lexical_variant.lower() for m in mentions]
        assert "fever" in lexical_variants
        assert "cough" in lexical_variants


class TestNegationDetection:
    """Tests for negation (assertion=ABSENT) detection."""

    @pytest.fixture
    def nlp_service(self) -> RuleBasedNLPService:
        """Create NLP service for tests."""
        return RuleBasedNLPService()

    def test_detect_no_negation(self, nlp_service: RuleBasedNLPService) -> None:
        """Test detection of 'no' negation."""
        text = "Patient has no fever."
        doc_id = uuid4()

        mentions = nlp_service.extract_mentions(text, doc_id)

        fever_mention = next(
            (m for m in mentions if m.lexical_variant.lower() == "fever"),
            None,
        )
        assert fever_mention is not None
        assert fever_mention.assertion == Assertion.ABSENT

    def test_detect_denies_negation(self, nlp_service: RuleBasedNLPService) -> None:
        """Test detection of 'denies' negation."""
        text = "Patient denies cough."
        doc_id = uuid4()

        mentions = nlp_service.extract_mentions(text, doc_id)

        cough_mention = next(
            (m for m in mentions if m.lexical_variant.lower() == "cough"),
            None,
        )
        assert cough_mention is not None
        assert cough_mention.assertion == Assertion.ABSENT

    def test_detect_without_negation(self, nlp_service: RuleBasedNLPService) -> None:
        """Test detection of 'without' negation."""
        text = "Patient presents without fever."
        doc_id = uuid4()

        mentions = nlp_service.extract_mentions(text, doc_id)

        fever_mention = next(
            (m for m in mentions if m.lexical_variant.lower() == "fever"),
            None,
        )
        assert fever_mention is not None
        assert fever_mention.assertion == Assertion.ABSENT

    def test_positive_mention_no_negation(
        self,
        nlp_service: RuleBasedNLPService,
    ) -> None:
        """Test that positive mentions are not marked as absent."""
        text = "Patient has fever."
        doc_id = uuid4()

        mentions = nlp_service.extract_mentions(text, doc_id)

        fever_mention = next(
            (m for m in mentions if m.lexical_variant.lower() == "fever"),
            None,
        )
        assert fever_mention is not None
        assert fever_mention.assertion == Assertion.PRESENT


class TestUncertaintyDetection:
    """Tests for uncertainty (assertion=POSSIBLE) detection."""

    @pytest.fixture
    def nlp_service(self) -> RuleBasedNLPService:
        """Create NLP service for tests."""
        return RuleBasedNLPService()

    def test_detect_possible(self, nlp_service: RuleBasedNLPService) -> None:
        """Test detection of 'possible' uncertainty."""
        text = "Patient has possible pneumonia."
        doc_id = uuid4()

        mentions = nlp_service.extract_mentions(text, doc_id)

        pneumonia_mention = next(
            (m for m in mentions if m.lexical_variant.lower() == "pneumonia"),
            None,
        )
        assert pneumonia_mention is not None
        assert pneumonia_mention.assertion == Assertion.POSSIBLE

    def test_detect_suspected(self, nlp_service: RuleBasedNLPService) -> None:
        """Test detection of 'suspected' uncertainty."""
        text = "Suspected pneumonia based on chest X-ray."
        doc_id = uuid4()

        mentions = nlp_service.extract_mentions(text, doc_id)

        pneumonia_mention = next(
            (m for m in mentions if m.lexical_variant.lower() == "pneumonia"),
            None,
        )
        assert pneumonia_mention is not None
        assert pneumonia_mention.assertion == Assertion.POSSIBLE

    def test_detect_concern_for(self, nlp_service: RuleBasedNLPService) -> None:
        """Test detection of 'concern for' uncertainty."""
        text = "Concern for congestive heart failure."
        doc_id = uuid4()

        mentions = nlp_service.extract_mentions(text, doc_id)

        chf_mention = next(
            (m for m in mentions if "heart failure" in m.lexical_variant.lower()),
            None,
        )
        assert chf_mention is not None
        assert chf_mention.assertion == Assertion.POSSIBLE


class TestTemporalityDetection:
    """Tests for temporality (CURRENT/PAST/FUTURE) detection."""

    @pytest.fixture
    def nlp_service(self) -> RuleBasedNLPService:
        """Create NLP service for tests."""
        return RuleBasedNLPService()

    def test_detect_history_of(self, nlp_service: RuleBasedNLPService) -> None:
        """Test detection of 'history of' past temporality."""
        text = "Patient has history of pneumonia."
        doc_id = uuid4()

        mentions = nlp_service.extract_mentions(text, doc_id)

        pneumonia_mention = next(
            (m for m in mentions if m.lexical_variant.lower() == "pneumonia"),
            None,
        )
        assert pneumonia_mention is not None
        assert pneumonia_mention.temporality == Temporality.PAST

    def test_detect_prior(self, nlp_service: RuleBasedNLPService) -> None:
        """Test detection of 'prior' past temporality."""
        text = "Prior hypertension diagnosis."
        doc_id = uuid4()

        mentions = nlp_service.extract_mentions(text, doc_id)

        htn_mention = next(
            (m for m in mentions if m.lexical_variant.lower() == "hypertension"),
            None,
        )
        assert htn_mention is not None
        assert htn_mention.temporality == Temporality.PAST

    def test_current_by_default(self, nlp_service: RuleBasedNLPService) -> None:
        """Test that mentions without temporal cues are CURRENT."""
        text = "Patient has fever."
        doc_id = uuid4()

        mentions = nlp_service.extract_mentions(text, doc_id)

        fever_mention = next(
            (m for m in mentions if m.lexical_variant.lower() == "fever"),
            None,
        )
        assert fever_mention is not None
        assert fever_mention.temporality == Temporality.CURRENT


class TestExperiencerDetection:
    """Tests for experiencer (PATIENT/FAMILY/OTHER) detection."""

    @pytest.fixture
    def nlp_service(self) -> RuleBasedNLPService:
        """Create NLP service for tests."""
        return RuleBasedNLPService()

    def test_detect_family_history(self, nlp_service: RuleBasedNLPService) -> None:
        """Test detection of 'family history of' experiencer."""
        text = "Family history of diabetes."
        doc_id = uuid4()

        mentions = nlp_service.extract_mentions(text, doc_id)

        # Look for any diabetes-related mention
        diabetes_mention = next(
            (m for m in mentions if "diabetes" in m.lexical_variant.lower()),
            None,
        )
        assert diabetes_mention is not None
        assert diabetes_mention.experiencer == Experiencer.FAMILY

    def test_detect_mother_has(self, nlp_service: RuleBasedNLPService) -> None:
        """Test detection of 'mother has' family experiencer."""
        text = "Mother has hypertension."
        doc_id = uuid4()

        mentions = nlp_service.extract_mentions(text, doc_id)

        htn_mention = next(
            (m for m in mentions if m.lexical_variant.lower() == "hypertension"),
            None,
        )
        assert htn_mention is not None
        assert htn_mention.experiencer == Experiencer.FAMILY

    def test_patient_by_default(self, nlp_service: RuleBasedNLPService) -> None:
        """Test that mentions without family cues are PATIENT."""
        text = "Patient has hypertension."
        doc_id = uuid4()

        mentions = nlp_service.extract_mentions(text, doc_id)

        htn_mention = next(
            (m for m in mentions if m.lexical_variant.lower() == "hypertension"),
            None,
        )
        assert htn_mention is not None
        assert htn_mention.experiencer == Experiencer.PATIENT


class TestRuleBasedNLPExports:
    """Tests for module exports."""

    def test_rule_based_service_exported(self) -> None:
        """Test that RuleBasedNLPService is exported from services."""
        from app.services import RuleBasedNLPService

        assert RuleBasedNLPService is not None
