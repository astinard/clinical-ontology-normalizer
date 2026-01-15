"""Tests for GraphBuilderService interface and base class.

Tests the abstract interface, dataclasses, and base utilities
for knowledge graph materialization (task 7.1).
"""

import pytest

from app.schemas.base import Domain
from app.schemas.knowledge_graph import EdgeType, NodeType
from app.services.graph_builder import (
    BaseGraphBuilderService,
    EdgeInput,
    GraphBuilderServiceInterface,
    GraphResult,
    NodeInput,
)


class TestNodeInput:
    """Tests for NodeInput dataclass."""

    def test_node_input_required_fields(self) -> None:
        """Test NodeInput with required fields only."""
        node = NodeInput(
            patient_id="P001",
            node_type=NodeType.CONDITION,
            label="Fever",
        )
        assert node.patient_id == "P001"
        assert node.node_type == NodeType.CONDITION
        assert node.label == "Fever"

    def test_node_input_with_concept_id(self) -> None:
        """Test NodeInput with OMOP concept ID."""
        node = NodeInput(
            patient_id="P001",
            node_type=NodeType.CONDITION,
            label="Fever",
            omop_concept_id=437663,
        )
        assert node.omop_concept_id == 437663

    def test_node_input_with_properties(self) -> None:
        """Test NodeInput with custom properties."""
        node = NodeInput(
            patient_id="P001",
            node_type=NodeType.CONDITION,
            label="Fever",
            properties={"assertion": "present", "severity": "high"},
        )
        assert node.properties == {"assertion": "present", "severity": "high"}

    def test_node_input_default_properties(self) -> None:
        """Test that properties default to empty dict."""
        node = NodeInput(
            patient_id="P001",
            node_type=NodeType.PATIENT,
            label="Patient P001",
        )
        assert node.properties == {}
        assert node.omop_concept_id is None


class TestEdgeInput:
    """Tests for EdgeInput dataclass."""

    def test_edge_input_required_fields(self) -> None:
        """Test EdgeInput with required fields."""
        from uuid import uuid4

        source_id = uuid4()
        target_id = uuid4()

        edge = EdgeInput(
            patient_id="P001",
            source_node_id=source_id,
            target_node_id=target_id,
            edge_type=EdgeType.HAS_CONDITION,
        )
        assert edge.patient_id == "P001"
        assert edge.source_node_id == source_id
        assert edge.target_node_id == target_id
        assert edge.edge_type == EdgeType.HAS_CONDITION

    def test_edge_input_with_fact_id(self) -> None:
        """Test EdgeInput with fact ID."""
        from uuid import uuid4

        source_id = uuid4()
        target_id = uuid4()
        fact_id = uuid4()

        edge = EdgeInput(
            patient_id="P001",
            source_node_id=source_id,
            target_node_id=target_id,
            edge_type=EdgeType.HAS_CONDITION,
            fact_id=fact_id,
        )
        assert edge.fact_id == fact_id

    def test_edge_input_with_properties(self) -> None:
        """Test EdgeInput with custom properties."""
        from uuid import uuid4

        edge = EdgeInput(
            patient_id="P001",
            source_node_id=uuid4(),
            target_node_id=uuid4(),
            edge_type=EdgeType.TAKES_DRUG,
            properties={"dose": "100mg"},
        )
        assert edge.properties == {"dose": "100mg"}


class TestGraphResult:
    """Tests for GraphResult dataclass."""

    def test_graph_result_defaults(self) -> None:
        """Test GraphResult with default values."""
        result = GraphResult(patient_id="P001")
        assert result.patient_id == "P001"
        assert result.node_count == 0
        assert result.edge_count == 0
        assert result.nodes_created == 0
        assert result.edges_created == 0

    def test_graph_result_with_counts(self) -> None:
        """Test GraphResult with counts."""
        result = GraphResult(
            patient_id="P001",
            node_count=5,
            edge_count=4,
            nodes_created=3,
            edges_created=2,
        )
        assert result.node_count == 5
        assert result.edge_count == 4
        assert result.nodes_created == 3
        assert result.edges_created == 2


