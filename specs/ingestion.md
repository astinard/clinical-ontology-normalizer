# Ingestion Specification

## Overview
The ingestion layer handles uploading and storing clinical documents and structured resources.

## Endpoints

### POST /documents
Upload a clinical note for processing.

**Request:**
```json
{
  "patient_id": "string",
  "note_type": "string",  // progress_note, discharge_summary, etc.
  "text": "string",
  "metadata": {}
}
```

**Response:**
```json
{
  "document_id": "uuid",
  "job_id": "uuid",
  "status": "queued"
}
```

### POST /structured-resources
Upload structured data (FHIR bundle or CSV).

**Request:**
```json
{
  "patient_id": "string",
  "resource_type": "fhir_bundle" | "csv",
  "payload": {}
}
```

### GET /documents/{document_id}
Retrieve document with processing status.

### GET /jobs/{job_id}
Get job processing status.

**Response:**
```json
{
  "job_id": "uuid",
  "status": "queued" | "processing" | "completed" | "failed",
  "progress": 0.0-1.0,
  "result": {} | null,
  "error": "string" | null
}
```

## Document Model

```python
class Document:
    id: UUID
    patient_id: str
    note_type: str
    text: str
    metadata: dict
    created_at: datetime
    processed_at: datetime | None
    status: str  # pending, processing, completed, failed
```

## Acceptance Criteria

- [ ] Documents can be uploaded via REST API
- [ ] Each upload creates a background job
- [ ] Job status is queryable
- [ ] Documents are stored in Postgres
- [ ] Large documents (>1MB) are handled gracefully
- [ ] Invalid requests return appropriate error codes
