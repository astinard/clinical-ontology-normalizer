"""Tests for Pydantic schemas."""

from datetime import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas import (
    Assertion,
    ClinicalFact,
    ClinicalFactCreate,
    Document,
    DocumentCreate,
    Domain,
    Experiencer,
    FactEvidenceCreate,
    JobStatus,
    KGEdge,
    KGEdgeCreate,
    KGNode,
    KGNodeCreate,
    MentionConceptCandidateCreate,
    MentionCreate,
    PatientGraph,
    Temporality,
)
from app.schemas.clinical_fact import EvidenceType
from app.schemas.knowledge_graph import EdgeType, NodeType


class TestEnums:
    """Test enum definitions."""

    def test_assertion_values(self) -> None:
        """Test assertion enum has correct values."""
        assert Assertion.PRESENT.value == "present"
        assert Assertion.ABSENT.value == "absent"
        assert Assertion.POSSIBLE.value == "possible"

    def test_temporality_values(self) -> None:
        """Test temporality enum has correct values."""
        assert Temporality.CURRENT.value == "current"
        assert Temporality.PAST.value == "past"
        assert Temporality.FUTURE.value == "future"

    def test_experiencer_values(self) -> None:
        """Test experiencer enum has correct values."""
        assert Experiencer.PATIENT.value == "patient"
        assert Experiencer.FAMILY.value == "family"
        assert Experiencer.OTHER.value == "other"

    def test_domain_values(self) -> None:
        """Test domain enum has required values."""
        assert Domain.CONDITION.value == "condition"
        assert Domain.DRUG.value == "drug"
        assert Domain.MEASUREMENT.value == "measurement"
        assert Domain.PROCEDURE.value == "procedure"

    def test_job_status_values(self) -> None:
        """Test job status enum values."""
        assert JobStatus.QUEUED.value == "queued"
        assert JobStatus.PROCESSING.value == "processing"
        assert JobStatus.COMPLETED.value == "completed"
        assert JobStatus.FAILED.value == "failed"


class TestDocumentSchemas:
    """Test Document schemas."""

    def test_document_create_valid(self) -> None:
        """Test valid document creation."""
        doc = DocumentCreate(
            patient_id="P001",
            note_type="progress_note",
            text="Patient presents with cough.",
        )
        assert doc.patient_id == "P001"
        assert doc.note_type == "progress_note"
        assert doc.metadata == {}

    def test_document_create_with_metadata(self) -> None:
        """Test document creation with metadata."""
        doc = DocumentCreate(
            patient_id="P001",
            note_type="discharge_summary",
            text="Discharge summary text.",
            metadata={"encounter_id": "E123"},
        )
        assert doc.metadata["encounter_id"] == "E123"

    def test_document_full(self) -> None:
        """Test full document schema."""
        doc = Document(
            id=uuid4(),
            patient_id="P001",
            note_type="progress_note",
            text="Note text",
            metadata={},
            status=JobStatus.COMPLETED,
            created_at=datetime.now(),
            processed_at=datetime.now(),
        )
        assert doc.status == JobStatus.COMPLETED


class TestMentionSchemas:
    """Test Mention schemas."""

    def test_mention_create_valid(self) -> None:
        """Test valid mention creation."""
        mention = MentionCreate(
            document_id=uuid4(),
            text="pneumonia",
            start_offset=10,
            end_offset=19,
            lexical_variant="pneumonia",
            assertion=Assertion.ABSENT,
            temporality=Temporality.CURRENT,
            experiencer=Experiencer.PATIENT,
        )
        assert mention.assertion == Assertion.ABSENT
        assert mention.confidence == 1.0  # default

    def test_mention_create_invalid_offsets(self) -> None:
        """Test that end_offset must be after start_offset."""
        with pytest.raises(ValidationError):
            MentionCreate(
                document_id=uuid4(),
                text="test",
                start_offset=10,
                end_offset=5,  # Invalid: before start
                lexical_variant="test",
            )

    def test_mention_create_confidence_bounds(self) -> None:
        """Test confidence must be between 0 and 1."""
        with pytest.raises(ValidationError):
            MentionCreate(
                document_id=uuid4(),
                text="test",
                start_offset=0,
                end_offset=4,
                lexical_variant="test",
                confidence=1.5,  # Invalid: > 1
            )

    def test_concept_candidate_create(self) -> None:
        """Test concept candidate creation."""
        candidate = MentionConceptCandidateCreate(
            mention_id=uuid4(),
            omop_concept_id=233604007,
            concept_name="Pneumonia",
            concept_code="233604007",
            vocabulary_id="SNOMED",
            domain_id=Domain.CONDITION,
            score=0.95,
            method="exact",
            rank=1,
        )
        assert candidate.omop_concept_id == 233604007
        assert candidate.score == 0.95


