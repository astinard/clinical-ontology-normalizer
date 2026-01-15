"""Tests for KGNode and KGEdge models."""

from app.models import KGEdge, KGNode
from app.schemas.knowledge_graph import EdgeType, NodeType


class TestKGNodeModel:
    """Test KGNode model class."""

    def test_kg_node_inherits_base(self) -> None:
        """Test that KGNode inherits from Base."""
        from app.core.database import Base

        assert issubclass(KGNode, Base)

    def test_kg_node_tablename(self) -> None:
        """Test KGNode has correct table name."""
        assert KGNode.__tablename__ == "kg_nodes"

    def test_kg_node_has_required_columns(self) -> None:
        """Test KGNode has all required columns."""
        columns = KGNode.__table__.c
        required_columns = [
            "id", "created_at", "patient_id", "node_type",
            "omop_concept_id", "label", "properties"
        ]
        for col in required_columns:
            assert col in columns, f"Missing column: {col}"

    def test_kg_node_patient_id_indexed(self) -> None:
        """Test patient_id column is indexed."""
        patient_id_col = KGNode.__table__.c.patient_id
        assert patient_id_col.index is True

    def test_kg_node_node_type_indexed(self) -> None:
        """Test node_type column is indexed."""
        node_type_col = KGNode.__table__.c.node_type
        assert node_type_col.index is True

    def test_kg_node_omop_concept_id_indexed(self) -> None:
        """Test omop_concept_id column is indexed."""
        concept_id_col = KGNode.__table__.c.omop_concept_id
        assert concept_id_col.index is True

    def test_create_patient_node(self) -> None:
        """Test creating a patient node."""
        node = KGNode(
            patient_id="P001",
            node_type=NodeType.PATIENT,
            label="Patient P001",
            properties={},
        )
        assert node.node_type == NodeType.PATIENT
        assert node.is_patient_node is True
        assert node.omop_concept_id is None

    def test_create_condition_node(self) -> None:
        """Test creating a condition node."""
        node = KGNode(
            patient_id="P001",
            node_type=NodeType.CONDITION,
            omop_concept_id=233604007,
            label="Pneumonia",
            properties={"assertion": "absent"},
        )
        assert node.node_type == NodeType.CONDITION
        assert node.omop_concept_id == 233604007
        assert node.properties["assertion"] == "absent"
        assert node.is_patient_node is False

    def test_create_drug_node(self) -> None:
        """Test creating a drug node."""
        node = KGNode(
            patient_id="P001",
            node_type=NodeType.DRUG,
            omop_concept_id=1191,
            label="Aspirin",
            properties={"dose": "81mg", "frequency": "daily"},
        )
        assert node.node_type == NodeType.DRUG
        assert node.label == "Aspirin"

    def test_create_measurement_node(self) -> None:
        """Test creating a measurement node."""
        node = KGNode(
            patient_id="P001",
            node_type=NodeType.MEASUREMENT,
            omop_concept_id=4548,
            label="Hemoglobin A1c",
            properties={"value": "7.2", "unit": "%"},
        )
        assert node.node_type == NodeType.MEASUREMENT
        assert node.properties["value"] == "7.2"

    def test_kg_node_omop_concept_id_nullable(self) -> None:
        """Test omop_concept_id is nullable (for patient nodes)."""
        concept_id_col = KGNode.__table__.c.omop_concept_id
        assert concept_id_col.nullable is True

    def test_kg_node_properties_is_jsonb(self) -> None:
        """Test properties column uses JSONB type."""
        properties_col = KGNode.__table__.c.properties
        assert "JSONB" in str(properties_col.type).upper()

    def test_kg_node_repr(self) -> None:
        """Test KGNode __repr__ method."""
        node = KGNode(
            id="550e8400-e29b-41d4-a716-446655440000",
            patient_id="P001",
            node_type=NodeType.CONDITION,
            label="Pneumonia",
        )
        repr_str = repr(node)
        assert "KGNode" in repr_str
        assert "Pneumonia" in repr_str


