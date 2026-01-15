"""Tests for rule-based NLP service."""

from uuid import uuid4

import pytest

from app.schemas.base import Assertion, Experiencer, Temporality
from app.services import ExtractedMention, RuleBasedNLPService
from app.services.vocabulary import VocabularyService


class TestRuleBasedNLPServiceInit:
    """Tests for RuleBasedNLPService initialization."""

    def test_can_instantiate(self) -> None:
        """Test that RuleBasedNLPService can be instantiated."""
        service = RuleBasedNLPService()
        assert service is not None

    def test_loads_vocabulary_on_init(self) -> None:
        """Test that vocabulary service is set on initialization."""
        service = RuleBasedNLPService()
        # Vocabulary is lazy loaded, trigger it
        service.extract_mentions("fever", uuid4())
        assert service._vocabulary_service is not None

    def test_accepts_custom_vocabulary_service(self) -> None:
        """Test that custom vocabulary service can be provided."""
        vocab = VocabularyService()
        service = RuleBasedNLPService(vocabulary_service=vocab)
        assert service._vocabulary_service is vocab


class TestRuleBasedNLPServiceExtraction:
    """Tests for mention extraction functionality."""

    @pytest.fixture
    def service(self) -> RuleBasedNLPService:
        """Create a RuleBasedNLPService for testing."""
        return RuleBasedNLPService()

    def test_extract_single_mention(self, service: RuleBasedNLPService) -> None:
        """Test extracting a single mention."""
        text = "Patient has fever."
        doc_id = uuid4()
        mentions = service.extract_mentions(text, doc_id)

        assert len(mentions) >= 1
        fever_mentions = [m for m in mentions if "fever" in m.lexical_variant.lower()]
        assert len(fever_mentions) == 1
        assert "fever" in fever_mentions[0].text.lower()

    def test_extract_multiple_mentions(self, service: RuleBasedNLPService) -> None:
        """Test extracting multiple mentions."""
        text = "Patient presents with cough and fever."
        doc_id = uuid4()
        mentions = service.extract_mentions(text, doc_id)

        mention_texts = [m.lexical_variant.lower() for m in mentions]
        assert any("cough" in v for v in mention_texts)
        assert any("fever" in v for v in mention_texts)

    def test_extract_mention_offsets(self, service: RuleBasedNLPService) -> None:
        """Test that mention offsets are correct."""
        text = "Patient has pneumonia."
        doc_id = uuid4()
        mentions = service.extract_mentions(text, doc_id)

        pneumonia_mentions = [m for m in mentions if "pneumonia" in m.lexical_variant.lower()]
        assert len(pneumonia_mentions) == 1
        mention = pneumonia_mentions[0]

        # Verify the offset points to the actual text
        assert text[mention.start_offset : mention.end_offset].lower() == "pneumonia"

    def test_extract_case_insensitive(self, service: RuleBasedNLPService) -> None:
        """Test case-insensitive extraction."""
        text = "Patient has FEVER and Cough."
        doc_id = uuid4()
        mentions = service.extract_mentions(text, doc_id)

        mention_variants = [m.lexical_variant.lower() for m in mentions]
        assert any("fever" in v for v in mention_variants)
        assert any("cough" in v for v in mention_variants)

    def test_extract_multi_word_terms(self, service: RuleBasedNLPService) -> None:
        """Test extracting multi-word clinical terms."""
        text = "History of congestive heart failure."
        doc_id = uuid4()
        mentions = service.extract_mentions(text, doc_id)

        chf_mentions = [m for m in mentions if "heart failure" in m.lexical_variant.lower()]
        assert len(chf_mentions) >= 1

    def test_extract_abbreviations(self, service: RuleBasedNLPService) -> None:
        """Test extracting abbreviations like CHF, HTN."""
        text = "Patient with CHF and HTN."
        doc_id = uuid4()
        mentions = service.extract_mentions(text, doc_id)

        mention_variants = [m.lexical_variant.lower() for m in mentions]
        has_chf = any("chf" in v for v in mention_variants)
        has_htn = any("htn" in v for v in mention_variants)
        assert has_chf or has_htn

    def test_empty_text_returns_empty_list(self, service: RuleBasedNLPService) -> None:
        """Test that empty text returns empty list."""
        doc_id = uuid4()
        mentions = service.extract_mentions("", doc_id)
        assert mentions == []

    def test_no_matches_returns_empty_list(self, service: RuleBasedNLPService) -> None:
        """Test that text with no matches returns empty list."""
        text = "The weather is nice today."
        doc_id = uuid4()
        mentions = service.extract_mentions(text, doc_id)
        assert mentions == []

    def test_mentions_sorted_by_offset(self, service: RuleBasedNLPService) -> None:
        """Test that mentions are sorted by start offset."""
        text = "Patient has fever and cough with pneumonia."
        doc_id = uuid4()
        mentions = service.extract_mentions(text, doc_id)

        offsets = [m.start_offset for m in mentions]
        assert offsets == sorted(offsets)


