"""Tests for Relation Extraction Service.

Tests the clinical relation extraction functionality including:
- Pattern-based relation extraction
- Proximity-based relation extraction
- Dependency parsing relations (when available)
"""

import pytest
from uuid import uuid4

from app.services.relation_extraction import (
    ExtractedRelation,
    RelationExtractionConfig,
    RelationExtractionService,
    RelationType,
    get_relation_extraction_service,
    reset_relation_extraction_service,
)
from app.services.nlp import ExtractedMention
from app.schemas.base import Assertion, Domain, Experiencer, Temporality


# ============================================================================
# Configuration Tests
# ============================================================================


class TestRelationExtractionConfig:
    """Test configuration dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = RelationExtractionConfig()
        assert config.min_confidence == 0.5
        assert config.max_entity_distance == 200
        assert config.use_dependency_parsing is True
        assert config.use_patterns is True
        assert config.allowed_source_domains is None
        assert config.allowed_target_domains is None

    def test_custom_config(self):
        """Test custom configuration."""
        config = RelationExtractionConfig(
            min_confidence=0.8,
            max_entity_distance=100,
            use_dependency_parsing=False,
            allowed_source_domains=[Domain.DRUG.value],
        )
        assert config.min_confidence == 0.8
        assert config.max_entity_distance == 100
        assert config.use_dependency_parsing is False
        assert config.allowed_source_domains == [Domain.DRUG.value]


# ============================================================================
# Relation Type Tests
# ============================================================================


class TestRelationType:
    """Test relation type enum."""

    def test_treatment_relations(self):
        """Test treatment relation types exist."""
        assert RelationType.TREATS.value == "treats"
        assert RelationType.PRESCRIBED_FOR.value == "prescribed_for"
        assert RelationType.ALLEVIATES.value == "alleviates"

    def test_adverse_relations(self):
        """Test adverse effect relation types exist."""
        assert RelationType.CAUSES.value == "causes"
        assert RelationType.CONTRAINDICATED_FOR.value == "contraindicated_for"

    def test_diagnostic_relations(self):
        """Test diagnostic relation types exist."""
        assert RelationType.INDICATES.value == "indicates"
        assert RelationType.DIAGNOSES.value == "diagnoses"
        assert RelationType.FINDING_OF.value == "finding_of"

    def test_procedural_relations(self):
        """Test procedural relation types exist."""
        assert RelationType.REQUIRES.value == "requires"
        assert RelationType.PERFORMED_FOR.value == "performed_for"

    def test_anatomical_relations(self):
        """Test anatomical relation types exist."""
        assert RelationType.LOCATED_IN.value == "located_in"
        assert RelationType.AFFECTS.value == "affects"


# ============================================================================
# Service Initialization Tests
# ============================================================================


class TestRelationExtractionServiceInit:
    """Test service initialization."""

    def setup_method(self):
        """Reset singleton before each test."""
        reset_relation_extraction_service()

    def test_service_creation(self):
        """Test basic service creation."""
        service = RelationExtractionService()
        assert service is not None
        assert service.config is not None

    def test_service_with_custom_config(self):
        """Test service creation with custom config."""
        config = RelationExtractionConfig(min_confidence=0.9)
        service = RelationExtractionService(config=config)
        assert service.config.min_confidence == 0.9

    def test_singleton_pattern(self):
        """Test singleton pattern works."""
        service1 = get_relation_extraction_service()
        service2 = get_relation_extraction_service()
        assert service1 is service2

    def test_singleton_reset(self):
        """Test singleton can be reset."""
        service1 = get_relation_extraction_service()
        reset_relation_extraction_service()
        service2 = get_relation_extraction_service()
        assert service1 is not service2


# ============================================================================
# Pattern Extraction Tests
# ============================================================================


class TestPatternExtraction:
    """Test pattern-based relation extraction."""

    def setup_method(self):
        """Create service for testing."""
        reset_relation_extraction_service()
        self.service = RelationExtractionService()

    def test_drug_for_condition(self):
        """Test extracting 'Drug for Condition' pattern."""
        text = "Patient is on metformin for diabetes."
        relations = self.service.extract_pattern_relations(text)

        # Should find metformin -> diabetes relation
        drug_relations = [r for r in relations
                        if "metformin" in r.source_text.lower() or
                        "metformin" in r.target_text.lower()]
        assert len(drug_relations) > 0

    def test_started_on_drug_for_condition(self):
        """Test extracting 'Started on Drug for Condition' pattern."""
        text = "Started on lisinopril for hypertension."
        relations = self.service.extract_pattern_relations(text)

        treatment_relations = [r for r in relations
                              if r.relation_type in [RelationType.TREATS, RelationType.PRESCRIBED_FOR]]
        assert len(treatment_relations) > 0

    def test_continue_drug_for_condition(self):
        """Test extracting 'Continue Drug for Condition' pattern."""
        text = "Continue aspirin for cardiac protection."
        relations = self.service.extract_pattern_relations(text)

        assert len(relations) > 0
        assert any(r.relation_type == RelationType.TREATS for r in relations)

    def test_condition_dash_drug_pattern(self):
        """Test extracting 'Condition - Drug' assessment pattern."""
        text = "Diabetes - continue metformin"
        relations = self.service.extract_pattern_relations(text)

        # Should extract the treatment relation
        assert len(relations) > 0

    def test_drug_causes_side_effect(self):
        """Test extracting adverse effect pattern."""
        text = "Statin caused muscle pain."
        relations = self.service.extract_pattern_relations(text)

        causes_relations = [r for r in relations if r.relation_type == RelationType.CAUSES]
        assert len(causes_relations) > 0

    def test_test_shows_condition(self):
        """Test extracting diagnostic pattern."""
        text = "CT scan shows pneumonia."
        relations = self.service.extract_pattern_relations(text)

        diagnostic_relations = [r for r in relations
                               if r.relation_type == RelationType.DIAGNOSES]
        assert len(diagnostic_relations) > 0

    def test_symptom_suggestive_of_condition(self):
        """Test extracting indicative pattern."""
        text = "Chest pain suggestive of angina."
        relations = self.service.extract_pattern_relations(text)

        indicates_relations = [r for r in relations
                              if r.relation_type == RelationType.INDICATES]
        assert len(indicates_relations) > 0

    def test_procedure_for_condition(self):
        """Test extracting procedure pattern."""
        text = "Colonoscopy for colon cancer screening."
        relations = self.service.extract_pattern_relations(text)

        procedure_relations = [r for r in relations
                              if r.relation_type == RelationType.PERFORMED_FOR]
        assert len(procedure_relations) > 0

    def test_no_relations_in_simple_text(self):
        """Test that simple text without relations returns empty."""
        text = "Patient is doing well."
        relations = self.service.extract_pattern_relations(text)
        # May have some false positives, but should be minimal
        assert len(relations) < 5


# ============================================================================
# Proximity Extraction Tests
# ============================================================================


class TestProximityExtraction:
    """Test proximity-based relation extraction."""

    def setup_method(self):
        """Create service and test mentions."""
        reset_relation_extraction_service()
        self.service = RelationExtractionService()

    def _create_mention(
        self,
        text: str,
        start: int,
        end: int,
        domain: str,
    ) -> ExtractedMention:
        """Helper to create test mentions."""
        return ExtractedMention(
            text=text,
            start_offset=start,
            end_offset=end,
            lexical_variant=text.lower(),
            domain_hint=domain,
            assertion=Assertion.PRESENT,
            temporality=Temporality.CURRENT,
            experiencer=Experiencer.PATIENT,
            confidence=0.9,
        )

    def test_drug_condition_proximity(self):
        """Test extracting relations based on proximity."""
        text = "Patient on metformin for diabetes control."
        #        0         1         2         3         4
        #        0123456789012345678901234567890123456789012

        mentions = [
            self._create_mention("metformin", 11, 20, Domain.DRUG.value),
            self._create_mention("diabetes", 25, 33, Domain.CONDITION.value),
        ]

        relations = self.service.extract_mention_relations(text, mentions)

        # Should find metformin -> diabetes relation
        assert len(relations) > 0
        assert any(r.relation_type == RelationType.TREATS for r in relations)

    def test_observation_condition_proximity(self):
        """Test extracting observation -> condition relations."""
        text = "Fever suggests infection."
        #        0         1         2
        #        0123456789012345678901234

        mentions = [
            self._create_mention("Fever", 0, 5, Domain.OBSERVATION.value),
            self._create_mention("infection", 15, 24, Domain.CONDITION.value),
        ]

        relations = self.service.extract_mention_relations(text, mentions)

        # Should find indicates relation
        indicates = [r for r in relations if r.relation_type == RelationType.INDICATES]
        assert len(indicates) > 0

    def test_distant_entities_no_relation(self):
        """Test that distant entities don't create relations."""
        text = "Patient has diabetes. " + "x" * 300 + " Taking metformin."

        mentions = [
            self._create_mention("diabetes", 12, 20, Domain.CONDITION.value),
            self._create_mention("metformin", 330, 339, Domain.DRUG.value),
        ]

        relations = self.service.extract_mention_relations(text, mentions)

        # Should not find relations due to distance
        assert len(relations) == 0

    def test_multiple_mentions(self):
        """Test extraction with multiple mentions."""
        text = "Diabetes controlled on metformin. Hypertension on lisinopril."
        #        0         1         2         3         4         5         6
        #        0123456789012345678901234567890123456789012345678901234567890

        mentions = [
            self._create_mention("Diabetes", 0, 8, Domain.CONDITION.value),
            self._create_mention("metformin", 23, 32, Domain.DRUG.value),
            self._create_mention("Hypertension", 34, 46, Domain.CONDITION.value),
            self._create_mention("lisinopril", 50, 60, Domain.DRUG.value),
        ]

        relations = self.service.extract_mention_relations(text, mentions)

        # Should find multiple treatment relations
        treatment_relations = [r for r in relations
                              if r.relation_type == RelationType.TREATS]
        assert len(treatment_relations) >= 2


