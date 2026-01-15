"""Services for Clinical Ontology Normalizer.

Services implement business logic and data processing:
- VocabularyService: OMOP concept lookup and matching (task 2.7)
- NLPService: Mention extraction (task 4.x) - pending
- MappingService: OMOP concept mapping (task 5.x) - pending
- FactBuilderService: ClinicalFact construction (task 6.x) - pending
- GraphBuilderService: Knowledge graph materialization (task 7.x) - pending
"""

from app.services.vocabulary import VocabularyService

__all__ = ["VocabularyService"]
