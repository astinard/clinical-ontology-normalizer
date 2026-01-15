"""Tests for Document and StructuredResource models."""

from uuid import UUID

from app.models import Document, StructuredResource
from app.schemas.base import JobStatus, ResourceType


class TestDocumentModel:
    """Test Document model class."""

    def test_document_inherits_base(self) -> None:
        """Test that Document inherits from Base."""
        from app.core.database import Base

        assert issubclass(Document, Base)

    def test_document_tablename(self) -> None:
        """Test Document has correct table name."""
        assert Document.__tablename__ == "documents"

    def test_document_has_required_columns(self) -> None:
        """Test Document has all required columns."""
        columns = Document.__table__.c
        # Note: 'metadata' is the DB column name, mapped to 'extra_metadata' in Python
        required_columns = [
            "id",
            "created_at",
            "patient_id",
            "note_type",
            "text",
            "metadata",
            "status",
            "processed_at",
        ]
        for col in required_columns:
            assert col in columns, f"Missing column: {col}"

    def test_document_patient_id_indexed(self) -> None:
        """Test patient_id column is indexed."""
        patient_id_col = Document.__table__.c.patient_id
        assert patient_id_col.index is True

    def test_document_status_indexed(self) -> None:
        """Test status column is indexed."""
        status_col = Document.__table__.c.status
        assert status_col.index is True

    def test_create_document_instance(self) -> None:
        """Test creating a Document instance."""
        doc = Document(
            patient_id="P001",
            note_type="progress_note",
            text="Patient presents with chest pain.",
            extra_metadata={"author": "Dr. Smith"},
        )
        assert doc.patient_id == "P001"
        assert doc.note_type == "progress_note"
        assert doc.text == "Patient presents with chest pain."
        assert doc.extra_metadata == {"author": "Dr. Smith"}

    def test_document_default_status_column(self) -> None:
        """Test Document status column has QUEUED as default."""
        # SQLAlchemy defaults are applied at DB insert time, not Python instantiation
        status_col = Document.__table__.c.status
        assert status_col.default is not None
        assert status_col.default.arg == JobStatus.QUEUED

    def test_document_status_can_be_set(self) -> None:
        """Test Document status can be explicitly set."""
        doc = Document(
            patient_id="P001",
            note_type="progress_note",
            text="Test note",
            status=JobStatus.COMPLETED,
        )
        assert doc.status == JobStatus.COMPLETED

    def test_document_processed_at_nullable(self) -> None:
        """Test processed_at is nullable."""
        processed_at_col = Document.__table__.c.processed_at
        assert processed_at_col.nullable is True

    def test_document_text_is_text_type(self) -> None:
        """Test text column uses TEXT type for large content."""
        text_col = Document.__table__.c.text
        assert "TEXT" in str(text_col.type).upper()

    def test_document_metadata_is_jsonb(self) -> None:
        """Test metadata column uses JSONB type."""
        # Column name is 'metadata' in DB, mapped to 'extra_metadata' in Python
        metadata_col = Document.__table__.c.metadata
        assert "JSONB" in str(metadata_col.type).upper()

    def test_document_repr(self) -> None:
        """Test Document __repr__ method."""
        doc = Document(
            id="550e8400-e29b-41d4-a716-446655440000",
            patient_id="P001",
            note_type="progress_note",
            text="Test",
        )
        repr_str = repr(doc)
        assert "Document" in repr_str
        assert "P001" in repr_str
        assert "progress_note" in repr_str

    def test_document_id_is_uuid(self) -> None:
        """Test Document id is valid UUID format."""
        doc = Document(
            id="550e8400-e29b-41d4-a716-446655440000",
            patient_id="P001",
            note_type="progress_note",
            text="Test",
        )
        UUID(doc.id)  # Will raise if not valid UUID


class TestStructuredResourceModel:
    """Test StructuredResource model class."""

    def test_structured_resource_inherits_base(self) -> None:
        """Test that StructuredResource inherits from Base."""
        from app.core.database import Base

        assert issubclass(StructuredResource, Base)

    def test_structured_resource_tablename(self) -> None:
        """Test StructuredResource has correct table name."""
        assert StructuredResource.__tablename__ == "structured_resources"

    def test_structured_resource_has_required_columns(self) -> None:
        """Test StructuredResource has all required columns."""
        columns = StructuredResource.__table__.c
        # Note: 'metadata' is the DB column name, mapped to 'extra_metadata' in Python
        required_columns = [
            "id",
            "created_at",
            "patient_id",
            "resource_type",
            "payload",
            "metadata",
            "status",
            "processed_at",
        ]
        for col in required_columns:
            assert col in columns, f"Missing column: {col}"

    def test_structured_resource_patient_id_indexed(self) -> None:
        """Test patient_id column is indexed."""
        patient_id_col = StructuredResource.__table__.c.patient_id
        assert patient_id_col.index is True

    def test_structured_resource_status_indexed(self) -> None:
        """Test status column is indexed."""
        status_col = StructuredResource.__table__.c.status
        assert status_col.index is True

    def test_create_structured_resource_fhir(self) -> None:
        """Test creating a StructuredResource with FHIR bundle."""
        resource = StructuredResource(
            patient_id="P001",
            resource_type=ResourceType.FHIR_BUNDLE,
            payload={"resourceType": "Bundle", "entry": []},
            extra_metadata={"source": "EHR"},
        )
        assert resource.patient_id == "P001"
        assert resource.resource_type == ResourceType.FHIR_BUNDLE
        assert resource.payload == {"resourceType": "Bundle", "entry": []}

    def test_create_structured_resource_csv(self) -> None:
        """Test creating a StructuredResource with CSV data."""
        resource = StructuredResource(
            patient_id="P001",
            resource_type=ResourceType.CSV,
            payload={"rows": [{"col1": "val1"}]},
        )
        assert resource.resource_type == ResourceType.CSV

    def test_structured_resource_default_status_column(self) -> None:
        """Test StructuredResource status column has QUEUED as default."""
        # SQLAlchemy defaults are applied at DB insert time, not Python instantiation
        status_col = StructuredResource.__table__.c.status
        assert status_col.default is not None
        assert status_col.default.arg == JobStatus.QUEUED

    def test_structured_resource_payload_is_jsonb(self) -> None:
        """Test payload column uses JSONB type."""
        payload_col = StructuredResource.__table__.c.payload
        assert "JSONB" in str(payload_col.type).upper()

    def test_structured_resource_repr(self) -> None:
        """Test StructuredResource __repr__ method."""
        resource = StructuredResource(
            id="550e8400-e29b-41d4-a716-446655440000",
            patient_id="P001",
            resource_type=ResourceType.FHIR_BUNDLE,
            payload={},
        )
        repr_str = repr(resource)
        assert "StructuredResource" in repr_str
        assert "P001" in repr_str
        assert "FHIR_BUNDLE" in repr_str  # Enum repr shows ResourceType.FHIR_BUNDLE


class TestModelExports:
    """Test model exports from package."""

    def test_document_exported(self) -> None:
        """Test Document is exported from models package."""
        from app.models import Document

        assert Document is not None

    def test_structured_resource_exported(self) -> None:
        """Test StructuredResource is exported from models package."""
        from app.models import StructuredResource

        assert StructuredResource is not None

    def test_all_exports(self) -> None:
        """Test __all__ contains expected exports."""
        from app import models

        assert "Document" in models.__all__
        assert "StructuredResource" in models.__all__
        assert "Base" in models.__all__
