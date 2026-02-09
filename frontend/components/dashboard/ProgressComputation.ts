/**
 * Progress computation utilities for CourseProgressDashboard.
 * Extracted to keep files under 500 lines (DRY/SOLID).
 */

import type { SubjectDetail } from "@/lib/api-types";

// -----------------------------------------------------------------------------
// Types
// -----------------------------------------------------------------------------

export interface PipelineStage {
  label: string;
  done: number;
  total: number;
}

export interface ActionItem {
  type: "warning" | "info";
  message: string;
  count: number;
}

/**
 * Type of next action - used to determine what to do when user clicks "Next"
 */
export type NextActionType =
  | "upload_temario"
  | "generate_standards"
  | "generate_atoms"
  | "upload_tests"
  | "run_split"
  | "run_qti_parse"
  | "run_tagging"
  | "run_enrichment"
  | "run_validation"
  | null;

export interface ComputedProgress {
  overallPercent: number;
  nextAction: string | null;
  nextActionType: NextActionType;
  /** Test ID for test-specific actions (split, parse, tag, etc.) */
  nextActionTestId: string | null;
  knowledgePipeline: {
    standards: { done: boolean; count: number; byEje: Record<string, number> };
    atoms: { done: boolean; count: number; byEje: Record<string, number> };
    prerequisites: { links: number; orphans: number };
  };
  questionsPipeline: PipelineStage[];
  variants: {
    questionsWithVariants: number;
    questionsWithValidatedVariants: number;
    totalQuestions: number;
    totalVariants: number;
    variantsEnriched: number;
    variantsValidated: number;
  };
  actionItems: ActionItem[];
}

// -----------------------------------------------------------------------------
// Helpers
// -----------------------------------------------------------------------------

/**
 * Build a human-readable "next action" message for enrichment/validation,
 * covering official questions and/or variants as applicable.
 */
function formatItemsMessage(
  verb: string, questionsLeft: number, variantsLeft: number
): string {
  const parts: string[] = [];
  if (questionsLeft > 0) parts.push(`${questionsLeft} questions`);
  if (variantsLeft > 0) parts.push(`${variantsLeft} variants`);
  return `${verb} ${parts.join(" + ")}`;
}

// -----------------------------------------------------------------------------
// Progress Computation
// -----------------------------------------------------------------------------

