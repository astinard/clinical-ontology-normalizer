"""Services for Clinical Ontology Normalizer.

Services implement business logic and data processing:
- VocabularyService: OMOP concept lookup and matching (task 2.7)
- NLPService: Mention extraction (task 4.x)
- MappingService: OMOP concept mapping (task 5.x)
- FactBuilderService: ClinicalFact construction (task 6.x)
- GraphBuilderService: Knowledge graph materialization (task 7.x)
- OMOPExporter: Export to OMOP CDM format (task 9.x)
"""

from app.services.export import (
    BaseOMOPExporter,
    DatabaseOMOPExporter,
    NoteExport,
    NoteNLPExport,
    OMOPExportResult,
)
from app.services.fact_builder import (
    BaseFactBuilderService,
    EvidenceInput,
    FactBuilderServiceInterface,
    FactInput,
    FactResult,
)
from app.services.fact_builder_db import DatabaseFactBuilderService
from app.services.graph_builder import (
    BaseGraphBuilderService,
    EdgeInput,
    GraphBuilderServiceInterface,
    GraphResult,
    NodeInput,
)
from app.services.graph_builder_db import DatabaseGraphBuilderService
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
    "BaseFactBuilderService",
    "BaseGraphBuilderService",
    "BaseMappingService",
    "BaseNLPService",
    "ConceptCandidate",
    "DatabaseFactBuilderService",
    "DatabaseGraphBuilderService",
    "DatabaseMappingService",
    "EdgeInput",
    "EvidenceInput",
    "ExtractedMention",
    "FactBuilderServiceInterface",
    "FactInput",
    "FactResult",
    "GraphBuilderServiceInterface",
    "GraphResult",
    "MappingMethod",
    "MappingServiceInterface",
    "NodeInput",
    "NLPServiceInterface",
    "RuleBasedNLPService",
    "VocabularyService",
    "BaseOMOPExporter",
    "DatabaseOMOPExporter",
    "NoteExport",
    "NoteNLPExport",
    "OMOPExportResult",
]
