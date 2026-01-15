"""Tests for OMOP export API endpoint (task 9.4, 9.5).

These tests verify the export API functionality:
- GET /export/omop/{patient_id} endpoint
- Export response format
- OMOP schema compliance
- Negation preservation in exports
"""

import inspect

import pytest

from app.api.export import OMOPExportResponse, router
from app.services.export import NoteExport, NoteNLPExport


class TestExportEndpoint:
    """Tests for the GET /export/omop/{patient_id} endpoint."""

    def test_export_route_exists(self) -> None:
        """The export endpoint should be registered."""
        route_paths = [route.path for route in router.routes]
        # Routes include the full path with prefix
        assert any("omop/{patient_id}" in path for path in route_paths)

    def test_export_route_methods(self) -> None:
        """The export endpoint should accept GET requests."""
        for route in router.routes:
            if hasattr(route, "path") and "omop/{patient_id}" in route.path:
                assert "GET" in route.methods
                break
        else:
            pytest.fail("Export route not found")

    def test_export_route_has_query_params(self) -> None:
        """The export endpoint should accept query parameters for filtering."""
        for route in router.routes:
            if hasattr(route, "path") and "omop/{patient_id}" in route.path:
                endpoint_func = route.endpoint
                sig = inspect.signature(endpoint_func)
                param_names = list(sig.parameters.keys())
                assert "patient_id" in param_names
                assert "include_notes" in param_names
                assert "include_nlp" in param_names
                break
        else:
            pytest.fail("Export route not found")


class TestExportRouterConfiguration:
    """Tests for export API router configuration."""

    def test_router_prefix(self) -> None:
        """Test router has correct prefix."""
        assert router.prefix == "/export"

    def test_router_tags(self) -> None:
        """Test router has correct tags."""
        assert "Export" in router.tags


class TestOMOPExportResponseSchema:
    """Tests for OMOPExportResponse Pydantic model."""

    def test_response_required_fields(self) -> None:
        """Test response schema with required fields."""
        response = OMOPExportResponse(
            patient_id="P001",
            note_count=2,
            note_nlp_count=5,
        )
        assert response.patient_id == "P001"
        assert response.note_count == 2
        assert response.note_nlp_count == 5
        assert response.notes == []
        assert response.note_nlp_records == []
        assert response.export_format == "OMOP CDM v5.4"

    def test_response_serialization(self) -> None:
        """Test response serializes to dict correctly."""
        response = OMOPExportResponse(
            patient_id="P001",
            note_count=0,
            note_nlp_count=0,
        )
        data = response.model_dump()
        assert data["patient_id"] == "P001"
        assert data["export_format"] == "OMOP CDM v5.4"


class TestExportFunctionDefaults:
    """Tests for export function default values."""

    def test_include_notes_defaults_true(self) -> None:
        """Test include_notes defaults to True."""
        from app.api.export import export_patient_omop

        sig = inspect.signature(export_patient_omop)
        include_notes_param = sig.parameters["include_notes"]
        assert include_notes_param.default is True

    def test_include_nlp_defaults_true(self) -> None:
        """Test include_nlp defaults to True."""
        from app.api.export import export_patient_omop

        sig = inspect.signature(export_patient_omop)
        include_nlp_param = sig.parameters["include_nlp"]
        assert include_nlp_param.default is True


class TestOMOPNoteExportFormat:
    """Tests validating NOTE export format correctness."""

    def test_note_export_has_required_omop_fields(self) -> None:
        """Test NoteExport contains required OMOP NOTE fields."""
        fields = NoteExport.model_fields

        required_fields = [
            "note_id",
            "person_id",
            "note_date",
            "note_text",
            "note_type_concept_id",
        ]

        for field in required_fields:
            assert field in fields, f"Missing required OMOP NOTE field: {field}"

    def test_note_export_has_optional_omop_fields(self) -> None:
        """Test NoteExport contains optional OMOP NOTE fields."""
        fields = NoteExport.model_fields

        optional_fields = [
            "note_datetime",
            "note_title",
            "note_source_value",
            "language_concept_id",
        ]

        for field in optional_fields:
            assert field in fields, f"Missing optional OMOP NOTE field: {field}"


class TestOMOPNoteNLPExportFormat:
    """Tests validating NOTE_NLP export format correctness."""

    def test_note_nlp_export_has_required_omop_fields(self) -> None:
        """Test NoteNLPExport contains required OMOP NOTE_NLP fields."""
        fields = NoteNLPExport.model_fields

        required_fields = [
            "note_nlp_id",
            "note_id",
            "snippet",
            "offset",
            "lexical_variant",
            "note_nlp_concept_id",
            "nlp_date",
        ]

        for field in required_fields:
            assert field in fields, f"Missing required OMOP NOTE_NLP field: {field}"

    def test_note_nlp_export_has_assertion_fields(self) -> None:
        """Test NOTE_NLP export has assertion-related fields.

        These fields are essential for preserving clinical context:
        - term_exists: Y/N for present/negated
        - term_temporal: Historical, Current, Future
        - term_modifiers: Additional context (experiencer, confidence)
        """
        fields = NoteNLPExport.model_fields

        assert "term_exists" in fields, "Missing term_exists for negation"
        assert "term_temporal" in fields, "Missing term_temporal"
        assert "term_modifiers" in fields, "Missing term_modifiers"

    def test_note_nlp_export_term_exists_default(self) -> None:
        """Test term_exists defaults to 'Y' (present)."""
        fields = NoteNLPExport.model_fields
        assert fields["term_exists"].default == "Y"

    def test_note_nlp_export_nlp_system_default(self) -> None:
        """Test nlp_system identifies our system."""
        fields = NoteNLPExport.model_fields
        assert fields["nlp_system"].default == "clinical_ontology_normalizer"


class TestNegationPreservation:
    """Tests ensuring negated findings are preserved in export.

    IMPORTANT: Negated findings (assertion=absent) must be exported
    with term_exists='N' to preserve clinical meaning in OMOP format.
    """

    def test_absent_assertion_maps_to_n(self) -> None:
        """Test absent assertion converts to term_exists='N'."""
        from app.services.export import BaseOMOPExporter

        assert BaseOMOPExporter.assertion_to_term_exists("absent") == "N"
        assert BaseOMOPExporter.assertion_to_term_exists("ABSENT") == "N"

    def test_present_assertion_maps_to_y(self) -> None:
        """Test present assertion converts to term_exists='Y'."""
        from app.services.export import BaseOMOPExporter

        assert BaseOMOPExporter.assertion_to_term_exists("present") == "Y"

    def test_possible_assertion_maps_to_y(self) -> None:
        """Test possible assertion converts to term_exists='Y'."""
        from app.services.export import BaseOMOPExporter

        assert BaseOMOPExporter.assertion_to_term_exists("possible") == "Y"
