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

export interface AtomTag {
  atom_id: string;
  titulo: string;
  eje: string;
  relevance: number;
}

export interface VariantBrief {
  id: string;
  variant_number: number;
  folder_name: string;
  has_qti: boolean;
  has_metadata: boolean;
}

export interface QuestionOption {
  id: string;
  text: string;
}

export interface QuestionDetail {
  id: string;
  test_id: string;
  question_number: number;
  has_split_pdf: boolean;
  has_qti: boolean;
  is_finalized: boolean;
  is_tagged: boolean;
  qti_xml: string | null;
  qti_stem: string | null;
  qti_options: QuestionOption[] | null;
  correct_answer: string | null;
  difficulty: string | null;
  source_info: Record<string, unknown> | null;
  atom_tags: AtomTag[];
  feedback: Record<string, string>;
  variants: VariantBrief[];
  qti_path: string | null;
  pdf_path: string | null;
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

export interface UnlockStatus {
  all_questions_tagged: boolean;
  tagged_count: number;
  total_count: number;
  completion_percentage: number;
  tests_status: Record<string, { tagged: number; total: number; complete: boolean }>;
}

export async function getAtomsUnlockStatus(subjectId: string): Promise<UnlockStatus> {
  return fetchAPI<UnlockStatus>(`/subjects/${subjectId}/atoms/unlock-status`);
}

export async function getTemario(subjectId: string): Promise<Record<string, unknown>> {
  return fetchAPI<Record<string, unknown>>(`/subjects/${subjectId}/temario`);
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

export async function getQuestionDetail(
  subjectId: string,
  testId: string,
  questionNum: number
): Promise<QuestionDetail> {
  return fetchAPI<QuestionDetail>(
    `/subjects/${subjectId}/tests/${testId}/questions/${questionNum}`
  );
}

// -----------------------------------------------------------------------------
// Pipeline types
// -----------------------------------------------------------------------------

export interface PipelineDefinition {
  id: string;
  name: string;
  description: string;
  has_ai_cost: boolean;
  requires: string[];
  produces: string;
}

export interface PipelineParam {
  name: string;
  type: "string" | "number" | "boolean" | "select";
  label: string;
  required: boolean;
  default?: string | number | boolean | null;
  options?: string[];
  description?: string;
}

export interface CostEstimate {
  pipeline_id: string;
  model: string;
  input_tokens: number;
  output_tokens: number;
  estimated_cost_min: number;
  estimated_cost_max: number;
  breakdown: Record<string, unknown>;
}

export interface FailedItem {
  id: string;
  error: string;
  timestamp: string | null;
}

export interface JobStatus {
  job_id: string;
  pipeline_id: string;
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  params: Record<string, unknown>;
  started_at: string | null;
  completed_at: string | null;
  total_items: number;
  completed_items: number;
  failed_items: number;
  current_item: string | null;
  completed_item_ids: string[];
  failed_item_details: FailedItem[];
  remaining_items: number;
  error: string | null;
  cost_actual: number | null;
  logs: string[];
  can_resume: boolean;
}

export interface JobListResponse {
  jobs: JobStatus[];
}

// -----------------------------------------------------------------------------
// Pipeline API functions
// -----------------------------------------------------------------------------

export async function getPipelines(): Promise<PipelineDefinition[]> {
  return fetchAPI<PipelineDefinition[]>("/pipelines");
}

export async function getPipelineDetails(
  pipelineId: string
): Promise<{ pipeline: PipelineDefinition; params: PipelineParam[] }> {
  return fetchAPI<{ pipeline: PipelineDefinition; params: PipelineParam[] }>(
    `/pipelines/${pipelineId}`
  );
}

export async function estimatePipelineCost(
  pipelineId: string,
  params: Record<string, unknown>
): Promise<CostEstimate> {
  return fetchAPI<CostEstimate>(
    `/pipelines/estimate?pipeline_id=${encodeURIComponent(pipelineId)}`,
    {
      method: "POST",
      body: JSON.stringify(params),
    }
  );
}

export async function getConfirmationToken(
  pipelineId: string,
  params: Record<string, unknown>
): Promise<{ confirmation_token: string }> {
  return fetchAPI<{ confirmation_token: string }>(
    `/pipelines/confirm?pipeline_id=${encodeURIComponent(pipelineId)}`,
    {
      method: "POST",
      body: JSON.stringify(params),
    }
  );
}

export async function runPipeline(
  pipelineId: string,
  params: Record<string, unknown>,
  confirmationToken: string
): Promise<{ job_id: string; status: string; message: string }> {
  return fetchAPI<{ job_id: string; status: string; message: string }>(
    "/pipelines/run",
    {
      method: "POST",
      body: JSON.stringify({
        pipeline_id: pipelineId,
        params,
        confirmation_token: confirmationToken,
      }),
    }
  );
}

export async function getJobs(limit = 20): Promise<JobListResponse> {
  return fetchAPI<JobListResponse>(`/pipelines/jobs?limit=${limit}`);
}

export async function getJob(jobId: string): Promise<JobStatus> {
  return fetchAPI<JobStatus>(`/pipelines/jobs/${jobId}`);
}

export async function cancelJob(jobId: string): Promise<JobStatus> {
  return fetchAPI<JobStatus>(`/pipelines/jobs/${jobId}/cancel`, {
    method: "POST",
  });
}

export async function deleteJob(jobId: string): Promise<{ message: string }> {
  return fetchAPI<{ message: string }>(`/pipelines/jobs/${jobId}`, {
    method: "DELETE",
  });
}

export async function resumeJob(
  jobId: string,
  mode: "remaining" | "failed_only" = "remaining"
): Promise<{ job_id: string; status: string; message: string }> {
  return fetchAPI<{ job_id: string; status: string; message: string }>(
    `/pipelines/jobs/${jobId}/resume`,
    {
      method: "POST",
      body: JSON.stringify({ mode }),
    }
  );
}

export interface JobLogsResponse {
  job_id: string;
  logs: string[];
  offset: number;
  limit: number;
  total: number;
  has_more: boolean;
}

export async function getJobLogs(
  jobId: string,
  offset = 0,
  limit = 100
): Promise<JobLogsResponse> {
  return fetchAPI<JobLogsResponse>(
    `/pipelines/jobs/${jobId}/logs?offset=${offset}&limit=${limit}`
  );
}

// -----------------------------------------------------------------------------
// Sync types
// -----------------------------------------------------------------------------

export interface SyncTableSummary {
  table: string;
  total: number;
  breakdown: Record<string, number>;
}

export interface SyncPreviewResponse {
  tables: SyncTableSummary[];
  summary: Record<string, unknown>;
  warnings: string[];
}

export interface SyncExecuteResponse {
  success: boolean;
  results: Record<string, number>;
  message: string;
  errors: string[];
}

export interface SyncStatus {
  database_configured: boolean;
  s3_configured: boolean;
  available_entities: string[];
}

// -----------------------------------------------------------------------------
// Sync API functions
// -----------------------------------------------------------------------------

export async function getSyncStatus(): Promise<SyncStatus> {
  return fetchAPI<SyncStatus>("/sync/status");
}

export async function previewSync(
  entities: string[],
  includeVariants: boolean,
  uploadImages: boolean
): Promise<SyncPreviewResponse> {
  return fetchAPI<SyncPreviewResponse>("/sync/preview", {
    method: "POST",
    body: JSON.stringify({
      entities,
      include_variants: includeVariants,
      upload_images: uploadImages,
    }),
  });
}

export async function executeSync(
  entities: string[],
  includeVariants: boolean,
  uploadImages: boolean,
  confirm: boolean
): Promise<SyncExecuteResponse> {
  return fetchAPI<SyncExecuteResponse>("/sync/execute", {
    method: "POST",
    body: JSON.stringify({
      entities,
      include_variants: includeVariants,
      upload_images: uploadImages,
      confirm,
    }),
  });
}
