/**
 * API client for the Clinical Ontology Normalizer backend.
 */

// Use relative URLs in browser, absolute URLs for server-side
const API_BASE_URL = typeof window !== "undefined"
  ? "/api"  // Browser: use Next.js API proxy
  : (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000");  // Server: direct backend call

export interface DocumentCreate {
  patient_id: string;
  note_type: string;
  text: string;
  metadata?: Record<string, unknown>;
}

export interface DocumentUploadResponse {
  document_id: string;
  job_id: string;
  status: string;
}

export interface Document {
  id: string;
  patient_id: string;
  note_type: string;
  text: string;
  metadata: Record<string, unknown>;
  status: string;
  job_id: string;
  created_at: string;
  processed_at: string | null;
}

export interface JobInfo {
  job_id: string;
  status: string;
  result: Record<string, unknown> | null;
  error: string | null;
}

export interface PatientGraph {
  patient_id: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  node_count: number;
  edge_count: number;
}

export interface GraphNode {
  id: string;
  patient_id: string;
  node_type: string;
  omop_concept_id: number | null;
  label: string;
  properties: Record<string, unknown>;
  created_at: string;
}

export interface GraphEdge {
  id: string;
  patient_id: string;
  source_node_id: string;
  target_node_id: string;
  edge_type: string;
  fact_id: string | null;
  properties: Record<string, unknown>;
  created_at: string;
}

export interface ClinicalFact {
  id: string;
  patient_id: string;
  domain: string;
  omop_concept_id: number;
  concept_name: string;
  assertion: string;
  temporality: string;
  experiencer: string;
  confidence: number;
  value: string | null;
  unit: string | null;
  start_date: string | null;
  end_date: string | null;
  created_at: string;
}

export interface Mention {
  id: string;
  document_id: string;
  text: string;
  start_offset: number;
  end_offset: number;
  lexical_variant: string;
  section: string | null;
  assertion: string;
  temporality: string;
  experiencer: string;
  confidence: number;
  created_at: string;
}

export interface ExtractedMentionPreview {
  text: string;
  start_offset: number;
  end_offset: number;
  lexical_variant: string;
  section: string | null;
  assertion: string;
  temporality: string;
  experiencer: string;
  confidence: number;
  domain: string | null;
  omop_concept_id: number | null;
}

export interface ExtractPreviewResponse {
  mentions: ExtractedMentionPreview[];
  extraction_time_ms: number;
  mention_count: number;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const errorText = await response.text();
    throw new ApiError(response.status, errorText);
  }
  return response.json();
}

export async function uploadDocument(
  document: DocumentCreate
): Promise<DocumentUploadResponse> {
  const response = await fetch(`${API_BASE_URL}/documents`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(document),
  });
  return handleResponse<DocumentUploadResponse>(response);
}

export async function getDocument(documentId: string): Promise<Document> {
  const response = await fetch(`${API_BASE_URL}/documents/${documentId}`);
  return handleResponse<Document>(response);
}

export async function getJobStatus(jobId: string): Promise<JobInfo> {
  const response = await fetch(`${API_BASE_URL}/jobs/${jobId}`);
  return handleResponse<JobInfo>(response);
}

export async function getPatientGraph(patientId: string): Promise<PatientGraph> {
  const response = await fetch(`${API_BASE_URL}/patients/${patientId}/graph`);
  return handleResponse<PatientGraph>(response);
}

export async function buildPatientGraph(
  patientId: string
): Promise<PatientGraph> {
  const response = await fetch(
    `${API_BASE_URL}/patients/${patientId}/graph/build`,
    {
      method: "POST",
    }
  );
  return handleResponse<PatientGraph>(response);
}

export async function getPatientFacts(
  patientId: string,
  options?: {
    domain?: string;
    assertion?: string;
    limit?: number;
    offset?: number;
  }
): Promise<ClinicalFact[]> {
  const params = new URLSearchParams();
  if (options?.domain) params.append("domain", options.domain);
  if (options?.assertion) params.append("assertion", options.assertion);
  if (options?.limit) params.append("limit", options.limit.toString());
  if (options?.offset) params.append("offset", options.offset.toString());

  const queryString = params.toString();
  const url = `${API_BASE_URL}/patients/${patientId}/facts${queryString ? `?${queryString}` : ""}`;
  const response = await fetch(url);
  return handleResponse<ClinicalFact[]>(response);
}

export async function getDocumentMentions(
  documentId: string
): Promise<Mention[]> {
  const response = await fetch(`${API_BASE_URL}/documents/${documentId}/mentions`);
  return handleResponse<Mention[]>(response);
}

export async function previewExtraction(
  text: string,
  noteType?: string
): Promise<ExtractPreviewResponse> {
  const response = await fetch(`${API_BASE_URL}/documents/preview/extract`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      text,
      note_type: noteType,
    }),
  });
  return handleResponse<ExtractPreviewResponse>(response);
}
