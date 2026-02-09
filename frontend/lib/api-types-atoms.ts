/**
 * TypeScript interfaces for atom pipeline API endpoints.
 * Separated from api-types.ts to keep files under 500 lines.
 */

// -----------------------------------------------------------------------------
// Atom Pipeline Summary
// -----------------------------------------------------------------------------

export interface AtomPipelineSummary {
  has_standards: boolean;
  atom_count: number;
  standards_count: number;
  last_generation_date: string | null;
  structural_checks_passed: boolean | null;
  standards_validated: number;
  standards_with_issues: number;
  has_saved_fix_results: boolean;
}

// -----------------------------------------------------------------------------
// Structural Checks
// -----------------------------------------------------------------------------

export interface StructuralCheckItem {
  atom_id: string | null;
  check: string;
  severity: "error" | "warning";
  message: string;
}

export interface StructuralChecksResult {
  passed: boolean;
  total_atoms: number;
  ran_at: string | null;
  schema_errors: number;
  id_eje_errors: number;
  circular_dependencies: number;
  missing_prerequisites: number;
  missing_standard_refs: number;
  granularity_warnings: number;
  issues: StructuralCheckItem[];
  cycles: string[][];
  graph_stats: Record<string, number>;
}

// -----------------------------------------------------------------------------
// LLM Validation
// -----------------------------------------------------------------------------

export interface AtomValidationJobResponse {
  job_id: string;
  status: string;
  standards_to_validate: number;
  estimated_cost_usd: number;
}

export interface AtomValidationProgress {
  total: number;
  completed: number;
  passed: number;
  with_issues: number;
}

export interface StandardValidationResult {
  standard_id: string;
  status: "pass" | "issues" | "error";
  evaluation_summary: Record<string, unknown> | null;
  atoms_evaluation: Record<string, unknown>[];
  coverage_analysis: Record<string, unknown> | null;
  global_recommendations: string[];
  error: string | null;
}

export interface AtomValidationStatusResponse {
  job_id: string;
  status: string;
  progress: AtomValidationProgress;
  results: StandardValidationResult[];
  started_at: string;
  completed_at: string | null;
}

// -----------------------------------------------------------------------------
// Coverage Analysis
// -----------------------------------------------------------------------------

export interface StandardCoverageItem {
  standard_id: string;
  title: string;
  atom_count: number;
  coverage_status: "full" | "partial" | "none";
}

export interface AtomQuestionCoverage {
  atom_id: string;
  titulo: string;
  eje: string;
  direct_questions: number;
  transitive_coverage: boolean;
  coverage_status: "direct" | "transitive" | "none";
}

export interface OverlapCandidate {
  atom_a: string;
  atom_b: string;
  shared_standards: string[];
  reason: string;
}

export interface CoverageAnalysisResult {
  total_standards: number;
  standards_fully_covered: number;
  standards_partially_covered: number;
  standards_not_covered: number;
  standards_coverage: StandardCoverageItem[];
  total_atoms: number;
  atoms_with_direct_questions: number;
  atoms_with_transitive_coverage: number;
  atoms_without_coverage: number;
  atom_question_coverage: AtomQuestionCoverage[];
  overlap_candidates: OverlapCandidate[];
  eje_distribution: Record<string, number>;
  type_distribution: Record<string, number>;
}

// -----------------------------------------------------------------------------
// Saved Validation Results
// -----------------------------------------------------------------------------

export interface SavedValidationSummary {
  standard_id: string;
  overall_quality: string | null;
  coverage_assessment: string | null;
  granularity_assessment: string | null;
  total_atoms: number;
  atoms_passing: number;
  atoms_with_issues: number;
}

// -----------------------------------------------------------------------------
// LLM Fix Pipeline
// -----------------------------------------------------------------------------

export interface AtomFixJobResponse {
  job_id: string;
  status: string;
  actions_to_fix: number;
  estimated_cost_usd: number;
  dry_run: boolean;
}

export interface AtomFixProgress {
  total: number;
  completed: number;
  succeeded: number;
  failed: number;
}

export interface AtomFixActionResult {
  fix_type: string;
  atom_ids: string[];
  standard_id: string;
  success: boolean;
  error: string | null;
}

export interface AtomFixChangeReport {
  atoms_added: string[];
  atoms_removed: string[];
  atoms_modified: string[];
  prerequisite_cascades: number;
  question_mapping_updates: number;
  manual_review_needed: string[];
}

export interface AtomFixStatusResponse {
  job_id: string;
  status: string;
  dry_run: boolean;
  progress: AtomFixProgress;
  results: AtomFixActionResult[];
  change_report: AtomFixChangeReport | null;
  has_saved_results: boolean;
  started_at: string;
  completed_at: string | null;
}

// -----------------------------------------------------------------------------
// Course Sync (used by atom sync tab)
// -----------------------------------------------------------------------------

export interface CourseSyncTableSummary {
  table: string;
  total: number;
  breakdown: Record<string, number>;
}

export interface CourseSyncPreview {
  tables: CourseSyncTableSummary[];
  summary: Record<string, unknown>;
  warnings: string[];
  environment: string;
}

export interface CourseSyncResult {
  success: boolean;
  results: Record<string, number>;
  message: string;
  errors: string[];
  environment: string;
}

export interface CourseSyncDiff {
  environment: string;
  has_changes: boolean;
  entities: Record<string, CourseSyncEntityDiff>;
  error?: string;
}

export interface CourseSyncEntityDiff {
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
}