class TestKGEdgeModel:
    """Test KGEdge model class."""

    def test_kg_edge_inherits_base(self) -> None:
        """Test that KGEdge inherits from Base."""
        from app.core.database import Base

        assert issubclass(KGEdge, Base)

    def test_kg_edge_tablename(self) -> None:
        """Test KGEdge has correct table name."""
        assert KGEdge.__tablename__ == "kg_edges"

    def test_kg_edge_has_required_columns(self) -> None:
        """Test KGEdge has all required columns."""
        columns = KGEdge.__table__.c
        required_columns = [
            "id", "created_at", "patient_id", "source_node_id",
            "target_node_id", "edge_type", "fact_id", "properties"
        ]
        for col in required_columns:
            assert col in columns, f"Missing column: {col}"

    def test_kg_edge_patient_id_indexed(self) -> None:
        """Test patient_id column is indexed."""
        patient_id_col = KGEdge.__table__.c.patient_id
        assert patient_id_col.index is True

    def test_kg_edge_source_node_id_indexed(self) -> None:
        """Test source_node_id column is indexed."""
        source_col = KGEdge.__table__.c.source_node_id
        assert source_col.index is True

    def test_kg_edge_target_node_id_indexed(self) -> None:
        """Test target_node_id column is indexed."""
        target_col = KGEdge.__table__.c.target_node_id
        assert target_col.index is True

    def test_kg_edge_edge_type_indexed(self) -> None:
        """Test edge_type column is indexed."""
        edge_type_col = KGEdge.__table__.c.edge_type
        assert edge_type_col.index is True

    def test_create_has_condition_edge(self) -> None:
        """Test creating a has_condition edge."""
        edge = KGEdge(
            patient_id="P001",
            source_node_id="550e8400-e29b-41d4-a716-446655440000",
            target_node_id="660e8400-e29b-41d4-a716-446655440000",
            edge_type=EdgeType.HAS_CONDITION,
            fact_id="770e8400-e29b-41d4-a716-446655440000",
            properties={"onset_date": "2024-01-01"},
        )
        assert edge.edge_type == EdgeType.HAS_CONDITION
        assert edge.fact_id is not None

    def test_create_takes_drug_edge(self) -> None:
        """Test creating a takes_drug edge."""
        edge = KGEdge(
            patient_id="P001",
            source_node_id="550e8400-e29b-41d4-a716-446655440000",
            target_node_id="660e8400-e29b-41d4-a716-446655440000",
            edge_type=EdgeType.TAKES_DRUG,
            properties={"start_date": "2024-01-01"},
        )
        assert edge.edge_type == EdgeType.TAKES_DRUG

    def test_kg_edge_fact_id_nullable(self) -> None:
        """Test fact_id is nullable."""
        fact_id_col = KGEdge.__table__.c.fact_id
        assert fact_id_col.nullable is True

    def test_kg_edge_has_source_foreign_key(self) -> None:
        """Test source_node_id has foreign key to kg_nodes."""
        source_col = KGEdge.__table__.c.source_node_id
        fk = list(source_col.foreign_keys)[0]
        assert str(fk.column) == "kg_nodes.id"

    def test_kg_edge_has_target_foreign_key(self) -> None:
        """Test target_node_id has foreign key to kg_nodes."""
        target_col = KGEdge.__table__.c.target_node_id
        fk = list(target_col.foreign_keys)[0]
        assert str(fk.column) == "kg_nodes.id"

    def test_kg_edge_has_fact_foreign_key(self) -> None:
        """Test fact_id has foreign key to clinical_facts."""
        fact_col = KGEdge.__table__.c.fact_id
        fk = list(fact_col.foreign_keys)[0]
        assert str(fk.column) == "clinical_facts.id"

    def test_kg_edge_repr(self) -> None:
        """Test KGEdge __repr__ method."""
        edge = KGEdge(
            id="550e8400-e29b-41d4-a716-446655440000",
            patient_id="P001",
            source_node_id="660e8400-e29b-41d4-a716-446655440000",
            target_node_id="770e8400-e29b-41d4-a716-446655440000",
            edge_type=EdgeType.HAS_CONDITION,
        )
        repr_str = repr(edge)
        assert "KGEdge" in repr_str
        assert "has_condition" in repr_str.lower()


class TestKGModelExports:
    """Test model exports from package."""

    def test_kg_node_exported(self) -> None:
        """Test KGNode is exported from models package."""
        from app.models import KGNode

        assert KGNode is not None

    def test_kg_edge_exported(self) -> None:
        """Test KGEdge is exported from models package."""
        from app.models import KGEdge

        assert KGEdge is not None

    def test_all_exports(self) -> None:
        """Test __all__ contains expected exports."""
        from app import models

        assert "KGNode" in models.__all__
        assert "KGEdge" in models.__all__
