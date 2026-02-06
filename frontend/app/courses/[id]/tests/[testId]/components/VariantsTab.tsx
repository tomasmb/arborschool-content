"use client";

import { useState, useCallback } from "react";
import { Plus, Trash2, ChevronDown, ChevronRight, Sparkles, MessageSquarePlus, ShieldCheck, RefreshCw, CheckCircle2, Circle } from "lucide-react";
import { cn } from "@/lib/utils";
import { ProgressRatio, ActionButton, ActionsDropdown, StepBanner } from "@/components/ui";
import { type QuestionBrief, type TestDetail } from "@/lib/api";
import { VariantsExpandedContent } from "./VariantsExpandedContent";

export interface VariantsTabProps {
  subjectId: string;
  testId: string;
  questions: QuestionBrief[];
  data: TestDetail;
  onGenerateVariants: () => void;
  onEnrichVariants?: () => void;
  onValidateVariants?: () => void;
  onDeleteVariants?: (questionNum: number) => void;
}

type VariantsFilter = "all" | "has_variants" | "no_variants";

/** Determine the next action for the variants pipeline. */
function getVariantNextAction(counts: {
  noVariants: number;
  unenrichedVariants: number;
  unvalidatedVariants: number;
}): "generate" | "enrich" | "validate" | "done" {
  if (counts.noVariants > 0) return "generate";
  if (counts.unenrichedVariants > 0) return "enrich";
  if (counts.unvalidatedVariants > 0) return "validate";
  return "done";
}

export function VariantsTab({
  subjectId,
  testId,
  questions,
  data,
  onGenerateVariants,
  onEnrichVariants,
  onValidateVariants,
  onDeleteVariants,
}: VariantsTabProps) {
  const [filter, setFilter] = useState<VariantsFilter>("all");
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set());

  // Only validated questions can have variants
  const validatedQuestions = questions.filter((q) => q.is_validated);

  // Counts
  const questionsWithVariants = validatedQuestions.filter((q) => q.variants_count > 0).length;
  const questionsNoVariants = validatedQuestions.length - questionsWithVariants;
  const totalVariants = data.variants_count;
  const unenrichedVariants = totalVariants - data.enriched_variants_count;
  const unvalidatedVariants = data.enriched_variants_count - data.validated_variants_count;

  const nextAction = getVariantNextAction({
    noVariants: questionsNoVariants,
    unenrichedVariants,
    unvalidatedVariants,
  });

  // Filter
  const filteredQuestions = validatedQuestions.filter((q) => {
    if (filter === "has_variants") return q.variants_count > 0;
    if (filter === "no_variants") return q.variants_count === 0;
    return true;
  });

  const toggleRow = useCallback((questionNum: number) => {
    setExpandedRows((prev) => {
      const next = new Set(prev);
      if (next.has(questionNum)) next.delete(questionNum);
      else next.add(questionNum);
      return next;
    });
  }, []);

  const filters: { id: VariantsFilter; label: string; count: number }[] = [
    { id: "all", label: "All", count: validatedQuestions.length },
    { id: "has_variants", label: "Has Variants", count: questionsWithVariants },
    { id: "no_variants", label: "No Variants", count: questionsNoVariants },
  ];

  // Secondary / overflow actions
  const secondaryActions = [
    {
      id: "add-more",
      label: "Add More Variants",
      icon: <Plus className="w-4 h-4" />,
      onClick: onGenerateVariants,
    },
    {
      id: "enrich",
      label: "Enrich Variants",
      icon: <MessageSquarePlus className="w-4 h-4" />,
      onClick: () => onEnrichVariants?.(),
      disabled: !onEnrichVariants || totalVariants === 0 || nextAction === "enrich",
    },
    {
      id: "validate",
      label: "Validate Variants",
      icon: <ShieldCheck className="w-4 h-4" />,
      onClick: () => onValidateVariants?.(),
      disabled: !onValidateVariants || totalVariants === 0 || nextAction === "validate",
    },
  ];

  return (
    <div className="p-6 space-y-5">
      {/* Header: compact summary + smart CTA */}
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-2">
          <h3 className="font-semibold">Variants</h3>
          {/* Horizontal summary bar (replaces 4-card grid) */}
          <VariantsSummaryBar
            totalVariants={totalVariants}
            enrichedCount={data.enriched_variants_count}
            validatedCount={data.validated_variants_count}
            failedCount={data.failed_validation_variants_count}
            questionsWithVariants={questionsWithVariants}
            totalQuestions={validatedQuestions.length}
          />
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <VariantPrimaryCTA
            nextAction={nextAction}
            questionsNoVariants={questionsNoVariants}
            unenrichedVariants={unenrichedVariants}
            unvalidatedVariants={unvalidatedVariants}
            onGenerateVariants={onGenerateVariants}
            onEnrichVariants={onEnrichVariants}
            onValidateVariants={onValidateVariants}
          />
          <ActionsDropdown actions={secondaryActions} label="More" />
        </div>
      </div>

      {/* Step guidance banner */}
      <VariantStepGuidance
        nextAction={nextAction}
        unenrichedVariants={unenrichedVariants}
        unvalidatedVariants={unvalidatedVariants}
        onEnrichVariants={onEnrichVariants}
        onValidateVariants={onValidateVariants}
      />

      {/* Filter tabs */}
      <div className="flex gap-1 border-b border-border">
        {filters.map((f) => (
          <button
            key={f.id}
            onClick={() => setFilter(f.id)}
            className={cn(
              "px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors",
              filter === f.id
                ? "border-accent text-accent"
                : "border-transparent text-text-secondary hover:text-text-primary",
            )}
          >
            {f.label}
            <span
              className={cn(
                "ml-2 px-1.5 py-0.5 text-xs rounded",
                filter === f.id ? "bg-accent/20" : "bg-surface",
              )}
            >
              {f.count}
            </span>
          </button>
        ))}
      </div>

      {/* Questions table */}
      <div className="bg-surface border border-border rounded-lg overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-border text-left text-xs text-text-secondary uppercase tracking-wide">
              <th className="w-8 px-2" />
              <th className="px-4 py-3 font-medium">Q#</th>
              <th className="px-4 py-3 font-medium text-center">Original</th>
              <th className="px-4 py-3 font-medium text-center">Has Variants?</th>
              <th className="px-4 py-3 font-medium text-center">Count</th>
              <th className="px-4 py-3 font-medium text-center">Enriched</th>
              <th className="px-4 py-3 font-medium text-center">Validated</th>
              <th className="px-4 py-3 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredQuestions.map((q) => (
              <VariantQuestionRow
                key={q.id}
                subjectId={subjectId}
                testId={testId}
                question={q}
                isExpanded={expandedRows.has(q.question_number)}
                onToggle={() => toggleRow(q.question_number)}
                onAddVariants={onGenerateVariants}
                onDeleteVariants={
                  onDeleteVariants
                    ? () => onDeleteVariants(q.question_number)
                    : undefined
                }
              />
            ))}
          </tbody>
        </table>

        {filteredQuestions.length === 0 && (
          <div className="p-8 text-center text-text-secondary">
            {validatedQuestions.length === 0
              ? "No validated questions yet. Validate questions first to generate variants."
              : "No questions match the current filter"}
          </div>
        )}
      </div>

      {/* Additive-model footnote */}
      <p className="text-xs text-text-secondary">
        <strong>Note:</strong> Variant generation is additive — use "Add More"
        to generate additional variants on top of existing ones.
      </p>
    </div>
  );
}

