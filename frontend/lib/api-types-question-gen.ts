/**
 * TypeScript interfaces for question generation checkpoint data.
 * Separated from api-types.ts to keep files under 500 lines.
 */

// -----------------------------------------------------------------------------
// Pipeline Report
// -----------------------------------------------------------------------------

export interface PhaseReport {
  name: string;
  success: boolean;
  errors: string[];
  warnings: string[];
}

export interface PipelineReport {
  atom_id: string;
  success: boolean;
  total_planned: number;
  total_generated: number;
  total_passed_dedupe: number;
  total_passed_base_validation: number;
  total_passed_feedback: number;
  total_final: number;
  total_synced: number;
  phases: PhaseReport[];
}

// -----------------------------------------------------------------------------
// Enrichment (Phase 1)
// -----------------------------------------------------------------------------

export interface ErrorFamily {
  name: string;
  description: string;
  how_to_address: string;
}

export interface ScopeGuardrails {
  in_scope: string[];
  out_of_scope: string[];
  prerequisites: string[];
  common_traps: string[];
}

export interface EnrichmentData {
  scope_guardrails: ScopeGuardrails;
  difficulty_rubric: {
    easy: string[];
    medium: string[];
    hard: string[];
  };
  error_families: ErrorFamily[];
  ambiguity_avoid: string[];
  numbers_profiles: string[];
  required_image_types: string[];
}

// -----------------------------------------------------------------------------
// Plan Slots (Phase 3)
// -----------------------------------------------------------------------------

export interface PlanSlot {
  slot_index: number;
  component_tag: string;
  difficulty_level: "easy" | "medium" | "hard";
  operation_skeleton_ast: string;
  surface_context: string;
  numbers_profile: string;
  target_exemplar_id: string | null;
  distance_level: string | null;
  image_required: boolean;
  image_type: string | null;
  image_description: string | null;
}

// -----------------------------------------------------------------------------
// Generated Items (Phase 4+)
// -----------------------------------------------------------------------------

export interface ValidatorStatuses {
  xsd: string;
  paes: string;
  solve_check: string;
  scope: string;
  exemplar_copy_check: string;
  feedback: string;
  dedupe: string;
}

export interface GeneratedItemMeta {
  atom_id: string;
  component_tag: string;
  difficulty_level: string;
  operation_skeleton_ast: string;
  surface_context: string;
  numbers_profile: string;
  fingerprint: string;
  target_exemplar_id: string | null;
  distance_level: string | null;
  validators: ValidatorStatuses;
}

export interface GeneratedItem {
  item_id: string;
  qti_xml: string;
  slot_index: number;
  pipeline_meta: GeneratedItemMeta;
}

// -----------------------------------------------------------------------------
// Full Checkpoint Response
// -----------------------------------------------------------------------------

export interface AtomCheckpointData {
  atom_id: string;
  available_phases: number[];
  pipeline_report: PipelineReport | null;
  enrichment: EnrichmentData | null;
  plan_slots: PlanSlot[] | null;
  generated_items: GeneratedItem[] | null;
  validation_results: GeneratedItem[] | null;
  feedback_items: GeneratedItem[] | null;
}
