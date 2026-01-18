"""Source Data Connectors for ETL Pipeline.

This module provides a pluggable architecture for connecting to various
clinical data sources (FHIR, HL7, C-CDA, CSV, databases) and extracting
data into a standardized intermediate format for OMOP CDM transformation.

Architecture:
    SourceConnector (abstract base)
        ├── FHIRConnector - FHIR R4 servers (planned)
        ├── HL7v2Connector - HL7 v2.x messages ✓
        ├── CCDAConnector - C-CDA/CDA documents ✓
        ├── CSVConnector - CSV/flat files ✓
        └── DatabaseConnector - SQL databases (planned)

Usage:
    from app.connectors import CCDAConnector, CCDAConnectorConfig, SourcePatient

    config = CCDAConnectorConfig(documents_path="/path/to/ccda/files")
    connector = CCDAConnector(config)
    async for patient in connector.extract_patients():
        print(patient.source_id, patient.given_name, patient.family_name)
"""

from app.connectors.base import (
    ConditionStatus,
    ConnectorConfig,
    ConnectorType,
    DrugStatus,
    ExtractionResult,
    Gender,
    ProcedureStatus,
    SourceCondition,
    SourceConnector,
    SourceDrug,
    SourceMeasurement,
    SourceObservation,
    SourcePatient,
    SourceProcedure,
    SourceRecord,
    SourceVisit,
    VisitType,
)
from app.connectors.ccda_connector import CCDAConnector, CCDAConnectorConfig
from app.connectors.csv_connector import CSVConnector, CSVConnectorConfig
from app.connectors.hl7v2_connector import HL7v2Connector, HL7v2ConnectorConfig

__all__ = [
    # Base classes and enums
    "ConditionStatus",
    "ConnectorConfig",
    "ConnectorType",
    "DrugStatus",
    "ExtractionResult",
    "Gender",
    "ProcedureStatus",
    "SourceCondition",
    "SourceConnector",
    "SourceDrug",
    "SourceMeasurement",
    "SourceObservation",
    "SourcePatient",
    "SourceProcedure",
    "SourceRecord",
    "SourceVisit",
    "VisitType",
    # C-CDA Connector
    "CCDAConnector",
    "CCDAConnectorConfig",
    # CSV Connector
    "CSVConnector",
    "CSVConnectorConfig",
    # HL7 v2 Connector
    "HL7v2Connector",
    "HL7v2ConnectorConfig",
]
