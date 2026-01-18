"""ETL (Extract-Transform-Load) Services for OMOP CDM.

This module provides services for transforming data from various clinical
source formats into the OMOP Common Data Model (CDM).

Architecture:
    SourceConnector → SourceRecord → ETL Service → OMOP Table

Modules:
    - person_etl: Transforms SourcePatient → Person table
    - visit_etl: Transforms SourceVisit → VisitOccurrence table
    - condition_etl: Transforms SourceCondition → ConditionOccurrence table
    - drug_etl: Transforms SourceDrug → DrugExposure table
    - measurement_etl: Transforms SourceMeasurement → Measurement table

Usage:
    from app.etl import PersonETL, VisitETL, ConditionETL
    from app.connectors import CCDAConnector, CCDAConnectorConfig

    # Extract from source
    connector = CCDAConnector(CCDAConnectorConfig(documents_path="/data"))

    # Transform and load
    person_etl = PersonETL(db_session)
    visit_etl = VisitETL(db_session)

    async for patient in connector.extract_patients():
        person = await person_etl.transform_and_load(patient)
        print(f"Created person_id={person.person_id}")

    async for visit in connector.extract_visits():
        visit_occ = await visit_etl.transform_and_load(visit, person_id=person.person_id)
"""

from app.etl.condition_etl import (
    ConditionETL,
    ConditionETLConfig,
    ConditionETLResult,
)
from app.etl.death_etl import (
    DeathETL,
    DeathETLConfig,
    DeathETLResult,
    SourceDeath,
)
from app.etl.drug_etl import (
    DrugETL,
    DrugETLConfig,
    DrugETLResult,
)
from app.etl.measurement_etl import (
    MeasurementETL,
    MeasurementETLConfig,
    MeasurementETLResult,
)
from app.etl.observation_etl import (
    ObservationETL,
    ObservationETLConfig,
    ObservationETLResult,
)
from app.etl.person_etl import (
    PersonETL,
    PersonETLConfig,
    PersonETLResult,
    get_person_etl_service,
)
from app.etl.procedure_etl import (
    ProcedureETL,
    ProcedureETLConfig,
    ProcedureETLResult,
)
from app.etl.visit_etl import (
    VisitETL,
    VisitETLConfig,
    VisitETLResult,
)

__all__ = [
    # Person ETL
    "PersonETL",
    "PersonETLConfig",
    "PersonETLResult",
    "get_person_etl_service",
    # Visit ETL
    "VisitETL",
    "VisitETLConfig",
    "VisitETLResult",
    # Condition ETL
    "ConditionETL",
    "ConditionETLConfig",
    "ConditionETLResult",
    # Death ETL
    "DeathETL",
    "DeathETLConfig",
    "DeathETLResult",
    "SourceDeath",
    # Drug ETL
    "DrugETL",
    "DrugETLConfig",
    "DrugETLResult",
    # Procedure ETL
    "ProcedureETL",
    "ProcedureETLConfig",
    "ProcedureETLResult",
    # Measurement ETL
    "MeasurementETL",
    "MeasurementETLConfig",
    "MeasurementETLResult",
    # Observation ETL
    "ObservationETL",
    "ObservationETLConfig",
    "ObservationETLResult",
]
