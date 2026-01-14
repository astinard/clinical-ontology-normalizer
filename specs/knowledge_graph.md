# Knowledge Graph Specification

## Overview
Materialize ClinicalFacts into a queryable patient-centric knowledge graph.

## Graph Model

### Nodes (KGNode)

```python
class KGNode:
    id: UUID
    patient_id: str
    node_type: str        # patient, condition, drug, measurement, procedure
    omop_concept_id: int | None
    label: str            # Human-readable label
    properties: dict      # Type-specific properties
    created_at: datetime
```

### Node Types

1. **Patient Node**
   - `node_type = "patient"`
   - `label = patient_id`
   - Properties: demographics if available

2. **Condition Node**
   - `node_type = "condition"`
   - `omop_concept_id = SNOMED code`
   - Properties: `{assertion, temporality, confidence}`

3. **Drug Node**
   - `node_type = "drug"`
   - `omop_concept_id = RxNorm code`
   - Properties: `{dose, frequency, route}`

4. **Measurement Node**
   - `node_type = "measurement"`
   - `omop_concept_id = LOINC code`
   - Properties: `{value, unit, reference_range}`

### Edges (KGEdge)

```python
class KGEdge:
    id: UUID
    patient_id: str
    source_node_id: UUID
    target_node_id: UUID
    edge_type: str        # has_condition, takes_drug, has_measurement
    properties: dict      # Edge-specific properties
    fact_id: UUID         # Link to source ClinicalFact
    created_at: datetime
```

### Edge Types

1. **has_condition**
   - Patient → Condition
   - Properties: `{assertion, onset_date}`

2. **takes_drug**
   - Patient → Drug
   - Properties: `{start_date, end_date}`

3. **has_measurement**
   - Patient → Measurement
   - Properties: `{date, value}`

4. **condition_treated_by**
   - Condition → Drug
   - Properties: `{evidence_strength}`

## Graph Building

### From ClinicalFact

```python
def build_graph_from_fact(fact: ClinicalFact) -> tuple[KGNode, KGEdge]:
    # 1. Find or create patient node
    patient_node = get_or_create_patient_node(fact.patient_id)

    # 2. Create concept node
    concept_node = KGNode(
        patient_id=fact.patient_id,
        node_type=fact.domain,
        omop_concept_id=fact.omop_concept_id,
        label=fact.concept_name,
        properties={
            "assertion": fact.assertion,
            "temporality": fact.temporality,
            "confidence": fact.confidence
        }
    )

    # 3. Create edge
    edge = KGEdge(
        patient_id=fact.patient_id,
        source_node_id=patient_node.id,
        target_node_id=concept_node.id,
        edge_type=f"has_{fact.domain}",
        fact_id=fact.id
    )

    return concept_node, edge
```

## Query API

### GET /patients/{patient_id}/graph
Return full patient graph.

**Response:**
```json
{
  "nodes": [
    {
      "id": "uuid",
      "type": "patient",
      "label": "P001"
    },
    {
      "id": "uuid",
      "type": "condition",
      "label": "Pneumonia",
      "omop_concept_id": 233604007,
      "properties": {
        "assertion": "absent",
        "temporality": "current"
      }
    }
  ],
  "edges": [
    {
      "source": "uuid",
      "target": "uuid",
      "type": "has_condition"
    }
  ]
}
```

### GET /patients/{patient_id}/graph/conditions
Return only condition subgraph.

### GET /patients/{patient_id}/graph/timeline
Return graph with temporal ordering.

## Acceptance Criteria

- [ ] Patient node created for each unique patient
- [ ] All ClinicalFacts materialize as nodes
- [ ] Edges correctly link patient to concepts
- [ ] Negated conditions are included (with assertion=absent)
- [ ] Graph query returns valid JSON
- [ ] Graph handles patients with 100+ facts efficiently
