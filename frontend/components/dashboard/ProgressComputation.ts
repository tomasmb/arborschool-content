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

export interface ComputedProgress {
  overallPercent: number;
  nextAction: string | null;
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
// Progress Computation
// -----------------------------------------------------------------------------

export function computeProgress(data: SubjectDetail): ComputedProgress {
  // Aggregate counts across all tests
  let totalSplit = 0;
  let totalQti = 0;
  let totalFinalized = 0;
  let totalTagged = 0;
  let totalEnriched = 0;
  let totalValidated = 0;
  let totalVariants = 0;

  for (const test of data.tests) {
    totalSplit += test.split_count;
    totalQti += test.qti_count;
    totalFinalized += test.finalized_count;
    totalTagged += test.tagged_count;
    totalEnriched += test.enriched_count;
    totalValidated += test.validated_count;
    totalVariants += test.variants_count;
  }

  const totalTests = data.tests.length;
  const testsWithPdf = data.tests.filter((t) => t.raw_pdf_exists).length;
  const totalQuestions = totalFinalized;

  // Standards by eje
  const standardsByEje: Record<string, number> = {};
  for (const std of data.standards) {
    standardsByEje[std.eje] = (standardsByEje[std.eje] || 0) + 1;
  }

  // Knowledge pipeline status
  const hasStandards = data.standards.length > 0;
  const hasAtoms = data.atoms_count > 0;

  // Questions pipeline stages
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

  // Determine next action
  let nextAction: string | null = null;
  if (!data.temario_exists) {
    nextAction = "Upload temario PDF";
  } else if (!hasStandards) {
    nextAction = "Generate standards";
  } else if (!hasAtoms) {
    nextAction = "Generate atoms";
  } else if (totalTests === 0) {
    nextAction = "Upload test PDFs";
  } else if (totalSplit === 0) {
    nextAction = "Run PDF splitting";
  } else if (totalQti < totalSplit) {
    nextAction = `Parse ${totalSplit - totalQti} questions to QTI`;
  } else if (totalTagged < totalFinalized) {
    nextAction = `Tag ${totalFinalized - totalTagged} questions`;
  } else if (totalEnriched < totalFinalized) {
    nextAction = `Enrich ${totalFinalized - totalEnriched} questions`;
  } else if (totalValidated < totalFinalized) {
    nextAction = `Validate ${totalFinalized - totalValidated} questions`;
  }

  // Action items
  const actionItems: ActionItem[] = [];
  if (totalFinalized - totalEnriched > 0) {
    actionItems.push({
      type: "warning",
      message: "questions need enrichment",
      count: totalFinalized - totalEnriched,
    });
  }
  if (totalFinalized - totalValidated > 0) {
    actionItems.push({
      type: "warning",
      message: "questions need validation",
      count: totalFinalized - totalValidated,
    });
  }
  if (totalVariants === 0 && totalValidated > 0) {
    actionItems.push({
      type: "info",
      message: "questions have no variants yet",
      count: totalValidated,
    });
  }

  return {
    overallPercent,
    nextAction,
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
      questionsWithVariants: 0,
      questionsWithValidatedVariants: 0,
      totalQuestions: totalFinalized,
      totalVariants,
      variantsEnriched: 0,
      variantsValidated: 0,
    },
    actionItems,
  };
}