// ─── Sub-components ───────────────────────────────────

/** Compact horizontal summary replacing the 4-card grid. */
function VariantsSummaryBar({
  totalVariants,
  enrichedCount,
  validatedCount,
  failedCount,
  questionsWithVariants,
  totalQuestions,
}: {
  totalVariants: number;
  enrichedCount: number;
  validatedCount: number;
  failedCount: number;
  questionsWithVariants: number;
  totalQuestions: number;
}) {
  return (
    <div className="flex flex-wrap items-center gap-x-5 gap-y-1 text-sm">
      <div>
        <span className="text-text-secondary">Variants:</span>{" "}
        <span className="font-medium">{totalVariants}</span>
      </div>
      <div>
        <span className="text-text-secondary">Enriched:</span>{" "}
        <ProgressRatio current={enrichedCount} total={totalVariants} />
      </div>
      <div>
        <span className="text-text-secondary">Validated:</span>{" "}
        <ProgressRatio current={validatedCount} total={enrichedCount} />
      </div>
      {failedCount > 0 && (
        <span className="text-error text-xs">{failedCount} failed</span>
      )}
      <div>
        <span className="text-text-secondary">Coverage:</span>{" "}
        <ProgressRatio current={questionsWithVariants} total={totalQuestions} />
      </div>
    </div>
  );
}

/** Smart primary CTA for the variants pipeline. */
function VariantPrimaryCTA({
  nextAction,
  questionsNoVariants,
  unenrichedVariants,
  unvalidatedVariants,
  onGenerateVariants,
  onEnrichVariants,
  onValidateVariants,
}: {
  nextAction: "generate" | "enrich" | "validate" | "done";
  questionsNoVariants: number;
  unenrichedVariants: number;
  unvalidatedVariants: number;
  onGenerateVariants: () => void;
  onEnrichVariants?: () => void;
  onValidateVariants?: () => void;
}) {
  switch (nextAction) {
    case "generate":
      return (
        <ActionButton
          variant="primary"
          icon={<Sparkles className="w-4 h-4" />}
          onClick={onGenerateVariants}
        >
          Generate for {questionsNoVariants} Missing
        </ActionButton>
      );
    case "enrich":
      return (
        <ActionButton
          variant="primary"
          icon={<MessageSquarePlus className="w-4 h-4" />}
          onClick={() => onEnrichVariants?.()}
          disabled={!onEnrichVariants}
        >
          Enrich {unenrichedVariants} Variants
        </ActionButton>
      );
    case "validate":
      return (
        <ActionButton
          variant="primary"
          icon={<ShieldCheck className="w-4 h-4" />}
          onClick={() => onValidateVariants?.()}
          disabled={!onValidateVariants}
        >
          Validate {unvalidatedVariants} Variants
        </ActionButton>
      );
    case "done":
      return (
        <ActionButton
          variant="secondary"
          disabled
          icon={<CheckCircle2 className="w-4 h-4 text-success" />}
        >
          All Complete
        </ActionButton>
      );
  }
}