class TestBaseGraphBuilderService:
    """Tests for BaseGraphBuilderService utilities."""

    def test_domain_to_node_type_condition(self) -> None:
        """Test mapping CONDITION domain to node type."""
        service = BaseGraphBuilderService()
        node_type = service.domain_to_node_type(Domain.CONDITION)
        assert node_type == NodeType.CONDITION

    def test_domain_to_node_type_drug(self) -> None:
        """Test mapping DRUG domain to node type."""
        service = BaseGraphBuilderService()
        node_type = service.domain_to_node_type(Domain.DRUG)
        assert node_type == NodeType.DRUG

    def test_domain_to_node_type_measurement(self) -> None:
        """Test mapping MEASUREMENT domain to node type."""
        service = BaseGraphBuilderService()
        node_type = service.domain_to_node_type(Domain.MEASUREMENT)
        assert node_type == NodeType.MEASUREMENT

    def test_domain_to_node_type_procedure(self) -> None:
        """Test mapping PROCEDURE domain to node type."""
        service = BaseGraphBuilderService()
        node_type = service.domain_to_node_type(Domain.PROCEDURE)
        assert node_type == NodeType.PROCEDURE

    def test_domain_to_node_type_observation(self) -> None:
        """Test mapping OBSERVATION domain to node type."""
        service = BaseGraphBuilderService()
        node_type = service.domain_to_node_type(Domain.OBSERVATION)
        assert node_type == NodeType.OBSERVATION

    def test_domain_to_node_type_device_falls_back(self) -> None:
        """Test that DEVICE domain maps to OBSERVATION node type."""
        service = BaseGraphBuilderService()
        node_type = service.domain_to_node_type(Domain.DEVICE)
        assert node_type == NodeType.OBSERVATION

    def test_domain_to_edge_type_condition(self) -> None:
        """Test mapping CONDITION domain to edge type."""
        service = BaseGraphBuilderService()
        edge_type = service.domain_to_edge_type(Domain.CONDITION)
        assert edge_type == EdgeType.HAS_CONDITION

    def test_domain_to_edge_type_drug(self) -> None:
        """Test mapping DRUG domain to edge type."""
        service = BaseGraphBuilderService()
        edge_type = service.domain_to_edge_type(Domain.DRUG)
        assert edge_type == EdgeType.TAKES_DRUG

    def test_domain_to_edge_type_measurement(self) -> None:
        """Test mapping MEASUREMENT domain to edge type."""
        service = BaseGraphBuilderService()
        edge_type = service.domain_to_edge_type(Domain.MEASUREMENT)
        assert edge_type == EdgeType.HAS_MEASUREMENT

    def test_domain_to_edge_type_procedure(self) -> None:
        """Test mapping PROCEDURE domain to edge type."""
        service = BaseGraphBuilderService()
        edge_type = service.domain_to_edge_type(Domain.PROCEDURE)
        assert edge_type == EdgeType.HAS_PROCEDURE

    def test_domain_to_edge_type_observation(self) -> None:
        """Test mapping OBSERVATION domain to edge type."""
        service = BaseGraphBuilderService()
        edge_type = service.domain_to_edge_type(Domain.OBSERVATION)
        assert edge_type == EdgeType.HAS_OBSERVATION

    def test_calculate_node_dedup_key(self) -> None:
        """Test deduplication key calculation."""
        service = BaseGraphBuilderService()
        key = service.calculate_node_dedup_key(
            patient_id="P001",
            node_type=NodeType.CONDITION,
            omop_concept_id=437663,
        )
        assert key == "P001:condition:437663"

    def test_calculate_node_dedup_key_patient(self) -> None:
        """Test deduplication key for patient node."""
        service = BaseGraphBuilderService()
        key = service.calculate_node_dedup_key(
            patient_id="P001",
            node_type=NodeType.PATIENT,
            omop_concept_id=None,
        )
        assert key == "P001:patient:patient"


class TestGraphBuilderServiceInterface:
    """Tests for interface compliance."""

    def test_interface_is_abstract(self) -> None:
        """Test that interface cannot be instantiated."""
        with pytest.raises(TypeError):
            GraphBuilderServiceInterface()  # type: ignore

    def test_base_class_raises_not_implemented(self) -> None:
        """Test that base class methods raise NotImplementedError."""
        service = BaseGraphBuilderService()

        with pytest.raises(NotImplementedError):
            service.create_patient_node("P001")

        with pytest.raises(NotImplementedError):
            service.create_node(
                NodeInput(
                    patient_id="P001",
                    node_type=NodeType.CONDITION,
                    label="Fever",
                )
            )

        with pytest.raises(NotImplementedError):
            from uuid import uuid4

            service.create_edge(
                EdgeInput(
                    patient_id="P001",
                    source_node_id=uuid4(),
                    target_node_id=uuid4(),
                    edge_type=EdgeType.HAS_CONDITION,
                )
            )

        with pytest.raises(NotImplementedError):
            from uuid import uuid4

            service.project_fact_to_graph(
                fact_id=uuid4(),
                patient_id="P001",
                domain=Domain.CONDITION,
                omop_concept_id=437663,
                concept_name="Fever",
                assertion="present",
                temporality="current",
                experiencer="patient",
            )

        with pytest.raises(NotImplementedError):
            service.build_graph_for_patient("P001")


class TestModuleExports:
    """Tests for module exports."""

    def test_graph_builder_interface_exported(self) -> None:
        """Test that GraphBuilderServiceInterface is exported."""
        from app.services import GraphBuilderServiceInterface

        assert GraphBuilderServiceInterface is not None

    def test_base_graph_builder_exported(self) -> None:
        """Test that BaseGraphBuilderService is exported."""
        from app.services import BaseGraphBuilderService

        assert BaseGraphBuilderService is not None

    def test_node_input_exported(self) -> None:
        """Test that NodeInput is exported."""
        from app.services import NodeInput

        assert NodeInput is not None

    def test_edge_input_exported(self) -> None:
        """Test that EdgeInput is exported."""
        from app.services import EdgeInput

        assert EdgeInput is not None

    def test_graph_result_exported(self) -> None:
        """Test that GraphResult is exported."""
        from app.services import GraphResult

        assert GraphResult is not None
