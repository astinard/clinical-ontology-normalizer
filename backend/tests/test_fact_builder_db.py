"""Tests for DatabaseFactBuilderService.

Tests fact construction, evidence linking, deduplication,
and correct handling of negated findings (tasks 6.2-6.6).
"""

from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.clinical_fact import ClinicalFact, FactEvidence
from app.schemas.base import Assertion, Domain, Experiencer, Temporality
from app.schemas.clinical_fact import EvidenceType
from app.services.fact_builder import EvidenceInput, FactInput
from app.services.fact_builder_db import DatabaseFactBuilderService

# Create test database engine
_test_engine = create_engine(
    "sqlite:///:memory:",
    echo=False,
    future=True,
)
_TestSession = sessionmaker(
    bind=_test_engine,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture(scope="function")
def db_session() -> Session:
    """Create a database session with clinical fact tables."""
    ClinicalFact.__table__.create(bind=_test_engine, checkfirst=True)
    FactEvidence.__table__.create(bind=_test_engine, checkfirst=True)

    session = _TestSession()
    try:
        yield session
    finally:
        session.close()
        FactEvidence.__table__.drop(bind=_test_engine, checkfirst=True)
        ClinicalFact.__table__.drop(bind=_test_engine, checkfirst=True)


@pytest.fixture
def fact_service(db_session: Session) -> DatabaseFactBuilderService:
    """Create a DatabaseFactBuilderService."""
    return DatabaseFactBuilderService(db_session)


class TestFactCreation:
    """Tests for basic fact creation (task 6.2)."""

    def test_create_fact_returns_result(self, fact_service: DatabaseFactBuilderService) -> None:
        """Test that create_fact returns a FactResult."""
        fact_input = FactInput(
            patient_id="P001",
            domain=Domain.CONDITION,
            omop_concept_id=437663,
            concept_name="Fever",
        )
        result = fact_service.create_fact(fact_input)

        assert result is not None
        assert result.fact_id is not None
        assert result.is_new is True

    def test_create_fact_persists_to_database(
        self, fact_service: DatabaseFactBuilderService, db_session: Session
    ) -> None:
        """Test that created fact is persisted to database."""
        fact_input = FactInput(
            patient_id="P001",
            domain=Domain.CONDITION,
            omop_concept_id=437663,
            concept_name="Fever",
        )
        result = fact_service.create_fact(fact_input)

        # Query database directly
        fact = db_session.query(ClinicalFact).filter_by(id=str(result.fact_id)).first()
        assert fact is not None
        assert fact.patient_id == "P001"
        assert fact.concept_name == "Fever"

    def test_create_fact_with_all_attributes(
        self, fact_service: DatabaseFactBuilderService
    ) -> None:
        """Test creating a fact with all attributes."""
        fact_input = FactInput(
            patient_id="P001",
            domain=Domain.MEASUREMENT,
            omop_concept_id=3000000,
            concept_name="Blood Pressure",
            assertion=Assertion.PRESENT,
            temporality=Temporality.CURRENT,
            experiencer=Experiencer.PATIENT,
            confidence=0.95,
            value="120/80",
            unit="mmHg",
        )
        result = fact_service.create_fact(fact_input)

        retrieved = fact_service.get_fact_by_id(result.fact_id)
        assert retrieved is not None
        assert retrieved.value == "120/80"
        assert retrieved.unit == "mmHg"
        assert retrieved.confidence == 0.95


class TestMentionToFactConversion:
    """Tests for unstructured-to-fact conversion (task 6.2)."""

    def test_create_fact_from_mention(self, fact_service: DatabaseFactBuilderService) -> None:
        """Test creating a fact from an NLP mention."""
        mention_id = uuid4()
        result = fact_service.create_fact_from_mention(
            mention_id=mention_id,
            patient_id="P001",
            omop_concept_id=437663,
            concept_name="Fever",
            domain=Domain.CONDITION,
            assertion=Assertion.PRESENT,
            temporality=Temporality.CURRENT,
            experiencer=Experiencer.PATIENT,
            confidence=0.95,
        )

        assert result.is_new is True
        assert len(result.evidence_ids) >= 1

    def test_mention_fact_creates_evidence_link(
        self, fact_service: DatabaseFactBuilderService, db_session: Session
    ) -> None:
        """Test that mention-to-fact creates evidence link."""
        mention_id = uuid4()
        result = fact_service.create_fact_from_mention(
            mention_id=mention_id,
            patient_id="P001",
            omop_concept_id=437663,
            concept_name="Fever",
            domain=Domain.CONDITION,
            assertion=Assertion.PRESENT,
            temporality=Temporality.CURRENT,
            experiencer=Experiencer.PATIENT,
            confidence=0.95,
        )

        evidence = fact_service.get_evidence_for_fact(result.fact_id)
        assert len(evidence) >= 1
        assert evidence[0].evidence_type == EvidenceType.MENTION
        assert evidence[0].source_table == "mentions"


class TestStructuredToFactConversion:
    """Tests for structured-to-fact conversion (task 6.3)."""

    def test_create_fact_from_structured(self, fact_service: DatabaseFactBuilderService) -> None:
        """Test creating a fact from structured data."""
        source_id = uuid4()
        result = fact_service.create_fact_from_structured(
            source_id=source_id,
            source_table="fhir_observations",
            patient_id="P001",
            omop_concept_id=3000000,
            concept_name="Blood Pressure",
            domain=Domain.MEASUREMENT,
            value="120/80",
            unit="mmHg",
        )

        assert result.is_new is True
        assert len(result.evidence_ids) >= 1

    def test_structured_fact_creates_evidence_link(
        self, fact_service: DatabaseFactBuilderService
    ) -> None:
        """Test that structured-to-fact creates evidence link."""
        source_id = uuid4()
        result = fact_service.create_fact_from_structured(
            source_id=source_id,
            source_table="fhir_observations",
            patient_id="P001",
            omop_concept_id=3000000,
            concept_name="Blood Pressure",
            domain=Domain.MEASUREMENT,
        )

        evidence = fact_service.get_evidence_for_fact(result.fact_id)
        assert len(evidence) >= 1
        assert evidence[0].evidence_type == EvidenceType.STRUCTURED
        assert evidence[0].source_table == "fhir_observations"


class TestEvidenceLinking:
    """Tests for FactEvidence creation (task 6.4)."""

    def test_create_fact_with_evidence(self, fact_service: DatabaseFactBuilderService) -> None:
        """Test creating a fact with evidence."""
        fact_input = FactInput(
            patient_id="P001",
            domain=Domain.CONDITION,
            omop_concept_id=437663,
            concept_name="Fever",
        )
        evidence = [
            EvidenceInput(
                evidence_type=EvidenceType.MENTION,
                source_id=uuid4(),
                source_table="mentions",
            )
        ]
        result = fact_service.create_fact(fact_input, evidence)

        assert len(result.evidence_ids) == 1

    def test_create_fact_with_multiple_evidence(
        self, fact_service: DatabaseFactBuilderService
    ) -> None:
        """Test creating a fact with multiple evidence sources."""
        fact_input = FactInput(
            patient_id="P001",
            domain=Domain.CONDITION,
            omop_concept_id=437663,
            concept_name="Fever",
        )
        evidence = [
            EvidenceInput(
                evidence_type=EvidenceType.MENTION,
                source_id=uuid4(),
                source_table="mentions",
            ),
            EvidenceInput(
                evidence_type=EvidenceType.STRUCTURED,
                source_id=uuid4(),
                source_table="fhir_conditions",
            ),
        ]
        result = fact_service.create_fact(fact_input, evidence)

        assert len(result.evidence_ids) == 2

    def test_evidence_has_correct_weight(self, fact_service: DatabaseFactBuilderService) -> None:
        """Test that evidence weight is persisted."""
        fact_input = FactInput(
            patient_id="P001",
            domain=Domain.CONDITION,
            omop_concept_id=437663,
            concept_name="Fever",
        )
        evidence = [
            EvidenceInput(
                evidence_type=EvidenceType.MENTION,
                source_id=uuid4(),
                source_table="mentions",
                weight=0.8,
            )
        ]
        result = fact_service.create_fact(fact_input, evidence)

        retrieved_evidence = fact_service.get_evidence_for_fact(result.fact_id)
        assert retrieved_evidence[0].weight == 0.8


class TestNegatedFindings:
    """Tests for correct handling of negated findings (task 6.5)."""

    def test_create_negated_fact(self, fact_service: DatabaseFactBuilderService) -> None:
        """Test creating a fact with assertion=ABSENT."""
        fact_input = FactInput(
            patient_id="P001",
            domain=Domain.CONDITION,
            omop_concept_id=255848,
            concept_name="Pneumonia",
            assertion=Assertion.ABSENT,
        )
        result = fact_service.create_fact(fact_input)

        retrieved = fact_service.get_fact_by_id(result.fact_id)
        assert retrieved is not None
        assert retrieved.assertion == Assertion.ABSENT
        assert retrieved.is_negated is True

    def test_negated_facts_preserved_in_get_all(
        self, fact_service: DatabaseFactBuilderService
    ) -> None:
        """Test that negated facts are included in get_facts_for_patient."""
        # Create a present fact
        fact_service.create_fact(
            FactInput(
                patient_id="P001",
                domain=Domain.CONDITION,
                omop_concept_id=437663,
                concept_name="Fever",
                assertion=Assertion.PRESENT,
            )
        )
        # Create a negated fact
        fact_service.create_fact(
            FactInput(
                patient_id="P001",
                domain=Domain.CONDITION,
                omop_concept_id=255848,
                concept_name="Pneumonia",
                assertion=Assertion.ABSENT,
            )
        )

        facts = fact_service.get_facts_for_patient("P001", include_negated=True)
        assert len(facts) == 2

        negated_facts = [f for f in facts if f.assertion == Assertion.ABSENT]
        assert len(negated_facts) == 1

    def test_negated_facts_can_be_excluded(self, fact_service: DatabaseFactBuilderService) -> None:
        """Test that negated facts can be excluded from results."""
        fact_service.create_fact(
            FactInput(
                patient_id="P001",
                domain=Domain.CONDITION,
                omop_concept_id=437663,
                concept_name="Fever",
                assertion=Assertion.PRESENT,
            )
        )
        fact_service.create_fact(
            FactInput(
                patient_id="P001",
                domain=Domain.CONDITION,
                omop_concept_id=255848,
                concept_name="Pneumonia",
                assertion=Assertion.ABSENT,
            )
        )

        facts = fact_service.get_facts_for_patient("P001", include_negated=False)
        assert len(facts) == 1
        assert facts[0].assertion == Assertion.PRESENT

    def test_get_negated_facts_for_patient(self, fact_service: DatabaseFactBuilderService) -> None:
        """Test getting only negated facts for a patient."""
        fact_service.create_fact(
            FactInput(
                patient_id="P001",
                domain=Domain.CONDITION,
                omop_concept_id=437663,
                concept_name="Fever",
                assertion=Assertion.PRESENT,
            )
        )
        fact_service.create_fact(
            FactInput(
                patient_id="P001",
                domain=Domain.CONDITION,
                omop_concept_id=255848,
                concept_name="Pneumonia",
                assertion=Assertion.ABSENT,
            )
        )

        negated = fact_service.get_negated_facts_for_patient("P001")
        assert len(negated) == 1
        assert negated[0].concept_name == "Pneumonia"


class TestDeduplication:
    """Tests for fact deduplication."""

    def test_duplicate_facts_are_merged(self, fact_service: DatabaseFactBuilderService) -> None:
        """Test that duplicate facts are merged, not duplicated."""
        fact_input = FactInput(
            patient_id="P001",
            domain=Domain.CONDITION,
            omop_concept_id=437663,
            concept_name="Fever",
        )

        result1 = fact_service.create_fact(fact_input)
        result2 = fact_service.create_fact(fact_input)

        # Same fact ID should be returned
        assert result1.fact_id == result2.fact_id
        assert result1.is_new is True
        assert result2.is_new is False

    def test_confidence_merged_on_dedup(self, fact_service: DatabaseFactBuilderService) -> None:
        """Test that confidence is merged when facts are deduplicated."""
        fact_input1 = FactInput(
            patient_id="P001",
            domain=Domain.CONDITION,
            omop_concept_id=437663,
            concept_name="Fever",
            confidence=0.8,
        )
        fact_input2 = FactInput(
            patient_id="P001",
            domain=Domain.CONDITION,
            omop_concept_id=437663,
            concept_name="Fever",
            confidence=0.8,
        )

        fact_service.create_fact(fact_input1)
        result2 = fact_service.create_fact(fact_input2)

        retrieved = fact_service.get_fact_by_id(result2.fact_id)
        # 1 - (0.2 * 0.2) = 0.96
        assert retrieved.confidence == pytest.approx(0.96)

    def test_different_assertion_not_deduplicated(
        self, fact_service: DatabaseFactBuilderService
    ) -> None:
        """Test that facts with different assertions are not deduplicated."""
        fact_present = FactInput(
            patient_id="P001",
            domain=Domain.CONDITION,
            omop_concept_id=437663,
            concept_name="Fever",
            assertion=Assertion.PRESENT,
        )
        fact_absent = FactInput(
            patient_id="P001",
            domain=Domain.CONDITION,
            omop_concept_id=437663,
            concept_name="Fever",
            assertion=Assertion.ABSENT,
        )

        result1 = fact_service.create_fact(fact_present)
        result2 = fact_service.create_fact(fact_absent)

        # Different fact IDs
        assert result1.fact_id != result2.fact_id
        assert result1.is_new is True
        assert result2.is_new is True


class TestDomainFiltering:
    """Tests for domain filtering."""

    def test_get_facts_by_domain(self, fact_service: DatabaseFactBuilderService) -> None:
        """Test filtering facts by domain."""
        fact_service.create_fact(
            FactInput(
                patient_id="P001",
                domain=Domain.CONDITION,
                omop_concept_id=437663,
                concept_name="Fever",
            )
        )
        fact_service.create_fact(
            FactInput(
                patient_id="P001",
                domain=Domain.DRUG,
                omop_concept_id=1000000,
                concept_name="Aspirin",
            )
        )

        conditions = fact_service.get_facts_for_patient("P001", domain=Domain.CONDITION)
        assert len(conditions) == 1
        assert conditions[0].domain == Domain.CONDITION

        drugs = fact_service.get_facts_for_patient("P001", domain=Domain.DRUG)
        assert len(drugs) == 1
        assert drugs[0].domain == Domain.DRUG


class TestDatabaseFactBuilderExports:
    """Tests for module exports."""

    def test_database_fact_builder_exported(self) -> None:
        """Test that DatabaseFactBuilderService is exported."""
        from app.services import DatabaseFactBuilderService

        assert DatabaseFactBuilderService is not None
