"use client";

import { useState, useCallback } from "react";
import {
  Plus,
  Trash2,
  ChevronDown,
  ChevronRight,
  Sparkles,
  Info,
  MessageSquarePlus,
  ShieldCheck,
  CheckCircle2,
  Circle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { ProgressRatio } from "@/components/ui";
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

type VariantsFilter = "all" | "has_variants" | "no_variants" | "all_validated" | "needs_work";

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

  // Calculate counts
  const questionsWithVariants = validatedQuestions.filter((q) => q.variants_count > 0).length;
  const questionsNoVariants = validatedQuestions.filter((q) => q.variants_count === 0).length;
  const totalVariants = data.variants_count;

  // Filter questions
  const filteredQuestions = validatedQuestions.filter((q) => {
    switch (filter) {
      case "has_variants":
        return q.variants_count > 0;
      case "no_variants":
        return q.variants_count === 0;
      case "all_validated":
        // Would need variant-level validation data
        return q.variants_count > 0;
      case "needs_work":
        return q.variants_count === 0;
      default:
        return true;
    }
  });

  const toggleRow = useCallback((questionNum: number) => {
    setExpandedRows((prev) => {
      const next = new Set(prev);
      if (next.has(questionNum)) {
        next.delete(questionNum);
      } else {
        next.add(questionNum);
      }
      return next;
    });
  }, []);

  const filters: { id: VariantsFilter; label: string; count: number }[] = [
    { id: "all", label: "All", count: validatedQuestions.length },
    { id: "has_variants", label: "Has Variants", count: questionsWithVariants },
    { id: "no_variants", label: "No Variants", count: questionsNoVariants },
  ];

  return (
    <div className="p-6 space-y-6">
      {/* Header with stats */}
      <div className="flex items-start justify-between">
        <div className="space-y-3">
          <h3 className="font-semibold">Variants</h3>

          {/* Key metrics */}
          <div className="grid grid-cols-4 gap-4 text-sm">
            <div className="bg-surface border border-border rounded-lg p-3">
              <p className="text-text-secondary text-xs mb-1">Total Variants</p>
              <p className="text-xl font-semibold">{totalVariants}</p>
              <p className="text-xs text-text-secondary mt-1">
                Avg {validatedQuestions.length > 0 ? (totalVariants / validatedQuestions.length).toFixed(1) : 0}/q
              </p>
            </div>
            <div className="bg-surface border border-border rounded-lg p-3">
              <p className="text-text-secondary text-xs mb-1">Enriched</p>
              <p className="text-xl font-semibold">
                <ProgressRatio current={data.enriched_variants_count} total={totalVariants} />
              </p>
              {totalVariants > 0 && data.enriched_variants_count < totalVariants && (
                <p className="text-xs text-warning mt-1">
                  {totalVariants - data.enriched_variants_count} need feedback
                </p>
              )}
            </div>
            <div className="bg-surface border border-border rounded-lg p-3">
              <p className="text-text-secondary text-xs mb-1">Validated</p>
              <p className="text-xl font-semibold">
                <ProgressRatio current={data.validated_variants_count} total={data.enriched_variants_count} />
              </p>
              {data.failed_validation_variants_count > 0 && (
                <p className="text-xs text-error mt-1">
                  {data.failed_validation_variants_count} failed
                </p>
              )}
            </div>
            <div className="bg-surface border border-border rounded-lg p-3">
              <p className="text-text-secondary text-xs mb-1">Questions w/ Variants</p>
              <p className="text-xl font-semibold">
                <ProgressRatio current={questionsWithVariants} total={validatedQuestions.length} />
              </p>
              {questionsNoVariants > 0 && (
                <p className="text-xs text-warning mt-1">{questionsNoVariants} need variants</p>
              )}
            </div>
          </div>
        </div>

        <div className="flex gap-2 flex-wrap items-center">
          {/* Generate variants */}
          {questionsNoVariants > 0 && (
            <button
              onClick={onGenerateVariants}
              className="flex items-center gap-2 px-3 py-2 bg-accent text-white rounded-lg text-sm font-medium hover:bg-accent/90"
            >
              <Sparkles className="w-4 h-4" />
              Generate for {questionsNoVariants} Missing
            </button>
          )}
          <button
            onClick={onGenerateVariants}
            className="flex items-center gap-2 px-3 py-2 bg-yellow-500/10 text-yellow-400
              rounded-lg text-sm font-medium hover:bg-yellow-500/20 border
              border-yellow-500/20"
          >
            <Plus className="w-4 h-4" />
            Add More Variants
          </button>

          {/* Enrich variants (for old variants without feedback) */}
          {onEnrichVariants && totalVariants > 0 && (
            <button
              onClick={onEnrichVariants}
              className="flex items-center gap-2 px-3 py-2 bg-green-500/10 text-green-400
                rounded-lg text-sm font-medium hover:bg-green-500/20 border
                border-green-500/20"
            >
              <MessageSquarePlus className="w-4 h-4" />
              Enrich Variants
            </button>
          )}

          {/* Validate variants */}
          {onValidateVariants && totalVariants > 0 && (
            <button
              onClick={onValidateVariants}
              className="flex items-center gap-2 px-3 py-2 bg-blue-500/10 text-blue-400
                rounded-lg text-sm font-medium hover:bg-blue-500/20 border
                border-blue-500/20"
            >
              <ShieldCheck className="w-4 h-4" />
              Validate Variants
            </button>
          )}

          {/* Info about variant generation */}
          <div className="flex items-center gap-1.5 text-xs text-text-secondary ml-2">
            <Info className="w-3.5 h-3.5" />
            <span>New variants include feedback; old ones may need enrichment</span>
          </div>
        </div>
      </div>

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
                : "border-transparent text-text-secondary hover:text-text-primary"
            )}
          >
            {f.label}
            <span
              className={cn(
                "ml-2 px-1.5 py-0.5 text-xs rounded",
                filter === f.id ? "bg-accent/20" : "bg-surface"
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
              <th className="w-8 px-2"></th>
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
            {filteredQuestions.map((q) => {
              const isExpanded = expandedRows.has(q.question_number);
              const hasVariants = q.variants_count > 0;

              return (
                <VariantQuestionRow
                  key={q.id}
                  subjectId={subjectId}
                  testId={testId}
                  question={q}
                  isExpanded={isExpanded}
                  onToggle={() => toggleRow(q.question_number)}
                  onAddVariants={onGenerateVariants}
                  onDeleteVariants={onDeleteVariants ? () => onDeleteVariants(q.question_number) : undefined}
                />
              );
            })}
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

      {/* Info about additive model */}
      <div className="text-xs text-text-secondary bg-surface/50 border border-border rounded-lg p-3">
        <strong>Note:</strong> Variant generation is additive. Use "Add More" to generate additional
        variants on top of existing ones. Use "Delete" to remove variants if needed.
      </div>
    </div>
  );
}

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
          isExpanded && "bg-white/5"
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
          {hasVariants ? <span className="text-accent">{q.variants_count}</span> : <span className="text-text-secondary">0</span>}
        </td>
        <td className="px-4 py-3 text-center text-sm">
          {hasVariants ? <span className="text-text-secondary">—/—</span> : <span className="text-text-secondary">—</span>}
        </td>
        <td className="px-4 py-3 text-center text-sm">
          {hasVariants ? <span className="text-text-secondary">—/—</span> : <span className="text-text-secondary">—</span>}
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

      {/* Expanded content showing individual variants */}
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