# ============================================================================
# Combined Extraction Tests
# ============================================================================


class TestCombinedExtraction:
    """Test combined extraction methods."""

    def setup_method(self):
        """Create service for testing."""
        reset_relation_extraction_service()
        self.service = RelationExtractionService()

    def _create_mention(
        self,
        text: str,
        start: int,
        end: int,
        domain: str,
    ) -> ExtractedMention:
        """Helper to create test mentions."""
        return ExtractedMention(
            text=text,
            start_offset=start,
            end_offset=end,
            lexical_variant=text.lower(),
            domain_hint=domain,
            assertion=Assertion.PRESENT,
            temporality=Temporality.CURRENT,
            experiencer=Experiencer.PATIENT,
            confidence=0.9,
        )

    def test_extract_all_combines_methods(self):
        """Test that extract_all combines pattern and proximity methods."""
        text = "Started metformin for diabetes. Continue aspirin for cardiac protection."

        mentions = [
            self._create_mention("metformin", 8, 17, Domain.DRUG.value),
            self._create_mention("diabetes", 22, 30, Domain.CONDITION.value),
            self._create_mention("aspirin", 41, 48, Domain.DRUG.value),
        ]

        relations = self.service.extract_all(text, mentions)

        # Should have relations from both patterns and proximity
        assert len(relations) > 0

    def test_extract_all_without_mentions(self):
        """Test extract_all with only pattern extraction."""
        text = "Started metformin for diabetes."
        relations = self.service.extract_all(text)

        # Should still find pattern relations
        assert len(relations) > 0

    def test_deduplication(self):
        """Test that duplicate relations are removed."""
        text = "Metformin for diabetes. Metformin treats diabetes."

        mentions = [
            self._create_mention("Metformin", 0, 9, Domain.DRUG.value),
            self._create_mention("diabetes", 14, 22, Domain.CONDITION.value),
            self._create_mention("Metformin", 24, 33, Domain.DRUG.value),
            self._create_mention("diabetes", 41, 49, Domain.CONDITION.value),
        ]

        relations = self.service.extract_all(text, mentions)

        # Check for duplicates
        seen = set()
        for r in relations:
            key = (r.source_text.lower(), r.target_text.lower(), r.relation_type)
            assert key not in seen, f"Duplicate relation: {key}"
            seen.add(key)


