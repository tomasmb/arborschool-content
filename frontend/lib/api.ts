/**
 * API client for the Arbor Content Dashboard backend.
 */

// Re-export types that are used by components
export type {
  AtomBrief,
  AtomTag,
  CheckResult,
  CheckStatus,
  ContentQualityCheck,
  CorrectAnswerCheck,
  CostEstimate,
  EnrichmentJobResponse,
  EnrichmentProgress,
  EnrichmentResult,
  FailedItem,
  GraphData,
  GraphEdge,
  GraphNode,
  JobLogsResponse,
  JobStatus,
  OverviewResponse,
  QuestionBrief,
  QuestionDetail,
  QuestionOption,
  StandardBrief,
  SubjectBrief,
  SubjectDetail,
  SubjectStats,
  SyncExecuteResponse,
  SyncPreviewResponse,
  SyncPreviewQuestions,
  SyncPreviewSummary,
  SyncStatus,
  SyncTableSummary,
  TestBrief,
  TestDetail,
  TestSyncPreview,
  TestSyncResult,
  ValidationJobResponse,
  ValidationProgress,
  ValidationResult,
  ValidationResultDetail,
  VariantBrief,
} from "./api-types";

import type {
  AtomBrief,
  CostEstimate,
  EnrichmentJobResponse,
  GraphData,
  JobLogsResponse,
  JobStatus,
  OverviewResponse,
  QuestionDetail,
  StandardBrief,
  SubjectDetail,
  SyncExecuteResponse,
  SyncPreviewResponse,
  SyncStatus,
  TestBrief,
  TestDetail,
  TestSyncPreview,
  TestSyncResult,
  ValidationJobResponse,
} from "./api-types";

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
// Overview API
// -----------------------------------------------------------------------------

export async function getOverview(): Promise<OverviewResponse> {
  return fetchAPI<OverviewResponse>("/overview");
}

// -----------------------------------------------------------------------------
// Subject API
// -----------------------------------------------------------------------------

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

// -----------------------------------------------------------------------------
// Tests & Questions API
// -----------------------------------------------------------------------------

export async function getTests(subjectId: string): Promise<TestBrief[]> {
  return fetchAPI<TestBrief[]>(`/subjects/${subjectId}/tests`);
}

export async function getTestDetail(subjectId: string, testId: string): Promise<TestDetail> {
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

/**
 * Get the URL for a question's PDF file.
 * This returns a URL that can be used directly in an anchor tag or window.open().
 */
export function getQuestionPdfUrl(
  subjectId: string,
  testId: string,
  questionNum: number
): string {
  return `${API_BASE}/subjects/${subjectId}/tests/${testId}/questions/${questionNum}/pdf`;
}

/**
 * Get the URL for a subject's temario PDF file.
 */
export function getTemarioPdfUrl(subjectId: string): string {
  return `${API_BASE}/subjects/${subjectId}/temario/pdf`;
}

/**
 * Get the URL for a test's raw (original) PDF file.
 */
export function getTestRawPdfUrl(subjectId: string, testId: string): string {
  return `${API_BASE}/subjects/${subjectId}/tests/${testId}/raw-pdf`;
}

// -----------------------------------------------------------------------------
// Pipeline API
// -----------------------------------------------------------------------------

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
  return fetchAPI<{ job_id: string; status: string; message: string }>("/pipelines/run", {
    method: "POST",
    body: JSON.stringify({
      pipeline_id: pipelineId,
      params,
      confirmation_token: confirmationToken,
    }),
  });
}

