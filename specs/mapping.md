# OMOP Mapping Specification

## Overview
Map extracted mentions to standard OMOP concept IDs.

## Mapping Strategy

### 1. Exact Match
Direct lookup of lexical variant against concept synonyms.

### 2. Fuzzy Match
Similarity-based matching using:
- Levenshtein distance
- Token overlap
- Character n-grams

### 3. Candidate Ranking
Return top-N candidates with confidence scores.

## MentionConceptCandidate Model

```python
class MentionConceptCandidate:
    id: UUID
    mention_id: UUID
    omop_concept_id: int
    concept_name: str
    concept_code: str
    vocabulary_id: str    # SNOMED, ICD10CM, RxNorm, etc.
    domain_id: str        # Condition, Drug, Measurement, etc.
    score: float          # 0.0-1.0 confidence
    method: str           # exact, fuzzy, ml
    rank: int             # 1 = best match
```

## Local Vocabulary Fixture

For MVP, use a small subset of OMOP concepts:

### Conditions (SNOMED)
- Pneumonia (233604007)
- Congestive heart failure (42343007)
- Colon cancer (93761005)
- Urinary tract infection (68566005)
- Chest pain (29857009)
- Diabetes mellitus (73211009)
- Hypertension (38341003)

### Drugs (RxNorm)
- Aspirin (1191)
- Metformin (6809)
- Lisinopril (29046)
- Atorvastatin (83367)

### Measurements (LOINC)
- Hemoglobin A1c (4548-4)
- Blood glucose (2345-7)
- Creatinine (2160-0)

## Mapping Service Interface

```python
class MappingService(Protocol):
    async def map_mention(
        self,
        mention: Mention,
        top_k: int = 5
    ) -> list[MentionConceptCandidate]:
        """Map a mention to OMOP concepts."""
        ...

    async def map_batch(
        self,
        mentions: list[Mention],
        top_k: int = 5
    ) -> dict[UUID, list[MentionConceptCandidate]]:
        """Batch mapping for efficiency."""
        ...
```

## Acceptance Criteria

- [ ] Exact matches return score >= 0.95
- [ ] Fuzzy matches handle common misspellings
- [ ] Unknown terms return empty candidates (not errors)
- [ ] Batch mapping is efficient (< 100ms per mention average)
- [ ] Domain filtering works (e.g., only Condition concepts)
