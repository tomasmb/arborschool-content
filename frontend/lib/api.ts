/**
 * API client for the Arbor Content Dashboard backend.
 */

// Re-export all types for backward compatibility
export type {
  AtomBrief,
  AtomTag,
  ConfigStatus,
  CostEstimate,
  FailedItem,
  GraphData,
  GraphEdge,
  GraphNode,
  JobListResponse,
  JobLogsResponse,
  JobStatus,
  OverviewResponse,
  PipelineDefinition,
  PipelineParam,
  QuestionBrief,
  QuestionDetail,
  QuestionOption,
  StandardBrief,
  SubjectBrief,
  SubjectDetail,
  SubjectStats,
  SyncExecuteResponse,
  SyncPreviewResponse,
  SyncStatus,
  SyncTableSummary,
  TestBrief,
  TestDetail,
  UnlockStatus,
  VariantBrief,
} from "./api-types";

import type {
  ConfigStatus,
  CostEstimate,
  GraphData,
  JobListResponse,
  JobLogsResponse,
  JobStatus,
  OverviewResponse,
  PipelineDefinition,
  PipelineParam,
  QuestionDetail,
  StandardBrief,
  AtomBrief,
  SubjectDetail,
  SyncExecuteResponse,
  SyncPreviewResponse,
  SyncStatus,
  TestBrief,
  TestDetail,
  UnlockStatus,
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
// Overview & Config API
// -----------------------------------------------------------------------------

export async function getOverview(): Promise<OverviewResponse> {
  return fetchAPI<OverviewResponse>("/overview");
}

export async function getConfigStatus(): Promise<ConfigStatus> {
  return fetchAPI<ConfigStatus>("/config-status");
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

export async function getAtomsUnlockStatus(subjectId: string): Promise<UnlockStatus> {
  return fetchAPI<UnlockStatus>(`/subjects/${subjectId}/atoms/unlock-status`);
}

export async function getTemario(subjectId: string): Promise<Record<string, unknown>> {
  return fetchAPI<Record<string, unknown>>(`/subjects/${subjectId}/temario`);
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

// -----------------------------------------------------------------------------
// Pipeline API
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
  return fetchAPI<{ job_id: string; status: string; message: string }>("/pipelines/run", {
    method: "POST",
    body: JSON.stringify({
      pipeline_id: pipelineId,
      params,
      confirmation_token: confirmationToken,
    }),
  });
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
// Sync API
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
