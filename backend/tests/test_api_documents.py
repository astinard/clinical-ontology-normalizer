"""Tests for document API endpoints."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.main import app
from app.schemas import JobStatus


class TestDocumentUpload:
    """Test document upload endpoint."""

    @pytest.fixture
    def valid_document_payload(self) -> dict:
        """Valid document upload payload."""
        return {
            "patient_id": "patient-123",
            "note_type": "progress_note",
            "text": "Patient presents with fever and cough for 3 days.",
            "metadata": {"encounter_date": "2026-01-14"},
        }

    @pytest.mark.asyncio
    async def test_upload_document_returns_201(
        self,
        client_with_mock_db: AsyncClient,
        mock_db_session: MagicMock,
        valid_document_payload: dict,
    ) -> None:
        """Test document upload returns 201 Created."""
        # Mock the document ID that would be assigned by the database
        mock_db_session.add = MagicMock(
            side_effect=lambda doc: setattr(doc, "id", str(uuid4()))
        )

        response = await client_with_mock_db.post(
            "/documents",
            json=valid_document_payload,
        )
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_upload_document_returns_document_id(
        self,
        client_with_mock_db: AsyncClient,
        mock_db_session: MagicMock,
        valid_document_payload: dict,
    ) -> None:
        """Test upload response contains document_id."""
        mock_db_session.add = MagicMock(
            side_effect=lambda doc: setattr(doc, "id", str(uuid4()))
        )

        response = await client_with_mock_db.post(
            "/documents",
            json=valid_document_payload,
        )
        data = response.json()
        assert "document_id" in data
        # Should be a valid UUID string
        assert len(data["document_id"]) == 36

    @pytest.mark.asyncio
    async def test_upload_document_returns_job_id(
        self,
        client_with_mock_db: AsyncClient,
        mock_db_session: MagicMock,
        valid_document_payload: dict,
    ) -> None:
        """Test upload response contains job_id."""
        mock_db_session.add = MagicMock(
            side_effect=lambda doc: setattr(doc, "id", str(uuid4()))
        )

        response = await client_with_mock_db.post(
            "/documents",
            json=valid_document_payload,
        )
        data = response.json()
        assert "job_id" in data
        # Should be a valid UUID string
        assert len(data["job_id"]) == 36

    @pytest.mark.asyncio
    async def test_upload_document_returns_queued_status(
        self,
        client_with_mock_db: AsyncClient,
        mock_db_session: MagicMock,
        valid_document_payload: dict,
    ) -> None:
        """Test upload response has QUEUED status."""
        mock_db_session.add = MagicMock(
            side_effect=lambda doc: setattr(doc, "id", str(uuid4()))
        )

        response = await client_with_mock_db.post(
            "/documents",
            json=valid_document_payload,
        )
        data = response.json()
        assert data["status"] == JobStatus.QUEUED.value

    @pytest.mark.asyncio
    async def test_upload_document_calls_db_add(
        self,
        client_with_mock_db: AsyncClient,
        mock_db_session: MagicMock,
        valid_document_payload: dict,
    ) -> None:
        """Test that document is added to database session."""
        mock_db_session.add = MagicMock(
            side_effect=lambda doc: setattr(doc, "id", str(uuid4()))
        )

        await client_with_mock_db.post(
            "/documents",
            json=valid_document_payload,
        )
        assert mock_db_session.add.called

    @pytest.mark.asyncio
    async def test_upload_document_calls_db_flush(
        self,
        client_with_mock_db: AsyncClient,
        mock_db_session: MagicMock,
        valid_document_payload: dict,
    ) -> None:
        """Test that database flush is called to get document ID."""
        mock_db_session.add = MagicMock(
            side_effect=lambda doc: setattr(doc, "id", str(uuid4()))
        )

        await client_with_mock_db.post(
            "/documents",
            json=valid_document_payload,
        )
        assert mock_db_session.flush.called

    @pytest.mark.asyncio
    async def test_upload_document_missing_patient_id_returns_422(
        self,
        client_with_mock_db: AsyncClient,
    ) -> None:
        """Test upload without patient_id returns validation error."""
        payload = {
            "note_type": "progress_note",
            "text": "Patient presents with fever.",
        }
        response = await client_with_mock_db.post("/documents", json=payload)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_upload_document_missing_note_type_returns_422(
        self,
        client_with_mock_db: AsyncClient,
    ) -> None:
        """Test upload without note_type returns validation error."""
        payload = {
            "patient_id": "patient-123",
            "text": "Patient presents with fever.",
        }
        response = await client_with_mock_db.post("/documents", json=payload)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_upload_document_missing_text_returns_422(
        self,
        client_with_mock_db: AsyncClient,
    ) -> None:
        """Test upload without text returns validation error."""
        payload = {
            "patient_id": "patient-123",
            "note_type": "progress_note",
        }
        response = await client_with_mock_db.post("/documents", json=payload)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_upload_document_empty_text_allowed(
        self,
        client_with_mock_db: AsyncClient,
        mock_db_session: MagicMock,
    ) -> None:
        """Test upload with empty text is allowed (edge case)."""
        mock_db_session.add = MagicMock(
            side_effect=lambda doc: setattr(doc, "id", str(uuid4()))
        )

        payload = {
            "patient_id": "patient-123",
            "note_type": "progress_note",
            "text": "",
        }
        response = await client_with_mock_db.post("/documents", json=payload)
        # Empty string is technically valid
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_upload_document_without_metadata_uses_default(
        self,
        client_with_mock_db: AsyncClient,
        mock_db_session: MagicMock,
    ) -> None:
        """Test upload without metadata uses empty dict default."""
        mock_db_session.add = MagicMock(
            side_effect=lambda doc: setattr(doc, "id", str(uuid4()))
        )

        payload = {
            "patient_id": "patient-123",
            "note_type": "progress_note",
            "text": "Patient presents with fever.",
        }
        response = await client_with_mock_db.post("/documents", json=payload)
        assert response.status_code == 201


class TestDocumentUploadWithSyntheticNotes:
    """Test document upload with synthetic clinical notes."""

    @pytest.mark.asyncio
    async def test_upload_pneumonia_note(
        self,
        client_with_mock_db: AsyncClient,
        mock_db_session: MagicMock,
    ) -> None:
        """Test uploading a pneumonia clinical note."""
        mock_db_session.add = MagicMock(
            side_effect=lambda doc: setattr(doc, "id", str(uuid4()))
        )

        payload = {
            "patient_id": "patient-001",
            "note_type": "progress_note",
            "text": """
            Chief Complaint: Fever and productive cough for 3 days.

            History of Present Illness:
            68-year-old male presents with fever, productive cough with yellowish
            sputum, and shortness of breath. No hemoptysis. Denies chest pain.

            Assessment:
            Community-acquired pneumonia.

            Plan:
            Start azithromycin 500mg PO daily for 5 days.
            """,
            "metadata": {"encounter_type": "outpatient"},
        }
        response = await client_with_mock_db.post("/documents", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "queued"

    @pytest.mark.asyncio
    async def test_upload_discharge_summary(
        self,
        client_with_mock_db: AsyncClient,
        mock_db_session: MagicMock,
    ) -> None:
        """Test uploading a discharge summary note."""
        mock_db_session.add = MagicMock(
            side_effect=lambda doc: setattr(doc, "id", str(uuid4()))
        )

        payload = {
            "patient_id": "patient-002",
            "note_type": "discharge_summary",
            "text": """
            Discharge Summary

            Admission Diagnosis: Acute exacerbation of congestive heart failure
            Discharge Diagnosis: Congestive heart failure, compensated

            Hospital Course:
            Patient was admitted with dyspnea and lower extremity edema.
            Treated with IV furosemide with good diuresis.
            BNP improved from 1500 to 400.

            Discharge Medications:
            - Furosemide 40mg PO BID
            - Lisinopril 10mg PO daily
            - Metoprolol 25mg PO BID
            """,
            "metadata": {"admission_date": "2026-01-10", "discharge_date": "2026-01-14"},
        }
        response = await client_with_mock_db.post("/documents", json=payload)
        assert response.status_code == 201
