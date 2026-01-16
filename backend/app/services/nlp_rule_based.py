"""Rule-based NLP service for clinical mention extraction.

Uses regex patterns and vocabulary lookups to extract mentions
from clinical documents.
"""

import logging
import os
import re
from typing import Protocol
from uuid import UUID

from app.schemas.base import Assertion, Experiencer, Temporality
from app.services.nlp import BaseNLPService, ExtractedMention
from app.services.vocabulary import VocabularyService

logger = logging.getLogger(__name__)


class VocabularyServiceProtocol(Protocol):
    """Protocol for vocabulary services (file-based or database-backed)."""

    @property
    def concepts(self) -> list: ...

    def load(self) -> None: ...


class RuleBasedNLPService(BaseNLPService):
    """Rule-based mention extractor using regex and vocabulary matching.

    This service extracts clinical mentions by:
    1. Searching for known clinical terms from the vocabulary
    2. Using regex patterns to identify common clinical patterns
    3. Applying context rules for negation, temporality, and experiencer

    By default, uses database-backed vocabulary if USE_DB_VOCABULARY=true
    environment variable is set, otherwise falls back to file-based fixture.

    Usage:
        nlp = RuleBasedNLPService()
        mentions = nlp.extract_mentions(document.text, document.id)

        # Or with explicit vocabulary service:
        vocab = VocabularyService()
        nlp = RuleBasedNLPService(vocab)
    """

    # Stopwords - common English words that should NOT be extracted as clinical terms
    # These may exist as concepts in OMOP but create noise when extracted from text
    STOPWORDS = {
        # Common English words
        "a", "an", "the", "is", "are", "was", "were", "be", "been",
        "or", "and", "but", "if", "then", "so", "as", "at", "by", "for",
        "from", "in", "into", "of", "on", "to", "with", "without",
        "yes", "no", "not", "can", "will", "may", "has", "had", "have",
        "all", "any", "some", "one", "two", "per", "mg", "ml",
        # Common medical/clinical words that are too generic
        "air",      # RxNorm Ingredient - creates false positives from "room air"
        "water",    # Too common
        "normal",   # Too generic - "within normal limits"
        "stable",   # Too generic - "vitals stable"
        "pain",     # Too generic without context
        "use",      # From "use of"
        "day",      # Too common
        "time",     # Too common
        "room",     # Too common
        "well",     # Too common - "patient doing well"
        "new",      # Too common
        "old",      # Too common
        "left",     # Too ambiguous without body site context
        "right",    # Too ambiguous without body site context
        "patient",  # Too common
    }

    # Minimum term length to extract (helps reduce noise)
    MIN_TERM_LENGTH = 2

    # Common patterns for clinical terms not in vocabulary
    CLINICAL_PATTERNS = [
        # Vital signs with values
        r"(?:temperature|temp)\s*(?:of\s*)?([\d.]+)\s*(?:°?[FC])?",
        r"(?:blood pressure|bp)\s*(?:of\s*)?(\d+/\d+)\s*(?:mmHg)?",
        r"(?:heart rate|hr|pulse)\s*(?:of\s*)?(\d+)\s*(?:bpm)?",
        r"(?:respiratory rate|rr)\s*(?:of\s*)?(\d+)\s*(?:/min)?",
        r"(?:oxygen saturation|o2 sat|spo2)\s*(?:of\s*)?(\d+)\s*%?",
        # Lab values
        r"(?:hemoglobin|hgb)\s*(?:of\s*)?([\d.]+)\s*(?:g/dL)?",
        r"(?:white blood cell|wbc)\s*(?:count\s*)?(?:of\s*)?([\d.]+)\s*(?:k/uL)?",
        r"(?:creatinine|cr)\s*(?:of\s*)?([\d.]+)\s*(?:mg/dL)?",
        r"(?:bnp)\s*(?:of\s*)?([\d.]+)\s*(?:pg/mL)?",
    ]

    # Negation triggers (words that indicate absence)
    # Note: Order matters - check "cannot rule out" for uncertainty first
    NEGATION_TRIGGERS = [
        r"\bno\b",
        r"\bnot\b",
        r"\bdenies\b",
        r"\bdenied\b",
        r"\bwithout\b",
        r"\babsence\s+of\b",
        r"\bnegative\s+for\b",
        r"\bruled\s+out\b",  # Past tense - confirmed absence
        r"\brunlikely\b",
        r"\bno\s+evidence\s+of\b",
    ]

    # Uncertainty triggers (words that indicate possibility)
    # These should be checked BEFORE negation for proper precedence
    UNCERTAINTY_TRIGGERS = [
        r"\bcannot\s+rule\s+out\b",  # Uncertain, NOT negated
        r"\bcan\'?t\s+rule\s+out\b",  # Uncertain, NOT negated
        r"\bpossible\b",
        r"\bprobable\b",
        r"\bsuspected?\b",
        r"\bquestionable\b",
        r"\bmay\s+have\b",
        r"\bmight\s+have\b",
        r"\bcould\s+be\b",
        r"\bappears?\s+to\s+be\b",
        r"\blikely\b",
        r"\bconcern\s+for\b",
        r"\brule\s+out\b",  # Not yet ruled out = uncertain
    ]

    # Past temporality triggers
    PAST_TRIGGERS = [
        r"\bhistory\s+of\b",
        r"\bpast\s+history\s+of\b",
        r"\bprior\b",
        r"\bprevious\b",
        r"\bformer\b",
        r"\bhad\b",
        r"\bwas\s+diagnosed\s+with\b",
        r"\bremote\b",
    ]

    # Family history triggers
    FAMILY_TRIGGERS = [
        r"\bfamily\s+history\b",  # Matches "family history" in any context
        r"\bfamily\s+hx\b",
        r"\bfhx\b",
        r"\bmother\s+(?:has|had|with|diagnosed)\b",
        r"\bfather\s+(?:has|had|with|diagnosed)\b",
        r"\bsibling\s+(?:has|had|with|diagnosed)\b",
        r"\bbrother\s+(?:has|had|with|diagnosed)\b",
        r"\bsister\s+(?:has|had|with|diagnosed)\b",
        r"\bparent\s+(?:has|had|with|diagnosed)\b",
    ]

    def __init__(self, vocabulary_service: VocabularyServiceProtocol | None = None) -> None:
        """Initialize the rule-based NLP service.

        Args:
            vocabulary_service: Optional vocabulary service for term lookup.
                               If not provided, uses filtered database vocabulary
                               if USE_DB_VOCABULARY=true, else file-based fixture.
        """
        super().__init__()

        if vocabulary_service is not None:
            self._vocabulary_service = vocabulary_service
        elif os.environ.get("USE_DB_VOCABULARY", "").lower() == "true":
            # Use FILTERED database vocabulary for memory-efficient NLP extraction
            # This loads only high-value clinical terms (~100K) instead of all 5.36M
            from app.services.nlp_vocabulary import FilteredNLPVocabularyService
            logger.info("Using filtered database vocabulary service for NLP extraction")
            self._vocabulary_service = FilteredNLPVocabularyService()
        else:
            # Fall back to file-based fixture
            self._vocabulary_service = VocabularyService()

        # Pattern info: (pattern, synonym, domain_id, concept_id)
        self._term_patterns: list[tuple[re.Pattern[str], str, str, int]] = []
        self._initialized = False

    def _initialize_patterns(self) -> None:
        """Build regex patterns from vocabulary terms."""
        if self._initialized:
            return

        self._vocabulary_service.load()
        self._term_patterns = []

        # Build patterns from vocabulary synonyms with domain/concept hints
        for concept in self._vocabulary_service.concepts:
            for synonym in concept.synonyms:
                # Create word-boundary pattern for each synonym
                # Use case-insensitive matching
                pattern = re.compile(
                    r"\b" + re.escape(synonym) + r"\b",
                    re.IGNORECASE,
                )
                # Store pattern with domain and concept_id for direct mapping
                self._term_patterns.append((
                    pattern,
                    synonym,
                    concept.domain_id,
                    concept.concept_id
                ))

        self._initialized = True

    def extract_mentions(
        self,
        text: str,
        document_id: UUID,
        note_type: str | None = None,
    ) -> list[ExtractedMention]:
        """Extract clinical mentions from document text.

        Uses vocabulary-based matching and regex patterns to find
        clinical terms, then applies context rules for assertion,
        temporality, and experiencer.

        Args:
            text: The clinical note text to process.
            document_id: UUID of the source document.
            note_type: Optional type of clinical note.

        Returns:
            List of ExtractedMention objects with text spans and attributes.
        """
        self._initialize_patterns()

        mentions: list[ExtractedMention] = []
        seen_spans: set[tuple[int, int]] = set()

        # Extract vocabulary-based mentions
        for pattern, lexical_variant, domain_id, concept_id in self._term_patterns:
            for match in pattern.finditer(text):
                start, end = match.start(), match.end()
                matched_text = match.group()

                # Skip if we've already found a mention at this span
                if (start, end) in seen_spans:
                    continue

                # Skip stopwords (common English words that create noise)
                if matched_text.lower() in self.STOPWORDS:
                    continue

                # Skip terms below minimum length
                if len(matched_text) < self.MIN_TERM_LENGTH:
                    continue

                seen_spans.add((start, end))

                # Get context for attribute detection
                # Use preceding context for negation (NegEx-style)
                preceding_context = self._get_preceding_context(text, start)
                # Use surrounding context for temporality and experiencer
                surrounding_context = self._get_context_window(text, start, end)

                # Determine attributes from context
                assertion = self._detect_assertion(preceding_context)
                temporality = self._detect_temporality(surrounding_context)
                experiencer = self._detect_experiencer(surrounding_context)

                # Get section name
                section = self.get_section_name(text, start)

                mention = ExtractedMention(
                    text=match.group(),
                    start_offset=start,
                    end_offset=end,
                    lexical_variant=lexical_variant,
                    section=section,
                    assertion=assertion,
                    temporality=temporality,
                    experiencer=experiencer,
                    confidence=0.8,  # Rule-based confidence
                    domain_hint=domain_id,  # Pass domain from vocabulary
                    omop_concept_id=concept_id,  # Direct concept_id if available
                )
                mentions.append(mention)

        # Sort mentions by position
        mentions.sort(key=lambda m: m.start_offset)

        return mentions

    def _get_context_window(
        self,
        text: str,
        start: int,
        end: int,
        window_size: int = 50,
    ) -> str:
        """Get text context around a mention for attribute detection.

        Args:
            text: Full document text.
            start: Start offset of mention.
            end: End offset of mention.
            window_size: Characters to include before/after mention.

        Returns:
            Context string including the mention.
        """
        context_start = max(0, start - window_size)
        context_end = min(len(text), end + window_size)
        return text[context_start:context_end].lower()

    def _get_preceding_context(
        self,
        text: str,
        start: int,
        window_size: int = 50,
    ) -> str:
        """Get text BEFORE a mention for negation detection.

        NegEx-style negation typically only looks at preceding text,
        not following text.

        Args:
            text: Full document text.
            start: Start offset of mention.
            window_size: Characters to include before mention.

        Returns:
            Preceding context string (lowercase).
        """
        context_start = max(0, start - window_size)
        return text[context_start:start].lower()

    def _detect_assertion(self, context: str) -> Assertion:
        """Detect assertion status from context.

        Checks for uncertainty and negation triggers in the context
        preceding a mention. Uncertainty is checked FIRST because
        phrases like "cannot rule out" should be POSSIBLE, not ABSENT.

        Args:
            context: Text context before the mention.

        Returns:
            Assertion enum value (PRESENT, ABSENT, or POSSIBLE).
        """
        # Check for uncertainty FIRST (important for "cannot rule out")
        for pattern in self.UNCERTAINTY_TRIGGERS:
            if re.search(pattern, context, re.IGNORECASE):
                return Assertion.POSSIBLE

        # Then check for negation
        for pattern in self.NEGATION_TRIGGERS:
            if re.search(pattern, context, re.IGNORECASE):
                return Assertion.ABSENT

        return Assertion.PRESENT

    def _detect_temporality(self, context: str) -> Temporality:
        """Detect temporality from context.

        Checks for past/historical indicators in the context.

        Args:
            context: Text context around the mention.

        Returns:
            Temporality enum value (CURRENT, PAST, or FUTURE).
        """
        for pattern in self.PAST_TRIGGERS:
            if re.search(pattern, context, re.IGNORECASE):
                return Temporality.PAST

        return Temporality.CURRENT

    def _detect_experiencer(self, context: str) -> Experiencer:
        """Detect experiencer from context.

        Checks for family history indicators in the context.

        Args:
            context: Text context around the mention.

        Returns:
            Experiencer enum value (PATIENT, FAMILY, or OTHER).
        """
        for pattern in self.FAMILY_TRIGGERS:
            if re.search(pattern, context, re.IGNORECASE):
                return Experiencer.FAMILY

        return Experiencer.PATIENT