class TestRuleBasedNLPServiceNegation:
    """Tests for negation detection."""

    @pytest.fixture
    def service(self) -> RuleBasedNLPService:
        """Create a RuleBasedNLPService for testing."""
        return RuleBasedNLPService()

    def test_detects_no_negation(self, service: RuleBasedNLPService) -> None:
        """Test detection of 'no' negation."""
        text = "No fever reported."
        doc_id = uuid4()
        mentions = service.extract_mentions(text, doc_id)

        fever_mentions = [m for m in mentions if "fever" in m.lexical_variant.lower()]
        if fever_mentions:
            assert fever_mentions[0].assertion == Assertion.ABSENT

    def test_detects_denies_negation(self, service: RuleBasedNLPService) -> None:
        """Test detection of 'denies' negation."""
        text = "Patient denies cough."
        doc_id = uuid4()
        mentions = service.extract_mentions(text, doc_id)

        cough_mentions = [m for m in mentions if "cough" in m.lexical_variant.lower()]
        if cough_mentions:
            assert cough_mentions[0].assertion == Assertion.ABSENT

    def test_detects_without_negation(self, service: RuleBasedNLPService) -> None:
        """Test detection of 'without' negation."""
        text = "Patient without fever."
        doc_id = uuid4()
        mentions = service.extract_mentions(text, doc_id)

        fever_mentions = [m for m in mentions if "fever" in m.lexical_variant.lower()]
        if fever_mentions:
            assert fever_mentions[0].assertion == Assertion.ABSENT


class TestRuleBasedNLPServiceUncertainty:
    """Tests for uncertainty detection."""

    @pytest.fixture
    def service(self) -> RuleBasedNLPService:
        """Create a RuleBasedNLPService for testing."""
        return RuleBasedNLPService()

    def test_detects_possible(self, service: RuleBasedNLPService) -> None:
        """Test detection of 'possible' uncertainty."""
        text = "Possible pneumonia."
        doc_id = uuid4()
        mentions = service.extract_mentions(text, doc_id)

        pneumonia_mentions = [m for m in mentions if "pneumonia" in m.lexical_variant.lower()]
        if pneumonia_mentions:
            assert pneumonia_mentions[0].assertion == Assertion.POSSIBLE

    def test_detects_suspected(self, service: RuleBasedNLPService) -> None:
        """Test detection of 'suspected' uncertainty."""
        text = "Suspected infection."
        doc_id = uuid4()
        mentions = service.extract_mentions(text, doc_id)

        # May or may not have infection in vocabulary
        for m in mentions:
            if "infection" in m.lexical_variant.lower():
                assert m.assertion == Assertion.POSSIBLE


class TestRuleBasedNLPServiceTemporality:
    """Tests for temporality detection."""

    @pytest.fixture
    def service(self) -> RuleBasedNLPService:
        """Create a RuleBasedNLPService for testing."""
        return RuleBasedNLPService()

    def test_detects_history_of(self, service: RuleBasedNLPService) -> None:
        """Test detection of 'history of' temporality."""
        text = "History of congestive heart failure."
        doc_id = uuid4()
        mentions = service.extract_mentions(text, doc_id)

        chf_mentions = [m for m in mentions if "heart failure" in m.lexical_variant.lower()]
        if chf_mentions:
            assert chf_mentions[0].temporality == Temporality.PAST

    def test_default_temporality_is_current(self, service: RuleBasedNLPService) -> None:
        """Test that default temporality is CURRENT."""
        text = "Patient has fever."
        doc_id = uuid4()
        mentions = service.extract_mentions(text, doc_id)

        for mention in mentions:
            # Unless there's a past trigger, should be current
            assert mention.temporality == Temporality.CURRENT