# ============================================================================
# Configuration Behavior Tests
# ============================================================================


class TestConfigurationBehavior:
    """Test configuration affects service behavior."""

    def setup_method(self):
        """Reset singleton before each test."""
        reset_relation_extraction_service()

    def test_high_confidence_threshold(self):
        """Test high confidence threshold filters relations."""
        text = "Metformin for diabetes."

        # Low threshold
        config_low = RelationExtractionConfig(min_confidence=0.1)
        service_low = RelationExtractionService(config=config_low)
        relations_low = service_low.extract_pattern_relations(text)

        # High threshold
        config_high = RelationExtractionConfig(min_confidence=0.99)
        service_high = RelationExtractionService(config=config_high)
        relations_high = service_high.extract_pattern_relations(text)

        # High threshold should filter more
        assert len(relations_high) <= len(relations_low)

    def test_patterns_disabled(self):
        """Test disabling pattern extraction."""
        config = RelationExtractionConfig(use_patterns=False)
        service = RelationExtractionService(config=config)

        text = "Metformin for diabetes."
        relations = service.extract_pattern_relations(text)

        assert len(relations) == 0

    def test_domain_filter(self):
        """Test domain filtering."""
        config = RelationExtractionConfig(
            allowed_source_domains=[Domain.DRUG.value],
            allowed_target_domains=[Domain.CONDITION.value],
        )
        service = RelationExtractionService(config=config)

        text = "Metformin for diabetes. CT shows pneumonia."

        relations = service.extract_pattern_relations(text)

        # All relations should have drug source and condition target
        for r in relations:
            if r.source_domain:
                assert r.source_domain == Domain.DRUG.value