export async function getJob(jobId: string): Promise<JobStatus> {
  return fetchAPI<JobStatus>(`/pipelines/jobs/${jobId}`);
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

export interface ClearPipelineResponse {
  pipeline_id: string;
  deleted_count: number;
  deleted_paths: string[];
  message: string;
}

export async function clearPipelineOutputs(
  pipelineId: string,
  params?: { subject_id?: string; test_id?: string }
): Promise<ClearPipelineResponse> {
  const queryParams = new URLSearchParams();
  if (params?.subject_id) queryParams.set("subject_id", params.subject_id);
  if (params?.test_id) queryParams.set("test_id", params.test_id);
  const query = queryParams.toString();
  return fetchAPI<ClearPipelineResponse>(
    `/pipelines/${pipelineId}/clear${query ? `?${query}` : ""}`,
    { method: "DELETE" }
  );
}

// -----------------------------------------------------------------------------
// Sync API (Global - deprecated, use course-scoped sync instead)
// -----------------------------------------------------------------------------

export async function getSyncStatus(): Promise<SyncStatus> {
  return fetchAPI<SyncStatus>("/sync/status");
}

// -----------------------------------------------------------------------------
// Course-scoped Sync API
// -----------------------------------------------------------------------------

export type SyncEnvironment = "local" | "staging" | "prod";

export interface SyncDiffResponse {
  environment: SyncEnvironment;
  has_changes: boolean;
  entities: Record<string, {
    local_count: number;
    db_count: number;
    new: string[];
    new_count: number;
    modified: string[];
    modified_count: number;
    deleted: string[];
    deleted_count: number;
    unchanged: number;
    has_changes: boolean;
  }>;
  error: string | null;
}

export async function getCourseSyncDiff(
  courseId: string,
  environment: SyncEnvironment = "local"
): Promise<SyncDiffResponse> {
  return fetchAPI<SyncDiffResponse>(
    `/subjects/${courseId}/sync/diff?environment=${environment}`
  );
}

export async function previewCourseSync(
  courseId: string,
  entities: string[],
  environment: SyncEnvironment = "local"
): Promise<SyncPreviewResponse> {
  return fetchAPI<SyncPreviewResponse>(`/subjects/${courseId}/sync/preview`, {
    method: "POST",
    body: JSON.stringify({
      entities,
      environment,
    }),
  });
}

export async function executeCourseSync(
  courseId: string,
  entities: string[],
  environment: SyncEnvironment,
  confirm: boolean
): Promise<SyncExecuteResponse> {
  return fetchAPI<SyncExecuteResponse>(`/subjects/${courseId}/sync/execute`, {
    method: "POST",
    body: JSON.stringify({
      entities,
      environment,
      confirm,
    }),
  });
}

// -----------------------------------------------------------------------------
// Enrichment API
// -----------------------------------------------------------------------------

export interface StartEnrichmentParams {
  question_ids?: string[];
  all_tagged?: boolean;
  skip_already_enriched?: boolean;
}

export async function startEnrichment(
  subjectId: string,
  testId: string,
  params: StartEnrichmentParams
): Promise<{ job_id: string }> {
  return fetchAPI<{ job_id: string }>(
    `/subjects/${subjectId}/tests/${testId}/enrich`,
    {
      method: "POST",
      body: JSON.stringify(params),
    }
  );
}

export async function getEnrichmentStatus(
  subjectId: string,
  testId: string,
  jobId: string
): Promise<EnrichmentJobResponse> {
  return fetchAPI<EnrichmentJobResponse>(
    `/subjects/${subjectId}/tests/${testId}/enrich/status/${jobId}`
  );
}

// -----------------------------------------------------------------------------
// Validation API
// -----------------------------------------------------------------------------

export interface StartValidationParams {
  question_ids?: string[];
  all_enriched?: boolean;
  revalidate_passed?: boolean;
}

export async function startValidation(
  subjectId: string,
  testId: string,
  params: StartValidationParams
): Promise<{ job_id: string }> {
  return fetchAPI<{ job_id: string }>(
    `/subjects/${subjectId}/tests/${testId}/validate`,
    {
      method: "POST",
      body: JSON.stringify(params),
    }
  );
}

export async function getValidationStatus(
  subjectId: string,
  testId: string,
  jobId: string
): Promise<ValidationJobResponse> {
  return fetchAPI<ValidationJobResponse>(
    `/subjects/${subjectId}/tests/${testId}/validate/status/${jobId}`
  );
}

// -----------------------------------------------------------------------------
// Variant Enrichment & Validation API (DRY - reuses same job status endpoints)
// -----------------------------------------------------------------------------

export interface StartVariantEnrichmentParams {
  question_num?: string;
  skip_already_enriched?: boolean;
}

export async function startVariantEnrichment(
  subjectId: string,
  testId: string,
  params: StartVariantEnrichmentParams
): Promise<{ job_id: string }> {
  return fetchAPI<{ job_id: string }>(
    `/subjects/${subjectId}/tests/${testId}/variants/enrich`,
    {
      method: "POST",
      body: JSON.stringify(params),
    }
  );
}

export interface StartVariantValidationParams {
  question_num?: string;
  revalidate_passed?: boolean;
}

export async function startVariantValidation(
  subjectId: string,
  testId: string,
  params: StartVariantValidationParams
): Promise<{ job_id: string }> {
  return fetchAPI<{ job_id: string }>(
    `/subjects/${subjectId}/tests/${testId}/variants/validate`,
    {
      method: "POST",
      body: JSON.stringify(params),
    }
  );
}

// Note: Variant jobs use the same status endpoints as questions
// getEnrichmentStatus and getValidationStatus work for both

// -----------------------------------------------------------------------------
// Test Sync API
// -----------------------------------------------------------------------------

export interface TestSyncParams {
  include_variants?: boolean;
  upload_images?: boolean;
}

export async function getTestSyncPreview(
  subjectId: string,
  testId: string,
  params: TestSyncParams
): Promise<TestSyncPreview> {
  return fetchAPI<TestSyncPreview>(
    `/subjects/${subjectId}/tests/${testId}/sync/preview`,
    {
      method: "POST",
      body: JSON.stringify(params),
    }
  );
}

export async function executeTestSync(
  subjectId: string,
  testId: string,
  params: TestSyncParams
): Promise<TestSyncResult> {
  return fetchAPI<TestSyncResult>(
    `/subjects/${subjectId}/tests/${testId}/sync/execute`,
    {
      method: "POST",
      body: JSON.stringify(params),
    }
  );
}