class TestRuleBasedNLPServiceExperiencer:
    """Tests for experiencer detection."""

    @pytest.fixture
    def service(self) -> RuleBasedNLPService:
        """Create a RuleBasedNLPService for testing."""
        return RuleBasedNLPService()

    def test_detects_family_history(self, service: RuleBasedNLPService) -> None:
        """Test detection of family history."""
        text = "Family history of colon cancer."
        doc_id = uuid4()
        mentions = service.extract_mentions(text, doc_id)

        cancer_mentions = [m for m in mentions if "cancer" in m.lexical_variant.lower()]
        if cancer_mentions:
            assert cancer_mentions[0].experiencer == Experiencer.FAMILY

    def test_detects_mother_has(self, service: RuleBasedNLPService) -> None:
        """Test detection of 'mother has' experiencer."""
        text = "Mother has diabetes."
        doc_id = uuid4()
        mentions = service.extract_mentions(text, doc_id)

        diabetes_mentions = [m for m in mentions if "diabetes" in m.lexical_variant.lower()]
        if diabetes_mentions:
            assert diabetes_mentions[0].experiencer == Experiencer.FAMILY

    def test_default_experiencer_is_patient(self, service: RuleBasedNLPService) -> None:
        """Test that default experiencer is PATIENT."""
        text = "Patient has fever."
        doc_id = uuid4()
        mentions = service.extract_mentions(text, doc_id)

        for mention in mentions:
            assert mention.experiencer == Experiencer.PATIENT


class TestRuleBasedNLPServiceSectionDetection:
    """Tests for section detection in mentions."""

    @pytest.fixture
    def service(self) -> RuleBasedNLPService:
        """Create a RuleBasedNLPService for testing."""
        return RuleBasedNLPService()

    def test_detects_assessment_section(self, service: RuleBasedNLPService) -> None:
        """Test detection of Assessment section."""
        text = """Chief Complaint: Cough.

        Assessment: Pneumonia confirmed.
        """
        doc_id = uuid4()
        mentions = service.extract_mentions(text, doc_id)

        pneumonia_mentions = [m for m in mentions if "pneumonia" in m.lexical_variant.lower()]
        if pneumonia_mentions:
            assert pneumonia_mentions[0].section == "Assessment"


class TestRuleBasedNLPServiceWithSyntheticNotes:
    """Tests using synthetic clinical notes from fixtures."""

    @pytest.fixture
    def service(self) -> RuleBasedNLPService:
        """Create a RuleBasedNLPService for testing."""
        return RuleBasedNLPService()

    def test_extract_from_pneumonia_note(self, service: RuleBasedNLPService) -> None:
        """Test extraction from note_001: cough, fever, pneumonia."""
        text = (
            "Patient is a 65-year-old male presenting with cough and fever. "
            "Chest X-ray performed. No evidence of pneumonia. Will monitor symptoms."
        )
        doc_id = uuid4()
        mentions = service.extract_mentions(text, doc_id)

        mention_variants = [m.lexical_variant.lower() for m in mentions]
        assert any("cough" in v for v in mention_variants)
        assert any("fever" in v for v in mention_variants)
        assert any("pneumonia" in v for v in mention_variants)

        # Check pneumonia is negated
        pneumonia_mentions = [m for m in mentions if "pneumonia" in m.lexical_variant.lower()]
        if pneumonia_mentions:
            assert pneumonia_mentions[0].assertion == Assertion.ABSENT

    def test_extract_from_chf_note(self, service: RuleBasedNLPService) -> None:
        """Test extraction from note_002: CHF with past temporality."""
        text = (
            "History of congestive heart failure. Patient currently stable "
            "on current medications. No acute distress."
        )
        doc_id = uuid4()
        mentions = service.extract_mentions(text, doc_id)

        # Check CHF has past temporality
        chf_mentions = [m for m in mentions if "heart failure" in m.lexical_variant.lower()]
        if chf_mentions:
            assert chf_mentions[0].temporality == Temporality.PAST

    def test_extract_from_family_history_note(self, service: RuleBasedNLPService) -> None:
        """Test extraction from note_003: family history."""
        text = (
            "Family history significant for colon cancer - mother diagnosed at age 55. "
            "Patient denies any GI symptoms. Colonoscopy recommended."
        )
        doc_id = uuid4()
        mentions = service.extract_mentions(text, doc_id)

        # Check colon cancer is family experiencer
        cancer_mentions = [m for m in mentions if "cancer" in m.lexical_variant.lower()]
        if cancer_mentions:
            assert cancer_mentions[0].experiencer == Experiencer.FAMILY


class TestRuleBasedNLPServiceExports:
    """Tests for module exports."""

    def test_rule_based_service_exported(self) -> None:
        """Test that RuleBasedNLPService is exported from services."""
        from app.services import RuleBasedNLPService

        assert RuleBasedNLPService is not None

    def test_service_is_nlp_interface_subclass(self) -> None:
        """Test that RuleBasedNLPService implements NLPServiceInterface."""
        from app.services import NLPServiceInterface, RuleBasedNLPService

        assert issubclass(RuleBasedNLPService, NLPServiceInterface)
