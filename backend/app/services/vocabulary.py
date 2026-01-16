"""Vocabulary service for OMOP concept lookup.

Loads the local OMOP vocabulary fixture and clinical abbreviations,
providing lookup functions for concept matching.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar

from app.schemas.base import Domain

logger = logging.getLogger(__name__)


@dataclass
class OMOPConcept:
    """OMOP concept representation."""

    concept_id: int
    concept_name: str
    concept_code: str
    vocabulary_id: str
    domain_id: str
    synonyms: list[str] = field(default_factory=list)

    @property
    def domain(self) -> Domain:
        """Convert domain_id string to Domain enum."""
        domain_map = {
            "Condition": Domain.CONDITION,
            "Drug": Domain.DRUG,
            "Measurement": Domain.MEASUREMENT,
            "Procedure": Domain.PROCEDURE,
            "Observation": Domain.OBSERVATION,
            "Device": Domain.DEVICE,
        }
        return domain_map.get(self.domain_id, Domain.OBSERVATION)


class VocabularyService:
    """Service for loading and querying OMOP vocabulary.

    Loads concepts from the local fixture file and clinical abbreviations,
    providing lookup methods for concept matching.

    Usage:
        vocab = VocabularyService()
        vocab.load()
        matches = vocab.search("pneumonia")
    """

    # Default fixture paths relative to project root
    DEFAULT_FIXTURE_PATH: ClassVar[str] = "fixtures/omop_vocabulary.json"
    CLINICAL_ABBREVIATIONS_PATH: ClassVar[str] = "fixtures/clinical_abbreviations.json"

    def __init__(self, fixture_path: str | Path | None = None) -> None:
        """Initialize the vocabulary service.

        Args:
            fixture_path: Path to the OMOP vocabulary JSON fixture.
                         Defaults to fixtures/omop_vocabulary.json.
        """
        self._fixture_path = fixture_path
        self._concepts: list[OMOPConcept] = []
        self._synonym_index: dict[str, list[OMOPConcept]] = {}
        self._loaded = False

    def _find_fixtures_dir(self) -> Path:
        """Find the fixtures directory."""
        current = Path(__file__).parent
        while current.parent != current:
            potential_path = current / "fixtures"
            if potential_path.exists():
                return potential_path
            current = current.parent
        # Fallback to relative path from cwd
        return Path("fixtures")

    @property
    def fixture_path(self) -> Path:
        """Get the fixture file path."""
        if self._fixture_path:
            return Path(self._fixture_path)
        return self._find_fixtures_dir() / "omop_vocabulary.json"

    @property
    def clinical_abbreviations_path(self) -> Path:
        """Get the clinical abbreviations file path."""
        return self._find_fixtures_dir() / "clinical_abbreviations.json"

    def load(self) -> None:
        """Load concepts from vocabulary fixture and clinical abbreviations."""
        if self._loaded:
            return

        self._concepts = []
        self._synonym_index = {}

        # Load clinical abbreviations FIRST (highest priority)
        # These are curated terms with correct domains
        self._load_clinical_abbreviations()
        curated_synonyms = set(self._synonym_index.keys())

        # Then load OMOP vocabulary fixture
        path = self.fixture_path
        if path.exists():
            with open(path) as f:
                data = json.load(f)

            for concept_data in data.get("concepts", []):
                # Filter out synonyms already in clinical abbreviations
                synonyms = [
                    s for s in concept_data.get("synonyms", [])
                    if s.lower() not in curated_synonyms
                ]

                # Skip if all synonyms are already covered
                if not synonyms:
                    continue

                concept = OMOPConcept(
                    concept_id=concept_data["concept_id"],
                    concept_name=concept_data["concept_name"],
                    concept_code=concept_data["concept_code"],
                    vocabulary_id=concept_data["vocabulary_id"],
                    domain_id=concept_data["domain_id"],
                    synonyms=synonyms,
                )
                self._concepts.append(concept)

                # Build synonym index for fast lookup
                for synonym in concept.synonyms:
                    key = synonym.lower()
                    if key not in self._synonym_index:
                        self._synonym_index[key] = []
                    self._synonym_index[key].append(concept)

        self._loaded = True
        logger.info(
            f"Vocabulary loaded: {len(self._concepts)} concepts, "
            f"{len(self._synonym_index)} unique terms"
        )

    def _load_clinical_abbreviations(self) -> None:
        """Load clinical abbreviations for labs, vitals, conditions, drugs, etc."""
        abbrev_path = self.clinical_abbreviations_path
        if not abbrev_path.exists():
            logger.warning(f"Clinical abbreviations not found: {abbrev_path}")
            return

        try:
            with open(abbrev_path) as f:
                data = json.load(f)

            terms = data.get("terms", [])
            for term in terms:
                name = term.get("name", "")
                synonyms = term.get("synonyms", [])
                domain_str = term.get("domain", "Observation")
                concept_id = term.get("omop_concept_id", 0)

                if not name or not synonyms:
                    continue

                concept = OMOPConcept(
                    concept_id=concept_id,
                    concept_name=name,
                    concept_code=name.upper(),
                    vocabulary_id="Clinical Abbreviations",
                    domain_id=domain_str,
                    synonyms=synonyms,
                )
                self._concepts.append(concept)

                # Build synonym index
                for synonym in synonyms:
                    key = synonym.lower()
                    if key not in self._synonym_index:
                        self._synonym_index[key] = []
                    self._synonym_index[key].append(concept)

            logger.info(f"Loaded {len(terms)} clinical abbreviations")

        except Exception as e:
            logger.error(f"Error loading clinical abbreviations: {e}")

    @property
    def concepts(self) -> list[OMOPConcept]:
        """Get all loaded concepts."""
        if not self._loaded:
            self.load()
        return self._concepts

    @property
    def concept_count(self) -> int:
        """Get the number of loaded concepts."""
        return len(self.concepts)

    def get_by_id(self, concept_id: int) -> OMOPConcept | None:
        """Get a concept by its OMOP concept ID.

        Args:
            concept_id: The OMOP concept ID.

        Returns:
            The matching concept or None.
        """
        if not self._loaded:
            self.load()
        for concept in self._concepts:
            if concept.concept_id == concept_id:
                return concept
        return None

    def search(self, term: str, limit: int = 5) -> list[OMOPConcept]:
        """Search for concepts by term.

        Performs exact match on synonyms first, then partial match
        on concept names.

        Args:
            term: The search term.
            limit: Maximum number of results to return.

        Returns:
            List of matching concepts, ordered by relevance.
        """
        if not self._loaded:
            self.load()

        term_lower = term.lower()
        results: list[OMOPConcept] = []
        seen_ids: set[int] = set()

        # Exact synonym match (highest priority)
        if term_lower in self._synonym_index:
            for concept in self._synonym_index[term_lower]:
                if concept.concept_id not in seen_ids:
                    results.append(concept)
                    seen_ids.add(concept.concept_id)
                    if len(results) >= limit:
                        return results

        # Partial match on synonyms
        for synonym, concepts in self._synonym_index.items():
            if term_lower in synonym:
                for concept in concepts:
                    if concept.concept_id not in seen_ids:
                        results.append(concept)
                        seen_ids.add(concept.concept_id)
                        if len(results) >= limit:
                            return results

        # Partial match on concept names
        for concept in self._concepts:
            if term_lower in concept.concept_name.lower():
                if concept.concept_id not in seen_ids:
                    results.append(concept)
                    seen_ids.add(concept.concept_id)
                    if len(results) >= limit:
                        return results

        return results

    def search_by_domain(self, term: str, domain: Domain, limit: int = 5) -> list[OMOPConcept]:
        """Search for concepts by term within a specific domain.

        Args:
            term: The search term.
            domain: The OMOP domain to filter by.
            limit: Maximum number of results to return.

        Returns:
            List of matching concepts in the specified domain.
        """
        all_matches = self.search(term, limit=limit * 2)
        filtered = [c for c in all_matches if c.domain == domain]
        return filtered[:limit]

    def get_concepts_by_domain(self, domain: Domain) -> list[OMOPConcept]:
        """Get all concepts in a specific domain.

        Args:
            domain: The OMOP domain to filter by.

        Returns:
            List of concepts in the specified domain.
        """
        if not self._loaded:
            self.load()
        domain_str_map = {
            Domain.CONDITION: "Condition",
            Domain.DRUG: "Drug",
            Domain.MEASUREMENT: "Measurement",
            Domain.PROCEDURE: "Procedure",
            Domain.OBSERVATION: "Observation",
            Domain.DEVICE: "Device",
        }
        domain_str = domain_str_map.get(domain, "")
        return [c for c in self._concepts if c.domain_id == domain_str]