export function computeProgress(data: SubjectDetail): ComputedProgress {
  // Aggregate counts across all tests (official questions + variants)
  let totalSplit = 0;
  let totalQti = 0;
  let totalFinalized = 0;
  let totalTagged = 0;
  let totalEnriched = 0;
  let totalValidated = 0;
  let totalVariants = 0;
  let totalVariantsEnriched = 0;
  let totalVariantsValidated = 0;

  for (const test of data.tests) {
    totalSplit += test.split_count;
    totalQti += test.qti_count;
    totalFinalized += test.finalized_count;
    totalTagged += test.tagged_count;
    totalEnriched += test.enriched_count;
    totalValidated += test.validated_count;
    totalVariants += test.variants_count;
    totalVariantsEnriched += test.enriched_variants_count ?? 0;
    totalVariantsValidated += test.validated_variants_count ?? 0;
  }

  const totalTests = data.tests.length;
  const testsWithPdf = data.tests.filter((t) => t.raw_pdf_exists).length;
  const totalQuestions = totalFinalized;

  // Combined totals: official questions + variants
  const allItems = totalQuestions + totalVariants;
  const allEnriched = totalEnriched + totalVariantsEnriched;
  const allValidated = totalValidated + totalVariantsValidated;

  // Standards by eje
  const standardsByEje: Record<string, number> = {};
  for (const std of data.standards) {
    standardsByEje[std.eje] = (standardsByEje[std.eje] || 0) + 1;
  }

  // Knowledge pipeline status
  const hasStandards = data.standards.length > 0;
  const hasAtoms = data.atoms_count > 0;

  // Questions pipeline stages (official questions only for pipeline stages)
  const questionsPipeline: PipelineStage[] = [
    { label: "PDF Tests", done: testsWithPdf, total: totalTests },
    { label: "Split", done: totalSplit, total: totalQuestions || totalSplit },
    { label: "QTI Parsed", done: totalQti, total: totalQuestions || totalQti },
    { label: "Tagged", done: totalTagged, total: totalFinalized },
    { label: "Enriched", done: totalEnriched, total: totalFinalized },
    { label: "Validated", done: totalValidated, total: totalFinalized },
  ];

  // Calculate overall progress (weighted average of key stages)
  const weights = {
    standards: 10,
    atoms: 10,
    split: 15,
    qti: 15,
    tagged: 10,
    enriched: 20,
    validated: 20,
  };

  let weightedSum = 0;
  let totalWeight = 0;

  if (data.temario_exists) {
    weightedSum += (hasStandards ? 100 : 0) * weights.standards;
    totalWeight += weights.standards;
    weightedSum += (hasAtoms ? 100 : 0) * weights.atoms;
    totalWeight += weights.atoms;
  }

  if (totalQuestions > 0) {
    weightedSum += (totalSplit / totalQuestions) * 100 * weights.split;
    totalWeight += weights.split;
    weightedSum += (totalQti / totalQuestions) * 100 * weights.qti;
    totalWeight += weights.qti;
    weightedSum += (totalTagged / totalQuestions) * 100 * weights.tagged;
    totalWeight += weights.tagged;
    weightedSum += (totalEnriched / totalQuestions) * 100 * weights.enriched;
    totalWeight += weights.enriched;
    weightedSum += (totalValidated / totalQuestions) * 100 * weights.validated;
    totalWeight += weights.validated;
  }

  const overallPercent = totalWeight > 0 ? Math.round(weightedSum / totalWeight) : 0;

  // Determine next action and its type
  let nextAction: string | null = null;
  let nextActionType: NextActionType = null;
  let nextActionTestId: string | null = null;

  // Find the first test that needs work for test-specific actions
  const findTestNeedingWork = (
    predicate: (t: SubjectDetail["tests"][0]) => boolean
  ): string | null => {
    const test = data.tests.find(predicate);
    return test?.id ?? null;
  };

  // Unenriched/unvalidated counts (official questions + variants)
  const unenrichedItems = allItems - allEnriched;
  const unvalidatedItems = allItems - allValidated;

  if (!data.temario_exists) {
    nextAction = "Upload temario PDF";
    nextActionType = "upload_temario";
  } else if (!hasStandards) {
    nextAction = "Generate standards";
    nextActionType = "generate_standards";
  } else if (!hasAtoms) {
    nextAction = "Generate atoms";
    nextActionType = "generate_atoms";
  } else if (totalTests === 0) {
    nextAction = "Upload test PDFs";
    nextActionType = "upload_tests";
  } else if (totalSplit === 0) {
    nextAction = "Run PDF splitting";
    nextActionType = "run_split";
    nextActionTestId = findTestNeedingWork(
      (t) => t.raw_pdf_exists && t.split_count === 0
    );
  } else if (totalQti < totalSplit) {
    nextAction = `Parse ${totalSplit - totalQti} questions to QTI`;
    nextActionType = "run_qti_parse";
    nextActionTestId = findTestNeedingWork((t) => t.qti_count < t.split_count);
  } else if (totalTagged < totalFinalized) {
    nextAction = `Tag ${totalFinalized - totalTagged} questions`;
    nextActionType = "run_tagging";
    nextActionTestId = findTestNeedingWork(
      (t) => t.tagged_count < t.finalized_count
    );
  } else if (unenrichedItems > 0) {
    nextAction = formatItemsMessage(
      "Enrich", totalFinalized - totalEnriched,
      totalVariants - totalVariantsEnriched
    );
    nextActionType = "run_enrichment";
    nextActionTestId = findTestNeedingWork(
      (t) => t.enriched_count < t.finalized_count
        || (t.enriched_variants_count ?? 0) < t.variants_count
    );
  } else if (unvalidatedItems > 0) {
    nextAction = formatItemsMessage(
      "Validate", totalFinalized - totalValidated,
      totalVariants - totalVariantsValidated
    );
    nextActionType = "run_validation";
    nextActionTestId = findTestNeedingWork(
      (t) => t.validated_count < t.finalized_count
        || (t.validated_variants_count ?? 0) < t.variants_count
    );
  }

  // Action items (include variants)
  const actionItems: ActionItem[] = [];
  if (unenrichedItems > 0) {
    actionItems.push({
      type: "warning",
      message: "items need enrichment",
      count: unenrichedItems,
    });
  }
  if (unvalidatedItems > 0) {
    actionItems.push({
      type: "warning",
      message: "items need validation",
      count: unvalidatedItems,
    });
  }
  if (totalVariants === 0 && totalValidated > 0) {
    actionItems.push({
      type: "info",
      message: "questions have no variants yet",
      count: totalValidated,
    });
  }

  // Count questions that have at least one variant
  const questionsWithVariants = data.tests.reduce(
    (sum, t) => sum + (t.variants_count > 0 ? 1 : 0), 0
  );

  return {
    overallPercent,
    nextAction,
    nextActionType,
    nextActionTestId,
    knowledgePipeline: {
      standards: {
        done: hasStandards,
        count: data.standards.length,
        byEje: standardsByEje,
      },
      atoms: {
        done: hasAtoms,
        count: data.atoms_count,
        byEje: {},
      },
      prerequisites: { links: 0, orphans: 0 },
    },
    questionsPipeline,
    variants: {
      questionsWithVariants,
      questionsWithValidatedVariants: 0,
      totalQuestions: totalFinalized,
      totalVariants,
      variantsEnriched: totalVariantsEnriched,
      variantsValidated: totalVariantsValidated,
    },
    actionItems,
  };
}
