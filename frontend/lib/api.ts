/**
 * API client for the Arbor Content Dashboard backend.
 */

const API_BASE = "/api";

/**
 * Generic fetch wrapper with error handling.
 */
async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      "Content-Type": "application/json",
    },
    ...options,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `API error: ${res.status}`);
  }

  return res.json();
}

// -----------------------------------------------------------------------------
// Types (matching backend schemas)
// -----------------------------------------------------------------------------

export interface SubjectStats {
  temario_exists: boolean;
  standards_count: number;
  atoms_count: number;
  tests_count: number;
  questions_count: number;
  variants_count: number;
  tagging_completion: number;
}

export interface SubjectBrief {
  id: string;
  name: string;
  full_name: string;
  year: number;
  stats: SubjectStats;
}

export interface OverviewResponse {
  subjects: SubjectBrief[];
}

export interface StandardBrief {
  id: string;
  eje: string;
  title: string;
  atoms_count: number;
}

export interface AtomBrief {
  id: string;
  eje: string;
  standard_ids: string[];
  tipo_atomico: string;
  titulo: string;
  question_set_count: number;
  has_lesson: boolean;
}

export interface TestBrief {
  id: string;
  name: string;
  admission_year: number | null;
  application_type: string | null;
  raw_pdf_exists: boolean;
  split_count: number;
  qti_count: number;
  finalized_count: number;
  tagged_count: number;
  variants_count: number;
}

export interface SubjectDetail {
  id: string;
  name: string;
  full_name: string;
  year: number;
  temario_exists: boolean;
  temario_file: string | null;
  standards: StandardBrief[];
  atoms_count: number;
  tests: TestBrief[];
}

export interface QuestionBrief {
  id: string;
  question_number: number;
  has_split_pdf: boolean;
  has_qti: boolean;
  is_finalized: boolean;
  is_tagged: boolean;
  atoms_count: number;
  variants_count: number;
}

export interface TestDetail {
  id: string;
  name: string;
  admission_year: number | null;
  application_type: string | null;
  raw_pdf_exists: boolean;
  split_count: number;
  qti_count: number;
  finalized_count: number;
  tagged_count: number;
  variants_count: number;
  questions: QuestionBrief[];
}

export interface GraphNode {
  id: string;
  type: string;
  position: { x: number; y: number };
  data: Record<string, unknown>;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: string;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  stats: Record<string, unknown>;
}

// -----------------------------------------------------------------------------
// API functions
// -----------------------------------------------------------------------------

export async function getOverview(): Promise<OverviewResponse> {
  return fetchAPI<OverviewResponse>("/overview");
}

export async function getSubject(subjectId: string): Promise<SubjectDetail> {
  return fetchAPI<SubjectDetail>(`/subjects/${subjectId}`);
}

export async function getStandards(subjectId: string): Promise<StandardBrief[]> {
  return fetchAPI<StandardBrief[]>(`/subjects/${subjectId}/standards`);
}

export async function getAtoms(
  subjectId: string,
  filters?: { eje?: string; standard_id?: string }
): Promise<AtomBrief[]> {
  const params = new URLSearchParams();
  if (filters?.eje) params.set("eje", filters.eje);
  if (filters?.standard_id) params.set("standard_id", filters.standard_id);
  const query = params.toString();
  return fetchAPI<AtomBrief[]>(`/subjects/${subjectId}/atoms${query ? `?${query}` : ""}`);
}

export async function getAtomsGraph(subjectId: string): Promise<GraphData> {
  return fetchAPI<GraphData>(`/subjects/${subjectId}/atoms/graph`);
}

export async function getTests(subjectId: string): Promise<TestBrief[]> {
  return fetchAPI<TestBrief[]>(`/subjects/${subjectId}/tests`);
}

export async function getTestDetail(
  subjectId: string,
  testId: string
): Promise<TestDetail> {
  return fetchAPI<TestDetail>(`/subjects/${subjectId}/tests/${testId}`);
}