/** Contextual guidance banner for variant steps. */
function VariantStepGuidance({
  nextAction,
  unenrichedVariants,
  unvalidatedVariants,
  onEnrichVariants,
  onValidateVariants,
}: {
  nextAction: "generate" | "enrich" | "validate" | "done";
  unenrichedVariants: number;
  unvalidatedVariants: number;
  onEnrichVariants?: () => void;
  onValidateVariants?: () => void;
}) {
  if (nextAction === "done") {
    return (
      <StepBanner
        variant="complete"
        message="All variants are generated, enriched, and validated."
      />
    );
  }
  if (nextAction === "enrich") {
    return (
      <StepBanner
        variant="action"
        message={`All questions have variants. ${unenrichedVariants} variants need enrichment.`}
        actionLabel={`Enrich ${unenrichedVariants}`}
        onAction={() => onEnrichVariants?.()}
      />
    );
  }
  if (nextAction === "validate") {
    return (
      <StepBanner
        variant="action"
        message={`Enrichment complete. ${unvalidatedVariants} variants need validation.`}
        actionLabel={`Validate ${unvalidatedVariants}`}
        onAction={() => onValidateVariants?.()}
      />
    );
  }
  return null;
}

// ─── Table Row ────────────────────────────────────────

interface VariantQuestionRowProps {
  subjectId: string;
  testId: string;
  question: QuestionBrief;
  isExpanded: boolean;
  onToggle: () => void;
  onAddVariants: () => void;
  onDeleteVariants?: () => void;
}

function VariantQuestionRow({
  subjectId,
  testId,
  question: q,
  isExpanded,
  onToggle,
  onAddVariants,
  onDeleteVariants,
}: VariantQuestionRowProps) {
  const hasVariants = q.variants_count > 0;

  return (
    <>
      <tr
        className={cn(
          "border-b border-border hover:bg-white/5 transition-colors cursor-pointer",
          isExpanded && "bg-white/5",
        )}
        onClick={onToggle}
      >
        <td className="w-8 px-2">
          {hasVariants && (
            <span className="inline-flex items-center justify-center w-5 h-5 rounded hover:bg-white/10">
              {isExpanded ? (
                <ChevronDown className="w-4 h-4 text-text-secondary" />
              ) : (
                <ChevronRight className="w-4 h-4 text-text-secondary" />
              )}
            </span>
          )}
        </td>
        <td className="px-4 py-3 font-mono text-sm">Q{q.question_number}</td>
        <td className="px-4 py-3 text-center">
          <CheckCircle2 className="w-4 h-4 text-success mx-auto" />
        </td>
        <td className="px-4 py-3 text-center">
          {hasVariants ? (
            <CheckCircle2 className="w-4 h-4 text-success mx-auto" />
          ) : (
            <Circle className="w-4 h-4 text-text-secondary mx-auto" />
          )}
        </td>
        <td className="px-4 py-3 text-center text-sm font-mono">
          {hasVariants ? (
            <span className="text-accent">{q.variants_count}</span>
          ) : (
            <span className="text-text-secondary">0</span>
          )}
        </td>
        <td className="px-4 py-3 text-center text-sm">
          <span className="text-text-secondary">—</span>
        </td>
        <td className="px-4 py-3 text-center text-sm">
          <span className="text-text-secondary">—</span>
        </td>
        <td className="px-4 py-3">
          <div className="flex gap-2">
            <button
              onClick={(e) => {
                e.stopPropagation();
                onAddVariants();
              }}
              className="flex items-center gap-1 px-2 py-1 text-xs text-accent hover:bg-accent/10 rounded"
            >
              <Plus className="w-3 h-3" />
              Add
            </button>
            {hasVariants && onDeleteVariants && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDeleteVariants();
                }}
                className="flex items-center gap-1 px-2 py-1 text-xs text-error hover:bg-error/10 rounded"
              >
                <Trash2 className="w-3 h-3" />
              </button>
            )}
          </div>
        </td>
      </tr>

      {isExpanded && hasVariants && (
        <tr className="bg-background/50">
          <td colSpan={8} className="p-0">
            <div className="p-4 border-b border-border">
              <VariantsExpandedContent
                subjectId={subjectId}
                testId={testId}
                questionNum={q.question_number}
                variantCount={q.variants_count}
              />
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