class TestClinicalFactSchemas:
    """Test ClinicalFact schemas."""

    def test_clinical_fact_create(self) -> None:
        """Test clinical fact creation."""
        fact = ClinicalFactCreate(
            patient_id="P001",
            domain=Domain.CONDITION,
            omop_concept_id=233604007,
            concept_name="Pneumonia",
            assertion=Assertion.ABSENT,
            temporality=Temporality.CURRENT,
            experiencer=Experiencer.PATIENT,
            confidence=0.9,
        )
        assert fact.assertion == Assertion.ABSENT
        assert fact.domain == Domain.CONDITION

    def test_clinical_fact_with_measurement(self) -> None:
        """Test clinical fact with value and unit."""
        fact = ClinicalFactCreate(
            patient_id="P001",
            domain=Domain.MEASUREMENT,
            omop_concept_id=4548,
            concept_name="Hemoglobin A1c",
            value="7.2",
            unit="%",
        )
        assert fact.value == "7.2"
        assert fact.unit == "%"

    def test_clinical_fact_is_negated(self) -> None:
        """Test is_negated property."""
        fact = ClinicalFact(
            id=uuid4(),
            patient_id="P001",
            domain=Domain.CONDITION,
            omop_concept_id=233604007,
            concept_name="Pneumonia",
            assertion=Assertion.ABSENT,
            temporality=Temporality.CURRENT,
            experiencer=Experiencer.PATIENT,
            confidence=0.9,
            created_at=datetime.now(),
        )
        assert fact.is_negated is True
        assert fact.is_uncertain is False

    def test_clinical_fact_is_family_history(self) -> None:
        """Test is_family_history property."""
        fact = ClinicalFact(
            id=uuid4(),
            patient_id="P001",
            domain=Domain.CONDITION,
            omop_concept_id=93761005,
            concept_name="Colon cancer",
            assertion=Assertion.PRESENT,
            temporality=Temporality.PAST,
            experiencer=Experiencer.FAMILY,
            confidence=1.0,
            created_at=datetime.now(),
        )
        assert fact.is_family_history is True

    def test_fact_evidence_create(self) -> None:
        """Test fact evidence creation."""
        evidence = FactEvidenceCreate(
            fact_id=uuid4(),
            evidence_type=EvidenceType.MENTION,
            source_id=uuid4(),
            source_table="mentions",
            weight=0.8,
        )
        assert evidence.evidence_type == EvidenceType.MENTION


class TestKnowledgeGraphSchemas:
    """Test KGNode and KGEdge schemas."""

    def test_kg_node_create(self) -> None:
        """Test KG node creation."""
        node = KGNodeCreate(
            patient_id="P001",
            node_type=NodeType.CONDITION,
            omop_concept_id=233604007,
            label="Pneumonia",
            properties={"assertion": "absent"},
        )
        assert node.node_type == NodeType.CONDITION
        assert node.properties["assertion"] == "absent"

    def test_kg_node_patient(self) -> None:
        """Test patient node (no concept ID)."""
        node = KGNodeCreate(
            patient_id="P001",
            node_type=NodeType.PATIENT,
            label="Patient P001",
        )
        assert node.omop_concept_id is None

    def test_kg_edge_create(self) -> None:
        """Test KG edge creation."""
        edge = KGEdgeCreate(
            patient_id="P001",
            source_node_id=uuid4(),
            target_node_id=uuid4(),
            edge_type=EdgeType.HAS_CONDITION,
            fact_id=uuid4(),
        )
        assert edge.edge_type == EdgeType.HAS_CONDITION

    def test_patient_graph(self) -> None:
        """Test patient graph schema."""
        patient_node = KGNode(
            id=uuid4(),
            patient_id="P001",
            node_type=NodeType.PATIENT,
            label="P001",
            properties={},
            created_at=datetime.now(),
        )
        condition_node = KGNode(
            id=uuid4(),
            patient_id="P001",
            node_type=NodeType.CONDITION,
            omop_concept_id=233604007,
            label="Pneumonia",
            properties={"assertion": "absent"},
            created_at=datetime.now(),
        )
        edge = KGEdge(
            id=uuid4(),
            patient_id="P001",
            source_node_id=patient_node.id,
            target_node_id=condition_node.id,
            edge_type=EdgeType.HAS_CONDITION,
            properties={},
            created_at=datetime.now(),
        )

        graph = PatientGraph(
            patient_id="P001",
            nodes=[patient_node, condition_node],
            edges=[edge],
        )

        assert graph.node_count == 2
        assert graph.edge_count == 1
