# Web UI Specification

## Overview
Next.js frontend for uploading documents, viewing jobs, exploring facts, and visualizing the knowledge graph.

## Tech Stack
- Next.js 14+ with App Router
- TypeScript
- Tailwind CSS
- React Query for data fetching
- Simple graph visualization (D3.js or similar)

## Pages

### 1. Home / Upload Page (`/`)
- Document upload form
- Drag-and-drop support
- Patient ID input
- Note type selector
- Recent uploads list

### 2. Jobs Page (`/jobs`)
- List of all jobs
- Status indicators (queued, processing, completed, failed)
- Progress bars
- Filter by status
- Auto-refresh for active jobs

### 3. Document Viewer (`/documents/[id]`)
- Original note text
- Highlighted mentions (color-coded by type)
- Mention sidebar with details:
  - Text span
  - Assertion (with visual indicator for negated)
  - Temporality
  - Experiencer
  - Mapped concepts

### 4. Facts Page (`/patients/[id]/facts`)
- List of all ClinicalFacts for a patient
- Filterable by:
  - Domain (condition, drug, measurement)
  - Assertion (present, absent, possible)
  - Temporality
- Evidence links to source documents

### 5. Graph Page (`/patients/[id]/graph`)
- Interactive node-edge visualization
- Patient at center
- Conditions, drugs, measurements as connected nodes
- Color coding:
  - Green: present
  - Red: absent (negated)
  - Yellow: possible
- Click node for details
- Zoom and pan

### 6. Export Page (`/export`)
- Format selector (CSV, JSON)
- Date range filter
- Patient filter
- Download button
- Export preview

## Components

### MentionHighlight
Highlight text spans in documents with color coding.

### FactCard
Display a single ClinicalFact with:
- Concept name
- Domain badge
- Assertion indicator
- Evidence preview

### GraphVisualization
Interactive force-directed graph with:
- Draggable nodes
- Zoom controls
- Legend
- Node tooltips

### JobStatusBadge
Visual indicator for job status with animations.

## API Integration

```typescript
// API client
const api = {
  // Documents
  uploadDocument: (data: DocumentUpload) => POST('/documents', data),
  getDocument: (id: string) => GET(`/documents/${id}`),

  // Jobs
  getJobs: () => GET('/jobs'),
  getJob: (id: string) => GET(`/jobs/${id}`),

  // Patients
  getPatientFacts: (id: string) => GET(`/patients/${id}/facts`),
  getPatientGraph: (id: string) => GET(`/patients/${id}/graph`),

  // Export
  exportOmop: (params: ExportParams) => GET('/export/omop', params)
}
```

## Acceptance Criteria

- [ ] Upload page accepts documents and shows job ID
- [ ] Jobs page shows real-time status updates
- [ ] Document viewer highlights mentions correctly
- [ ] Negated mentions are visually distinct (e.g., strikethrough, red)
- [ ] Facts list filters work correctly
- [ ] Graph renders with proper node/edge layout
- [ ] Export downloads correct format
- [ ] Responsive design (mobile-friendly)
- [ ] Accessibility: keyboard navigation, screen reader support
