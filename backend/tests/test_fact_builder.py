"""Tests for ClinicalFact builder service.

Tests task 6.x: Validates fact construction from mentions and
structured data, evidence linking, and negation handling.
"""

from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.models.clinical_fact import ClinicalFact, FactEvidence
from app.schemas.base import Assertion, Domain, Experiencer, Temporality
from app.schemas.clinical_fact import EvidenceType
from app.services.fact_builder import (
    BaseFactBuilderService,
    EvidenceInput,
    FactInput,
)
from app.services.fact_builder_db import DatabaseFactBuilderService

_fact_test_engine = create_engine(
    "sqlite:///:memory:",
    echo=False,
    future=True,
)
_FactTestSession = sessionmaker(
    bind=_fact_test_engine,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture(scope="function")
def fact_session() -> Session:
    """Create a database session with fact tables."""
    ClinicalFact.__table__.create(bind=_fact_test_engine, checkfirst=True)
    FactEvidence.__table__.create(bind=_fact_test_engine, checkfirst=True)

    session = _FactTestSession()
    try:
        yield session
    finally:
        session.close()
        FactEvidence.__table__.drop(bind=_fact_test_engine, checkfirst=True)
        ClinicalFact.__table__.drop(bind=_fact_test_engine, checkfirst=True)


class TestFactInput:
    """Tests for FactInput dataclass."""

    def test_create_fact_input(self) -> None:
        """Test creating a FactInput."""
        fact_input = FactInput(
            patient_id="P001",
            domain=Domain.CONDITION,
            omop_concept_id=437663,
            concept_name="Fever",
        )
        assert fact_input.patient_id == "P001"
        assert fact_input.domain == Domain.CONDITION
        assert fact_input.assertion == Assertion.PRESENT

    def test_fact_input_is_negated(self) -> None:
        """Test is_negated property."""
        fact_input = FactInput(
            patient_id="P001",
            domain=Domain.CONDITION,
            omop_concept_id=437663,
            concept_name="Fever",
            assertion=Assertion.ABSENT,
        )
        assert fact_input.is_negated is True

    def test_fact_input_is_uncertain(self) -> None:
        """Test is_uncertain property."""
        fact_input = FactInput(
            patient_id="P001",
            domain=Domain.CONDITION,
            omop_concept_id=437663,
            concept_name="Fever",
            assertion=Assertion.POSSIBLE,
        )
        assert fact_input.is_uncertain is True


class TestBaseFactBuilderService:
    """Tests for BaseFactBuilderService utilities."""

    def test_calculate_dedup_key(self) -> None:
        """Test deduplication key calculation."""
        builder = BaseFactBuilderService()
        key = builder.calculate_dedup_key(
            patient_id="P001",
            omop_concept_id=437663,
            assertion=Assertion.PRESENT,
            temporality=Temporality.CURRENT,
            experiencer=Experiencer.PATIENT,
        )
        assert key == "P001:437663:present:current:patient"

    def test_dedup_key_different_for_negated(self) -> None:
        """Test that negated findings have different dedup keys."""
        builder = BaseFactBuilderService()
        key_present = builder.calculate_dedup_key(
            patient_id="P001",
            omop_concept_id=437663,
            assertion=Assertion.PRESENT,
            temporality=Temporality.CURRENT,
            experiencer=Experiencer.PATIENT,
        )
        key_absent = builder.calculate_dedup_key(
            patient_id="P001",
            omop_concept_id=437663,
            assertion=Assertion.ABSENT,
            temporality=Temporality.CURRENT,
            experiencer=Experiencer.PATIENT,
        )
        assert key_present != key_absent

    def test_merge_confidence(self) -> None:
        """Test confidence merging formula."""
        builder = BaseFactBuilderService()
        merged = builder.merge_confidence(0.8, 0.7)
        # 1 - (1 - 0.8) * (1 - 0.7) = 1 - 0.2 * 0.3 = 0.94
        assert abs(merged - 0.94) < 0.01

    def test_should_preserve_negation(self) -> None:
        """Test negation preservation check."""
        builder = BaseFactBuilderService()
        assert builder.should_preserve_negation(Assertion.ABSENT) is True
        assert builder.should_preserve_negation(Assertion.PRESENT) is False
        assert builder.should_preserve_negation(Assertion.POSSIBLE) is False


class TestDatabaseFactBuilderService:
    """Tests for DatabaseFactBuilderService with database."""

    @pytest.fixture
    def service(self, fact_session: Session) -> DatabaseFactBuilderService:
        """Create a fact builder service."""
        return DatabaseFactBuilderService(fact_session)

    def test_create_fact_from_mention(
        self, service: DatabaseFactBuilderService, fact_session: Session
    ) -> None:
        """Test creating a fact from a mention."""
        mention_id = uuid4()
        result = service.create_fact_from_mention(
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
        assert result.fact_id is not None
        assert len(result.evidence_ids) == 1

        # Verify fact in database
        fact = fact_session.execute(
            select(ClinicalFact).where(ClinicalFact.id == str(result.fact_id))
        ).scalar_one()
        assert fact.patient_id == "P001"
        assert fact.concept_name == "Fever"
        assert fact.confidence == 0.95

    def test_create_fact_from_structured(
        self, service: DatabaseFactBuilderService, fact_session: Session
    ) -> None:
        """Test creating a fact from structured data."""
        source_id = uuid4()
        result = service.create_fact_from_structured(
            source_id=source_id,
            source_table="structured_resources",
            patient_id="P001",
            omop_concept_id=3004249,
            concept_name="Blood pressure",
            domain=Domain.MEASUREMENT,
            value="120/80",
            unit="mmHg",
        )

        assert result.is_new is True

        # Verify fact in database
        fact = fact_session.execute(
            select(ClinicalFact).where(ClinicalFact.id == str(result.fact_id))
        ).scalar_one()
        assert fact.value == "120/80"
        assert fact.unit == "mmHg"
        assert fact.confidence == 1.0  # Structured data high confidence

    def test_evidence_link_created(
        self, service: DatabaseFactBuilderService, fact_session: Session
    ) -> None:
        """Test that evidence links are created correctly."""
        mention_id = uuid4()
        result = service.create_fact_from_mention(
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

        # Verify evidence in database
        evidence = (
            fact_session.execute(
                select(FactEvidence).where(FactEvidence.fact_id == str(result.fact_id))
            )
            .scalars()
            .all()
        )
        assert len(evidence) == 1
        assert evidence[0].evidence_type == EvidenceType.MENTION
        assert evidence[0].source_table == "mentions"

    def test_negated_fact_preserved(
        self, service: DatabaseFactBuilderService, fact_session: Session
    ) -> None:
        """Test that negated findings are preserved (task 6.5)."""
        mention_id = uuid4()
        result = service.create_fact_from_mention(
            mention_id=mention_id,
            patient_id="P001",
            omop_concept_id=255848,
            concept_name="Pneumonia",
            domain=Domain.CONDITION,
            assertion=Assertion.ABSENT,  # NEGATED
            temporality=Temporality.CURRENT,
            experiencer=Experiencer.PATIENT,
            confidence=0.9,
        )

        # Verify negated fact exists in database
        fact = fact_session.execute(
            select(ClinicalFact).where(ClinicalFact.id == str(result.fact_id))
        ).scalar_one()
        assert fact.assertion == Assertion.ABSENT
        assert fact.is_negated is True

    def test_get_negated_facts(
        self, service: DatabaseFactBuilderService, fact_session: Session
    ) -> None:
        """Test retrieving negated facts for a patient."""
        # Create a present fact
        service.create_fact_from_mention(
            mention_id=uuid4(),
            patient_id="P001",
            omop_concept_id=437663,
            concept_name="Fever",
            domain=Domain.CONDITION,
            assertion=Assertion.PRESENT,
            temporality=Temporality.CURRENT,
            experiencer=Experiencer.PATIENT,
            confidence=0.95,
        )

        # Create a negated fact
        service.create_fact_from_mention(
            mention_id=uuid4(),
            patient_id="P001",
            omop_concept_id=255848,
            concept_name="Pneumonia",
            domain=Domain.CONDITION,
            assertion=Assertion.ABSENT,
            temporality=Temporality.CURRENT,
            experiencer=Experiencer.PATIENT,
            confidence=0.9,
        )

        fact_session.commit()

        # Get only negated facts
        negated = service.get_negated_facts_for_patient("P001")
        assert len(negated) == 1
        assert negated[0].concept_name == "Pneumonia"
        assert negated[0].is_negated is True

    def test_deduplication(
        self, service: DatabaseFactBuilderService, fact_session: Session
    ) -> None:
        """Test that duplicate facts are merged."""
        mention_id_1 = uuid4()
        mention_id_2 = uuid4()

        # Create first fact
        result1 = service.create_fact_from_mention(
            mention_id=mention_id_1,
            patient_id="P001",
            omop_concept_id=437663,
            concept_name="Fever",
            domain=Domain.CONDITION,
            assertion=Assertion.PRESENT,
            temporality=Temporality.CURRENT,
            experiencer=Experiencer.PATIENT,
            confidence=0.8,
        )

        # Create same fact from different mention
        result2 = service.create_fact_from_mention(
            mention_id=mention_id_2,
            patient_id="P001",
            omop_concept_id=437663,
            concept_name="Fever",
            domain=Domain.CONDITION,
            assertion=Assertion.PRESENT,
            temporality=Temporality.CURRENT,
            experiencer=Experiencer.PATIENT,
            confidence=0.7,
        )

        # Same fact ID
        assert result1.fact_id == result2.fact_id
        assert result2.is_new is False

        # Verify only one fact in database
        facts = (
            fact_session.execute(select(ClinicalFact).where(ClinicalFact.patient_id == "P001"))
            .scalars()
            .all()
        )
        assert len(facts) == 1

        # Confidence should be merged
        assert facts[0].confidence > 0.8

    def test_separate_facts_for_different_assertions(
        self, service: DatabaseFactBuilderService, fact_session: Session
    ) -> None:
        """Test that present and absent findings are separate facts."""
        # Create present fact
        result_present = service.create_fact_from_mention(
            mention_id=uuid4(),
            patient_id="P001",
            omop_concept_id=437663,
            concept_name="Fever",
            domain=Domain.CONDITION,
            assertion=Assertion.PRESENT,
            temporality=Temporality.CURRENT,
            experiencer=Experiencer.PATIENT,
            confidence=0.9,
        )

        # Create absent fact for same concept
        result_absent = service.create_fact_from_mention(
            mention_id=uuid4(),
            patient_id="P001",
            omop_concept_id=437663,
            concept_name="Fever",
            domain=Domain.CONDITION,
            assertion=Assertion.ABSENT,
            temporality=Temporality.CURRENT,
            experiencer=Experiencer.PATIENT,
            confidence=0.9,
        )

        # Should be different facts
        assert result_present.fact_id != result_absent.fact_id

    def test_family_history_separate_from_patient(
        self, service: DatabaseFactBuilderService, fact_session: Session
    ) -> None:
        """Test that family history is separate from patient facts."""
        # Patient condition
        result_patient = service.create_fact_from_mention(
            mention_id=uuid4(),
            patient_id="P001",
            omop_concept_id=4092879,
            concept_name="Colon cancer",
            domain=Domain.CONDITION,
            assertion=Assertion.PRESENT,
            temporality=Temporality.CURRENT,
            experiencer=Experiencer.PATIENT,
            confidence=0.9,
        )

        # Family history
        result_family = service.create_fact_from_mention(
            mention_id=uuid4(),
            patient_id="P001",
            omop_concept_id=4092879,
            concept_name="Colon cancer",
            domain=Domain.CONDITION,
            assertion=Assertion.PRESENT,
            temporality=Temporality.PAST,
            experiencer=Experiencer.FAMILY,
            confidence=0.9,
        )

        # Should be different facts
        assert result_patient.fact_id != result_family.fact_id

    def test_get_facts_for_patient(
        self, service: DatabaseFactBuilderService, fact_session: Session
    ) -> None:
        """Test retrieving all facts for a patient."""
        # Create multiple facts
        service.create_fact_from_mention(
            mention_id=uuid4(),
            patient_id="P001",
            omop_concept_id=437663,
            concept_name="Fever",
            domain=Domain.CONDITION,
            assertion=Assertion.PRESENT,
            temporality=Temporality.CURRENT,
            experiencer=Experiencer.PATIENT,
            confidence=0.95,
        )
        service.create_fact_from_mention(
            mention_id=uuid4(),
            patient_id="P001",
            omop_concept_id=1503297,
            concept_name="Metformin",
            domain=Domain.DRUG,
            assertion=Assertion.PRESENT,
            temporality=Temporality.CURRENT,
            experiencer=Experiencer.PATIENT,
            confidence=0.9,
        )

        fact_session.commit()

        # Get all facts
        facts = service.get_facts_for_patient("P001")
        assert len(facts) == 2

        # Filter by domain
        conditions = service.get_facts_for_patient("P001", domain=Domain.CONDITION)
        assert len(conditions) == 1
        assert conditions[0].concept_name == "Fever"

    def test_get_facts_exclude_negated(
        self, service: DatabaseFactBuilderService, fact_session: Session
    ) -> None:
        """Test excluding negated facts from results."""
        # Create present fact
        service.create_fact_from_mention(
            mention_id=uuid4(),
            patient_id="P001",
            omop_concept_id=437663,
            concept_name="Fever",
            domain=Domain.CONDITION,
            assertion=Assertion.PRESENT,
            temporality=Temporality.CURRENT,
            experiencer=Experiencer.PATIENT,
            confidence=0.95,
        )
        # Create negated fact
        service.create_fact_from_mention(
            mention_id=uuid4(),
            patient_id="P001",
            omop_concept_id=255848,
            concept_name="Pneumonia",
            domain=Domain.CONDITION,
            assertion=Assertion.ABSENT,
            temporality=Temporality.CURRENT,
            experiencer=Experiencer.PATIENT,
            confidence=0.9,
        )

        fact_session.commit()

        # Include negated
        all_facts = service.get_facts_for_patient("P001", include_negated=True)
        assert len(all_facts) == 2

        # Exclude negated
        present_facts = service.get_facts_for_patient("P001", include_negated=False)
        assert len(present_facts) == 1
        assert present_facts[0].concept_name == "Fever"

    def test_get_evidence_for_fact(
        self, service: DatabaseFactBuilderService, fact_session: Session
    ) -> None:
        """Test retrieving evidence for a fact."""
        mention_id = uuid4()
        result = service.create_fact_from_mention(
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

        evidence = service.get_evidence_for_fact(result.fact_id)
        assert len(evidence) == 1
        assert evidence[0].evidence_type == EvidenceType.MENTION
        assert evidence[0].source_id == mention_id

    def test_multiple_evidence_for_same_fact(
        self, service: DatabaseFactBuilderService, fact_session: Session
    ) -> None:
        """Test that multiple evidence sources are linked to one fact."""
        mention_id_1 = uuid4()
        mention_id_2 = uuid4()
        source_id = uuid4()

        # Create from mention
        result1 = service.create_fact_from_mention(
            mention_id=mention_id_1,
            patient_id="P001",
            omop_concept_id=437663,
            concept_name="Fever",
            domain=Domain.CONDITION,
            assertion=Assertion.PRESENT,
            temporality=Temporality.CURRENT,
            experiencer=Experiencer.PATIENT,
            confidence=0.8,
        )

        # Add evidence from another mention
        service.create_fact_from_mention(
            mention_id=mention_id_2,
            patient_id="P001",
            omop_concept_id=437663,
            concept_name="Fever",
            domain=Domain.CONDITION,
            assertion=Assertion.PRESENT,
            temporality=Temporality.CURRENT,
            experiencer=Experiencer.PATIENT,
            confidence=0.7,
        )

        # Add evidence from structured source
        service.create_fact(
            fact_input=FactInput(
                patient_id="P001",
                domain=Domain.CONDITION,
                omop_concept_id=437663,
                concept_name="Fever",
                assertion=Assertion.PRESENT,
                temporality=Temporality.CURRENT,
                experiencer=Experiencer.PATIENT,
                confidence=0.9,
            ),
            evidence=[
                EvidenceInput(
                    evidence_type=EvidenceType.STRUCTURED,
                    source_id=source_id,
                    source_table="structured_resources",
                )
            ],
        )

        # Get all evidence
        evidence = service.get_evidence_for_fact(result1.fact_id)
        assert len(evidence) == 3  # 2 mentions + 1 structured
