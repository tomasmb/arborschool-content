# Frontend TypeScript Types

> **Type**: Reference Document
> **Usage**: Copy these types to `frontend/lib/api-types.ts`

## New Types to Add

```typescript
// ─────────────────────────────────────────────────────────────────
// Question Types (Updated)
// ─────────────────────────────────────────────────────────────────

interface QuestionBrief {
  id: string;
  question_number: number;
  has_split_pdf: boolean;
  has_qti: boolean;
  is_finalized: boolean;
  is_tagged: boolean;
  atoms_count: number;
  variants_count: number;
  // NEW
  is_enriched: boolean;
  is_validated: boolean;
  can_sync: boolean;
}

interface QuestionDetail extends QuestionBrief {
  qti_xml: string;
  selected_atoms: AtomBrief[];
  difficulty_level: string;
  difficulty_score: number | null;
  // NEW
  validation_result: ValidationResult | null;
  sync_status: SyncStatus;
}

type SyncStatus = "not_in_db" | "in_sync" | "local_changed" | "not_validated";

// ─────────────────────────────────────────────────────────────────
// Test Types (Updated)
// ─────────────────────────────────────────────────────────────────

interface TestDetail {
  id: string;
  name: string;
  subject_id: string;
  question_count: number;
  split_count: number;
  qti_count: number;
  finalized_count: number;
  tagged_count: number;
  // NEW
  enriched_count: number;
  validated_count: number;
  syncable_count: number;
}

// ─────────────────────────────────────────────────────────────────
// Validation Types
// ─────────────────────────────────────────────────────────────────

type CheckStatus = "pass" | "fail" | "not_applicable";

interface CheckResult {
  status: CheckStatus;
  issues: string[];
  reasoning: string;
}

interface CorrectAnswerCheck extends CheckResult {
  expected_answer: string;
  marked_answer: string;
  verification_steps: string;
}

interface ContentQualityCheck {
  status: CheckStatus;
  typos_found: string[];
  character_issues: string[];
  clarity_issues: string[];
}

interface ValidationResult {
  validation_result: "pass" | "fail";
  correct_answer_check: CorrectAnswerCheck;
  feedback_check: CheckResult;
  content_quality_check: ContentQualityCheck;
  image_check: CheckResult;
  math_validity_check: CheckResult;
  overall_reasoning: string;
}

// ─────────────────────────────────────────────────────────────────
// Enrichment Types
// ─────────────────────────────────────────────────────────────────

interface EnrichmentRequest {
  question_ids?: string[];
  all_tagged?: boolean;
  skip_already_enriched?: boolean;
}

interface EnrichmentJobResponse {
  job_id: string;
  status: JobStatus;
  questions_to_process: number;
  estimated_cost_usd: number;
}

interface EnrichmentProgress {
  total: number;
  completed: number;
  successful: number;
  failed: number;
}

interface EnrichmentStatusResponse {
  job_id: string;
  status: JobStatus;
  progress: EnrichmentProgress;
  current_question: string | null;
  results: EnrichmentQuestionResult[];
  started_at: string;
  completed_at: string | null;
}

interface EnrichmentQuestionResult {
  question_id: string;
  status: "success" | "failed";
  error?: string;
}

// ─────────────────────────────────────────────────────────────────
// Validation Job Types
// ─────────────────────────────────────────────────────────────────

interface ValidationRequest {
  question_ids?: string[];
  all_enriched?: boolean;
  revalidate_passed?: boolean;
}

interface ValidationJobResponse {
  job_id: string;
  status: JobStatus;
  questions_to_process: number;
  estimated_cost_usd: number;
}

interface ValidationProgress {
  total: number;
  completed: number;
  passed: number;
  failed: number;
}

interface ValidationStatusResponse {
  job_id: string;
  status: JobStatus;
  progress: ValidationProgress;
  results: ValidationQuestionResult[];
  started_at: string;
  completed_at: string | null;
}

interface ValidationQuestionResult {
  question_id: string;
  status: "pass" | "fail";
  failed_checks?: string[];
  issues?: string[];
}

// ─────────────────────────────────────────────────────────────────
// Sync Types
// ─────────────────────────────────────────────────────────────────

interface SyncPreviewRequest {
  include_variants?: boolean;
  upload_images?: boolean;
}

interface QuestionDiff {
  question_id: string;
  question_number: number;
  status: "create" | "update" | "unchanged" | "skipped";
  reason?: string;
  changes?: {
    qti_xml_changed: boolean;
    feedback_added: boolean;
    feedback_changed: boolean;
  };
  is_validated: boolean;
  validation_passed: boolean;
}

interface SyncPreviewResponse {
  questions: {
    to_create: QuestionDiff[];
    to_update: QuestionDiff[];
    unchanged: QuestionDiff[];
    skipped: QuestionDiff[];
  };
  summary: {
    create: number;
    update: number;
    unchanged: number;
    skipped: number;
  };
}

interface SyncExecuteRequest {
  include_variants?: boolean;
  upload_images?: boolean;
}

interface SyncExecuteResponse {
  created: number;
  updated: number;
  skipped: number;
  details: SyncResultDetail[];
}

interface SyncResultDetail {
  question_id: string;
  action: "created" | "updated" | "skipped";
  reason?: string;
}

// ─────────────────────────────────────────────────────────────────
// Common Types
// ─────────────────────────────────────────────────────────────────

type JobStatus = "started" | "in_progress" | "completed" | "failed";
```

## Types to Remove

The following types should be removed as they're no longer used:

```typescript
// REMOVE THESE
interface FeedbackGeneral {
  // Old format - no longer used
}

interface FeedbackPerOption {
  // Old format - no longer used
}

// Remove from QuestionDetail:
// - correct_answer: string
// - feedback_general: string
// - feedback_per_option: Record<string, string>
```
