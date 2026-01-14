# NLP Pipeline Specification

## Overview
Extract clinical mentions from unstructured text with assertion metadata.

## Mention Extraction

### Input
Raw clinical note text.

### Output
List of Mention objects with:
- Text span and character offsets
- Lexical variant (normalized form)
- Section (if detectable)
- Assertion status
- Temporality
- Experiencer

## Mention Model

```python
class Mention:
    id: UUID
    document_id: UUID
    text: str              # Original text span
    start_offset: int      # Character start position
    end_offset: int        # Character end position
    lexical_variant: str   # Normalized form
    section: str | None    # Clinical section
    assertion: str         # present, absent, possible
    temporality: str       # current, past, future
    experiencer: str       # patient, family, other
    confidence: float      # 0.0-1.0
```

## Assertion Detection

### Negation (assertion=absent)
Detect negated findings using NegEx-style rules:

**Pre-negation triggers:**
- "no evidence of"
- "denies"
- "negative for"
- "without"
- "ruled out"

**Post-negation triggers:**
- "was ruled out"
- "unlikely"

**Pseudo-negation (do NOT negate):**
- "no increase in"
- "not only"

### Uncertainty (assertion=possible)
- "possible"
- "probable"
- "suspected"
- "cannot rule out"
- "concerning for"

## Temporality Detection

### Past
- "history of"
- "previous"
- "prior"
- "had"
- "was diagnosed with"

### Future
- "will need"
- "planned"
- "scheduled for"

### Current (default)
- Present tense descriptions

## Experiencer Detection

### Family
- "family history of"
- "mother had"
- "father has"
- "sibling with"

### Other
- "patient reports friend has"
- Third-party references

### Patient (default)
- Direct statements about the patient

## Test Fixtures Expected Outputs

| Input | Expected Assertion | Expected Temporality | Expected Experiencer |
|-------|-------------------|---------------------|---------------------|
| "No evidence of pneumonia" | absent | current | patient |
| "History of CHF" | present | past | patient |
| "Mother had colon cancer" | present | past | family |
| "Denies chest pain" | absent | current | patient |
| "Possible UTI" | possible | current | patient |

## Acceptance Criteria

- [ ] Extracts mentions with correct offsets
- [ ] Correctly identifies negated findings
- [ ] Correctly identifies temporal context
- [ ] Correctly identifies experiencer
- [ ] Handles edge cases (double negation, etc.)
- [ ] Performance: <1 second per average note
