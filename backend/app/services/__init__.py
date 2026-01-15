"""Services for Clinical Ontology Normalizer.

Services implement business logic and data processing:
- VocabularyService: OMOP concept lookup and matching (task 2.7)
- NLPService: Mention extraction (task 4.x)
- MappingService: OMOP concept mapping (task 5.x)
- FactBuilderService: ClinicalFact construction (task 6.x) - pending
- GraphBuilderService: Knowledge graph materialization (task 7.x) - pending
"""

from app.services.mapping import (
    BaseMappingService,
    ConceptCandidate,
    MappingMethod,
    MappingServiceInterface,
)
from app.services.mapping_db import DatabaseMappingService
from app.services.nlp import BaseNLPService, ExtractedMention, NLPServiceInterface
from app.services.nlp_rule_based import RuleBasedNLPService
from app.services.vocabulary import VocabularyService

__all__ = [
    "BaseMappingService",
    "BaseNLPService",
    "ConceptCandidate",
    "DatabaseMappingService",
    "ExtractedMention",
    "MappingMethod",
    "MappingServiceInterface",
    "NLPServiceInterface",
    "RuleBasedNLPService",
    "VocabularyService",
]