# ============================================================================
# Complex Clinical Text Tests
# ============================================================================


class TestComplexClinicalText:
    """Test extraction on realistic clinical text."""

    def setup_method(self):
        """Create service for testing."""
        reset_relation_extraction_service()
        self.service = RelationExtractionService()

    def test_assessment_plan_section(self):
        """Test extraction on assessment and plan section."""
        text = """
ASSESSMENT AND PLAN:
1. Type 2 diabetes - continue metformin 1000mg BID
2. Hypertension - start lisinopril 10mg daily
3. Chest pain - rule out ACS, obtain EKG
4. Hyperlipidemia - atorvastatin 40mg daily
"""
        relations = self.service.extract_pattern_relations(text)

        # Should find multiple treatment relations
        treatment_relations = [r for r in relations
                              if r.relation_type in [RelationType.TREATS, RelationType.PRESCRIBED_FOR]]
        assert len(treatment_relations) >= 2

    def test_medication_list(self):
        """Test extraction on medication list."""
        text = """
MEDICATIONS:
1. Metformin 500mg for diabetes
2. Lisinopril 10mg for blood pressure
3. Aspirin 81mg for cardiac protection
4. Omeprazole 20mg for GERD
"""
        relations = self.service.extract_pattern_relations(text)

        # Should find treatment relations for each medication
        assert len(relations) >= 4

    def test_history_section(self):
        """Test extraction on history section."""
        text = """
PAST MEDICAL HISTORY:
- Diabetes mellitus, treated with metformin
- Hypertension, controlled on lisinopril
- Prior MI, status post stent placement
- GERD, on omeprazole
"""
        relations = self.service.extract_pattern_relations(text)

        assert len(relations) > 0

    def test_adverse_reactions(self):
        """Test extraction of adverse drug reactions."""
        text = """
ALLERGIES/ADVERSE REACTIONS:
- Penicillin: anaphylaxis
- Sulfa drugs: rash
- Statins caused muscle pain, discontinued
"""
        relations = self.service.extract_pattern_relations(text)

        # Should find causes/adverse relations
        adverse_relations = [r for r in relations
                           if r.relation_type in [RelationType.CAUSES, RelationType.CAUSED_BY]]
        assert len(adverse_relations) >= 1


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Integration tests for relation extraction service."""

    def setup_method(self):
        """Reset singleton before each test."""
        reset_relation_extraction_service()

    def test_service_through_module_interface(self):
        """Test accessing service through module interface."""
        from app.services import (
            RelationExtractionService,
            get_relation_extraction_service,
            reset_relation_extraction_service,
        )

        service = get_relation_extraction_service()
        assert isinstance(service, RelationExtractionService)

        reset_relation_extraction_service()
        service2 = get_relation_extraction_service()
        assert service is not service2

    def test_extracted_relation_fields(self):
        """Test that extracted relations have all expected fields."""
        service = RelationExtractionService()
        text = "Metformin for diabetes."
        relations = service.extract_pattern_relations(text)

        for relation in relations:
            assert hasattr(relation, "id")
            assert hasattr(relation, "source_text")
            assert hasattr(relation, "source_start")
            assert hasattr(relation, "source_end")
            assert hasattr(relation, "source_domain")
            assert hasattr(relation, "target_text")
            assert hasattr(relation, "target_start")
            assert hasattr(relation, "target_end")
            assert hasattr(relation, "target_domain")
            assert hasattr(relation, "relation_type")
            assert hasattr(relation, "confidence")
            assert hasattr(relation, "evidence_text")
            assert hasattr(relation, "extraction_method")
