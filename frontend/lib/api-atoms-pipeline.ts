/**
 * API functions for the atom pipeline (structural checks, validation,
 * fix, coverage). Split from api.ts to keep files under 500 lines.
 *
 * Re-exported from api.ts so consumers don't need to change imports.
 */

import type {
  AtomFixJobResponse,
  AtomFixStatusResponse,
  AtomPipelineSummary,
  AtomValidationJobResponse,
  AtomValidationStatusResponse,
  CoverageAnalysisResult,
  SavedValidationSummary,
  StructuralChecksResult,
} from "./api-types";
import { fetchAPI } from "./api";

// --- Pipeline summary ---

export async function getAtomPipelineSummary(
  subjectId: string,
): Promise<AtomPipelineSummary> {
  return fetchAPI<AtomPipelineSummary>(
    `/subjects/${subjectId}/atoms/pipeline-summary`,
  );
}

// --- Structural checks ---

export async function getAtomStructuralChecks(
  subjectId: string,
): Promise<StructuralChecksResult> {
  return fetchAPI<StructuralChecksResult>(
    `/subjects/${subjectId}/atoms/structural-checks`,
  );
}

export async function getSavedStructuralChecks(
  subjectId: string,
): Promise<StructuralChecksResult | null> {
  return fetchAPI<StructuralChecksResult | null>(
    `/subjects/${subjectId}/atoms/structural-checks/saved`,
  );
}

// --- LLM validation ---

export async function startAtomValidation(
  subjectId: string,
  params: { selection_mode: string; standard_ids?: string[] },
): Promise<AtomValidationJobResponse> {
  return fetchAPI<AtomValidationJobResponse>(
    `/subjects/${subjectId}/atoms/validate`,
    { method: "POST", body: JSON.stringify(params) },
  );
}

export async function getAtomValidationStatus(
  subjectId: string,
  jobId: string,
): Promise<AtomValidationStatusResponse> {
  return fetchAPI<AtomValidationStatusResponse>(
    `/subjects/${subjectId}/atoms/validate/status/${jobId}`,
  );
}

export async function getAtomValidationResults(
  subjectId: string,
): Promise<SavedValidationSummary[]> {
  return fetchAPI<SavedValidationSummary[]>(
    `/subjects/${subjectId}/atoms/validation-results`,
  );
}

// --- LLM fix ---

export async function startAtomFix(
  subjectId: string,
  params: {
    dry_run: boolean;
    fix_types?: string[];
    standard_ids?: string[];
  },
): Promise<AtomFixJobResponse> {
  return fetchAPI<AtomFixJobResponse>(
    `/subjects/${subjectId}/atoms/fix`,
    { method: "POST", body: JSON.stringify(params) },
  );
}

export async function getAtomFixStatus(
  subjectId: string,
  jobId: string,
): Promise<AtomFixStatusResponse> {
  return fetchAPI<AtomFixStatusResponse>(
    `/subjects/${subjectId}/atoms/fix/status/${jobId}`,
  );
}

export async function applyAtomFixSaved(
  subjectId: string,
): Promise<AtomFixJobResponse> {
  return fetchAPI<AtomFixJobResponse>(
    `/subjects/${subjectId}/atoms/fix/apply-saved`,
    { method: "POST" },
  );
}

export async function retryAtomFixFailed(
  subjectId: string,
  params: { dry_run: boolean },
): Promise<AtomFixJobResponse> {
  return fetchAPI<AtomFixJobResponse>(
    `/subjects/${subjectId}/atoms/fix/retry-failed`,
    { method: "POST", body: JSON.stringify(params) },
  );
}

// --- Coverage ---

export async function getAtomCoverage(
  subjectId: string,
): Promise<CoverageAnalysisResult> {
  return fetchAPI<CoverageAnalysisResult>(
    `/subjects/${subjectId}/atoms/coverage`,
  );
}
