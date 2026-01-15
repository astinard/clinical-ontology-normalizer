"""Rule-based NLP service for clinical mention extraction.

Uses regex patterns and vocabulary lookups to extract mentions
from clinical documents.
"""

import re
from uuid import UUID

from app.schemas.base import Assertion, Experiencer, Temporality
from app.services.nlp import BaseNLPService, ExtractedMention
from app.services.vocabulary import VocabularyService


class RuleBasedNLPService(BaseNLPService):
    """Rule-based mention extractor using regex and vocabulary matching.

    This service extracts clinical mentions by:
    1. Searching for known clinical terms from the vocabulary
    2. Using regex patterns to identify common clinical patterns
    3. Applying context rules for negation, temporality, and experiencer

    Usage:
        vocab = VocabularyService()
        nlp = RuleBasedNLPService(vocab)
        mentions = nlp.extract_mentions(document.text, document.id)
    """

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
    NEGATION_TRIGGERS = [
        r"\bno\b",
        r"\bnot\b",
        r"\bdenies\b",
        r"\bdenied\b",
        r"\bwithout\b",
        r"\babsence\s+of\b",
        r"\bnegative\s+for\b",
        r"\brules?\s+out\b",
        r"\brunlikely\b",
    ]

    # Uncertainty triggers (words that indicate possibility)
    UNCERTAINTY_TRIGGERS = [
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

    def __init__(self, vocabulary_service: VocabularyService | None = None) -> None:
        """Initialize the rule-based NLP service.

        Args:
            vocabulary_service: Optional vocabulary service for term lookup.
                               If not provided, creates a new instance.
        """
        super().__init__()
        self._vocabulary_service = vocabulary_service or VocabularyService()
        self._term_patterns: list[tuple[re.Pattern[str], str]] = []
        self._initialized = False

    def _initialize_patterns(self) -> None:
        """Build regex patterns from vocabulary terms."""
        if self._initialized:
            return

        self._vocabulary_service.load()
        self._term_patterns = []

        # Build patterns from vocabulary synonyms
        for concept in self._vocabulary_service.concepts:
            for synonym in concept.synonyms:
                # Create word-boundary pattern for each synonym
                # Use case-insensitive matching
                pattern = re.compile(
                    r"\b" + re.escape(synonym) + r"\b",
                    re.IGNORECASE,
                )
                self._term_patterns.append((pattern, synonym))

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
        for pattern, lexical_variant in self._term_patterns:
            for match in pattern.finditer(text):
                start, end = match.start(), match.end()

                # Skip if we've already found a mention at this span
                if (start, end) in seen_spans:
                    continue
                seen_spans.add((start, end))

                # Get context for assertion/temporality/experiencer detection
                context = self._get_context_window(text, start, end)

                # Determine attributes from context
                assertion = self._detect_assertion(context)
                temporality = self._detect_temporality(context)
                experiencer = self._detect_experiencer(context)

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

    def _detect_assertion(self, context: str) -> Assertion:
        """Detect assertion status from context.

        Checks for negation and uncertainty triggers in the context
        surrounding a mention.

        Args:
            context: Text context around the mention.

        Returns:
            Assertion enum value (PRESENT, ABSENT, or POSSIBLE).
        """
        # Check for negation first
        for pattern in self.NEGATION_TRIGGERS:
            if re.search(pattern, context, re.IGNORECASE):
                return Assertion.ABSENT

        # Check for uncertainty
        for pattern in self.UNCERTAINTY_TRIGGERS:
            if re.search(pattern, context, re.IGNORECASE):
                return Assertion.POSSIBLE

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
