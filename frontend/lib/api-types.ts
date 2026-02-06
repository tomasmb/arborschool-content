/**
 * TypeScript interfaces matching backend API schemas.
 * Separated from api.ts to keep files under 500 lines.
 */

// -----------------------------------------------------------------------------
// Subject & Overview Types
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
  enriched_count: number;
  validated_count: number;
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

// -----------------------------------------------------------------------------
// Question Types
// -----------------------------------------------------------------------------

export interface QuestionBrief {
  id: string;
  question_number: number;
  has_split_pdf: boolean;
  has_qti: boolean;
  is_finalized: boolean;
  is_tagged: boolean;
  is_enriched: boolean;
  is_validated: boolean;
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
  is_enriched: boolean;
  is_validated: boolean;
}

export interface QuestionOption {
  id: string;
  text: string;
}

/**
 * Full question detail for the slide-over panel.
 *
 * Note: correct_answer and feedback are now embedded in qti_xml and parsed
 * by the frontend when displaying questions (FeedbackTab component).
 */
export interface QuestionDetail {
  id: string;
  test_id: string;
  question_number: number;
  has_split_pdf: boolean;
  has_qti: boolean;
  is_finalized: boolean;
  is_tagged: boolean;
  is_enriched: boolean;
  is_validated: boolean;
  can_sync: boolean;
  qti_xml: string | null;
  qti_stem: string | null;
  qti_options: QuestionOption[] | null;
  difficulty: string | null;
  source_info: Record<string, unknown> | null;
  atom_tags: AtomTag[];
  variants: VariantBrief[];
  qti_path: string | null;
  pdf_path: string | null;
  sync_status: QuestionSyncStatus | null;
  validation_result: ValidationResultDetail | null;
}

// -----------------------------------------------------------------------------
// Question Sync Status (for individual questions)
// -----------------------------------------------------------------------------

export type QuestionSyncStatus = "not_in_db" | "in_sync" | "local_changed" | "not_validated";

// -----------------------------------------------------------------------------
// Detailed Validation Types (for display in ValidationTab)
// -----------------------------------------------------------------------------

export type CheckStatus = "pass" | "fail" | "not_applicable";

export interface CheckResult {
  status: CheckStatus;
  issues: string[];
  reasoning: string;
}

export interface CorrectAnswerCheck {
  status: CheckStatus;
  expected_answer: string;
  marked_answer: string;
  verification_steps: string;
  issues: string[];
}

export interface ContentQualityCheck {
  status: CheckStatus;
  typos_found: string[];
  character_issues: string[];
  clarity_issues: string[];
}

/**
 * Detailed validation result for display in the question panel.
 * This is the full result from FinalValidator, stored in validation_result.json.
 */
export interface ValidationResultDetail {
  validation_result: "pass" | "fail";
  correct_answer_check: CorrectAnswerCheck;
  feedback_check: CheckResult;
  content_quality_check: ContentQualityCheck;
  image_check: CheckResult;
  math_validity_check: CheckResult;
  overall_reasoning: string;
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
  enriched_count: number;
  validated_count: number;
  variants_count: number;
  // Variant-level enrichment/validation stats
  enriched_variants_count: number;
  validated_variants_count: number;
  failed_validation_variants_count: number;
  questions: QuestionBrief[];
}

// -----------------------------------------------------------------------------
// Enrichment & Validation Types
// -----------------------------------------------------------------------------

export interface EnrichmentProgress {
  completed: number;
  total: number;
  failed: number;
}

export interface EnrichmentFailureDetails {
  stage_failed?: string;
  issues?: string[];
  reasoning?: string;
}

export interface EnrichmentResult {
  question_id: string;
  status: "success" | "failed";
  error?: string;
  details?: EnrichmentFailureDetails;
}

export interface EnrichmentJobResponse {
  job_id: string;
  status: "pending" | "running" | "completed";
  progress: EnrichmentProgress;
  results?: EnrichmentResult[];
}

export interface ValidationProgress {
  completed: number;
  total: number;
  passed: number;
  failed: number;
}

export interface ValidationResult {
  question_id: string;
  status: "pass" | "fail";
  failed_checks?: string[];
  issues?: string[];
}

export interface ValidationJobResponse {
  job_id: string;
  status: "pending" | "running" | "completed";
  progress: ValidationProgress;
  results?: ValidationResult[];
}

export interface SyncPreviewQuestions {
  to_create: Array<{ id: string; question_number: number }>;
  to_update: Array<{ id: string; question_number: number }>;
  unchanged: Array<{ id: string; question_number: number }>;
  skipped: Array<{ id: string; question_number: number; reason: string }>;
}

export interface SyncPreviewSummary {
  create: number;
  update: number;
  unchanged: number;
  skipped: number;
}

export interface TestSyncPreview {
  questions: SyncPreviewQuestions;
  variants: SyncPreviewQuestions;
  summary: SyncPreviewSummary;
  question_summary: SyncPreviewSummary | null;
  variant_summary: SyncPreviewSummary | null;
}

export interface TestSyncResult {
  success: boolean;
  created: number;
  updated: number;
  skipped: number;
  errors: string[];
}

export interface TestSyncDiffEntity {
  local_count: number;
  db_count: number;
  new_count: number;
  deleted_count: number;
  unchanged_count: number;
  has_changes: boolean;
}

export interface TestSyncDiff {
  environment: string;
  has_changes: boolean;
  questions: TestSyncDiffEntity;
  variants: TestSyncDiffEntity;
  error: string | null;
}

// -----------------------------------------------------------------------------
// Graph Types
// -----------------------------------------------------------------------------

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
// Config Status Types
// -----------------------------------------------------------------------------

export interface ConfigStatus {
  database: {
    configured: boolean;
    required_vars: string[];
    description: string;
  };
  s3: {
    configured: boolean;
    required_vars: string[];
    optional_vars: string[];
    description: string;
  };
  ai: {
    gemini_configured: boolean;
    openai_configured: boolean;
    any_configured: boolean;
    required_vars: string[];
    optional_vars: string[];
    description: string;
  };
  summary: {
    can_sync: boolean;
    can_upload_images: boolean;
    can_run_ai_pipelines: boolean;
  };
}

export interface UnlockStatus {
  all_questions_tagged: boolean;
  tagged_count: number;
  total_count: number;
  completion_percentage: number;
  tests_status: Record<string, { tagged: number; total: number; complete: boolean }>;
}

// -----------------------------------------------------------------------------
// Pipeline Types
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

export interface JobLogsResponse {
  job_id: string;
  logs: string[];
  offset: number;
  limit: number;
  total: number;
  has_more: boolean;
}

// Note: Course progress types are computed client-side in
// components/dashboard/ProgressComputation.ts - not API types
