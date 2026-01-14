# OMOP Export Specification

## Overview
Export processed data in OMOP CDM-compatible formats.

## Export Tables

### NOTE Table
Document-level metadata.

```sql
note_id              -- Document ID
person_id            -- Patient ID
note_date            -- Document date
note_datetime        -- Full timestamp
note_type_concept_id -- Type (progress note, discharge, etc.)
note_class_concept_id
note_title
note_text            -- Original text
encoding_concept_id
language_concept_id
provider_id
visit_occurrence_id
visit_detail_id
note_source_value
```

### NOTE_NLP Table
NLP-extracted mentions with assertion info.

```sql
note_nlp_id          -- Unique ID
note_id              -- Foreign key to NOTE
section_concept_id   -- Section of note
snippet              -- Text span
offset               -- Character offset
lexical_variant      -- Normalized form
note_nlp_concept_id  -- OMOP concept ID
note_nlp_source_concept_id
nlp_system           -- "clinical-ontology-normalizer"
nlp_date
nlp_datetime
term_exists          -- Y/N (for negation: N=absent)
term_temporal        -- past/current/future
term_modifiers       -- JSON: {assertion, experiencer, confidence}
```

## Negation Handling

**CRITICAL**: Negated findings use `term_exists = 'N'`

Example:
- "No evidence of pneumonia"
- → `note_nlp_concept_id = pneumonia concept`
- → `term_exists = 'N'`
- → `term_modifiers = {"assertion": "absent"}`

Do NOT insert negated findings into CONDITION_OCCURRENCE as positive events.

## Export Formats

### CSV Export
Standard CSV files per table:
- `note.csv`
- `note_nlp.csv`

### JSON Export
Nested JSON for API consumers:
```json
{
  "notes": [...],
  "note_nlp": [...],
  "metadata": {
    "export_date": "...",
    "version": "1.0"
  }
}
```

## Export Endpoint

### GET /export/omop
Export all processed data.

**Query Parameters:**
- `format`: csv | json
- `patient_id`: Filter by patient
- `start_date`: Filter by date range
- `end_date`: Filter by date range

**Response (JSON):**
```json
{
  "notes": [...],
  "note_nlp": [...],
  "clinical_facts": [...]
}
```

**Response (CSV):**
ZIP file containing:
- note.csv
- note_nlp.csv
- clinical_facts.csv

## Acceptance Criteria

- [ ] NOTE export matches OMOP CDM 5.4 schema
- [ ] NOTE_NLP export includes all assertion metadata
- [ ] Negated findings have term_exists='N'
- [ ] CSV files have proper headers
- [ ] JSON is valid and parseable
- [ ] Export handles large datasets (streaming)
