"use client";

import { useState, useCallback } from "react";
import {
  CheckCircle2,
  Circle,
  XCircle,
  MessageSquarePlus,
  ShieldCheck,
  ChevronDown,
  ChevronRight,
  Tag,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { StatusBadge, StatusIcon, ProgressRatio } from "@/components/ui";
import { QTIFullView } from "@/components/qti";
import type { QuestionBrief, TestDetail } from "@/lib/api";

export interface QuestionsTabProps {
  subjectId: string;
  testId: string;
  questions: QuestionBrief[];
  data: TestDetail;
  onOpenEnrichment: () => void;
  onOpenValidation: () => void;
  onRunTagging: () => void;
  onSelectQuestion: (questionNum: number) => void;
}

type QuestionsFilter = "all" | "not_tagged" | "not_enriched" | "enriched" | "not_validated" | "validated";

export function QuestionsTab({
  subjectId,
  testId,
  questions,
  data,
  onOpenEnrichment,
  onOpenValidation,
  onRunTagging,
  onSelectQuestion,
}: QuestionsTabProps) {
  const [filter, setFilter] = useState<QuestionsFilter>("all");
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set());

  // Calculate counts - only count finalized questions
  const finalizedQuestions = questions.filter((q) => q.is_finalized);
  const taggedCount = questions.filter((q) => q.is_tagged).length;
  const enrichedCount = questions.filter((q) => q.is_enriched).length;
  const validatedCount = questions.filter((q) => q.is_validated).length;
  const notTaggedCount = finalizedQuestions.length - taggedCount;
  const notEnrichedCount = taggedCount - enrichedCount;
  const notValidatedCount = enrichedCount - validatedCount;

  // Filter questions - show all finalized questions, not just tagged
  const filteredQuestions = finalizedQuestions.filter((q) => {
    switch (filter) {
      case "not_tagged":
        return !q.is_tagged;
      case "not_enriched":
        return q.is_tagged && !q.is_enriched;
      case "enriched":
        return q.is_enriched;
      case "not_validated":
        return q.is_enriched && !q.is_validated;
      case "validated":
        return q.is_validated;
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

  const filters: { id: QuestionsFilter; label: string; count: number }[] = [
    { id: "all", label: "All", count: finalizedQuestions.length },
    { id: "not_tagged", label: "Not Tagged", count: notTaggedCount },
    { id: "not_enriched", label: "Not Enriched", count: notEnrichedCount },
    { id: "enriched", label: "Enriched", count: enrichedCount },
    { id: "not_validated", label: "Needs Validation", count: notValidatedCount },
    { id: "validated", label: "Validated", count: validatedCount },
  ];

  return (
    <div className="p-6 space-y-6">
      {/* Header with stats and actions */}
      <div className="flex items-start justify-between">
        <div className="space-y-2">
          <h3 className="font-semibold">Questions Pipeline</h3>
          <div className="flex gap-4 text-sm">
            <div>
              <span className="text-text-secondary">Tagged:</span>{" "}
              <ProgressRatio current={taggedCount} total={finalizedQuestions.length} />
            </div>
            <div>
              <span className="text-text-secondary">Enriched:</span>{" "}
              <ProgressRatio current={enrichedCount} total={taggedCount} />
            </div>
            <div>
              <span className="text-text-secondary">Validated:</span>{" "}
              <ProgressRatio current={validatedCount} total={enrichedCount} />
            </div>
          </div>
        </div>

        <div className="flex gap-2">
          {/* Tagging action */}
          <button
            onClick={onRunTagging}
            disabled={notTaggedCount === 0 && taggedCount === 0}
            className="flex items-center gap-2 px-3 py-2 bg-purple-500/10 text-purple-400 rounded-lg text-sm font-medium hover:bg-purple-500/20 border border-purple-500/20 disabled:opacity-50"
          >
            <Tag className="w-4 h-4" />
            {notTaggedCount > 0 ? `Tag ${notTaggedCount} Questions` : "Re-tag All"}
          </button>

          {/* Enrichment action */}
          <button
            onClick={onOpenEnrichment}
            disabled={taggedCount === 0}
            className="flex items-center gap-2 px-3 py-2 bg-green-500/10 text-green-400 rounded-lg text-sm font-medium hover:bg-green-500/20 border border-green-500/20 disabled:opacity-50"
          >
            <MessageSquarePlus className="w-4 h-4" />
            {notEnrichedCount > 0 ? `Enrich ${notEnrichedCount} Missing` : "Re-enrich"}
          </button>

          {/* Validation action */}
          <button
            onClick={onOpenValidation}
            disabled={enrichedCount === 0}
            className="flex items-center gap-2 px-3 py-2 bg-blue-500/10 text-blue-400 rounded-lg text-sm font-medium hover:bg-blue-500/20 border border-blue-500/20 disabled:opacity-50"
          >
            <ShieldCheck className="w-4 h-4" />
            {notValidatedCount > 0 ? `Validate ${notValidatedCount} Missing` : "Re-validate"}
          </button>
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
              <th className="px-4 py-3 font-medium text-center">Tagged</th>
              <th className="px-4 py-3 font-medium text-center">Enriched</th>
              <th className="px-4 py-3 font-medium text-center">Validated</th>
              <th className="px-4 py-3 font-medium text-center">Atoms</th>
              <th className="px-4 py-3 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredQuestions.map((q) => {
              const isExpanded = expandedRows.has(q.question_number);
              return (
                <QuestionRow
                  key={q.id}
                  question={q}
                  isExpanded={isExpanded}
                  onToggle={() => toggleRow(q.question_number)}
                  onViewDetail={() => onSelectQuestion(q.question_number)}
                />
              );
            })}
          </tbody>
        </table>

        {filteredQuestions.length === 0 && (
          <div className="p-8 text-center text-text-secondary">
            No questions match the current filter
          </div>
        )}
      </div>
    </div>
  );
}

interface QuestionRowProps {
  question: QuestionBrief;
  isExpanded: boolean;
  onToggle: () => void;
  onViewDetail: () => void;
}

function QuestionRow({ question: q, isExpanded, onToggle, onViewDetail }: QuestionRowProps) {
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
          <span className="inline-flex items-center justify-center w-5 h-5 rounded hover:bg-white/10">
            {isExpanded ? (
              <ChevronDown className="w-4 h-4 text-text-secondary" />
            ) : (
              <ChevronRight className="w-4 h-4 text-text-secondary" />
            )}
          </span>
        </td>
        <td className="px-4 py-3 font-mono text-sm">Q{q.question_number}</td>
        <td className="px-4 py-3 text-center">
          {q.is_tagged ? (
            <CheckCircle2 className="w-4 h-4 text-success mx-auto" />
          ) : (
            <Circle className="w-4 h-4 text-text-secondary mx-auto" />
          )}
        </td>
        <td className="px-4 py-3 text-center">
          {!q.is_tagged ? (
            <span className="text-text-secondary text-sm">—</span>
          ) : q.is_enriched ? (
            <CheckCircle2 className="w-4 h-4 text-success mx-auto" />
          ) : (
            <Circle className="w-4 h-4 text-text-secondary mx-auto" />
          )}
        </td>
        <td className="px-4 py-3 text-center">
          {!q.is_enriched ? (
            <span className="text-text-secondary text-sm">—</span>
          ) : q.is_validated ? (
            <CheckCircle2 className="w-4 h-4 text-success mx-auto" />
          ) : (
            <Circle className="w-4 h-4 text-text-secondary mx-auto" />
          )}
        </td>
        <td className="px-4 py-3 text-center text-sm">
          {q.atoms_count > 0 ? (
            <span className="text-accent">{q.atoms_count}</span>
          ) : (
            <span className="text-text-secondary">—</span>
          )}
        </td>
        <td className="px-4 py-3">
          <button
            onClick={(e) => {
              e.stopPropagation();
              onViewDetail();
            }}
            className="text-sm text-accent hover:underline"
          >
            View Details
          </button>
        </td>
      </tr>

      {/* Expanded content */}
      {isExpanded && (
        <tr className="bg-background/50">
          <td colSpan={7} className="p-0">
            <div className="p-4 border-b border-border">
              <QuestionExpandedContent questionNum={q.question_number} question={q} />
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

function QuestionExpandedContent({
  questionNum,
  question,
}: {
  questionNum: number;
  question: QuestionBrief;
}) {
  return (
    <div className="grid grid-cols-2 gap-4">
      {/* Left: Question preview */}
      <div>
        <h4 className="text-sm font-medium text-text-secondary mb-2">Question Preview</h4>
        <div className="bg-surface border border-border rounded-lg p-4 text-sm text-text-secondary">
          Question content would be loaded here...
          <br />
          (Click "View Details" to see full question)
        </div>
      </div>

      {/* Right: Status and feedback */}
      <div className="space-y-4">
        <div>
          <h4 className="text-sm font-medium text-text-secondary mb-2">Pipeline Status</h4>
          <div className="flex flex-wrap gap-2">
            <StatusBadge status={question.is_tagged ? "complete" : "not_started"} label="Tagged" size="sm" />
            <StatusBadge
              status={question.is_enriched ? "complete" : question.is_tagged ? "not_started" : "blocked"}
              label="Enriched"
              size="sm"
            />
            <StatusBadge
              status={
                question.is_validated
                  ? "complete"
                  : question.is_enriched
                    ? "not_started"
                    : "blocked"
              }
              label="Validated"
              size="sm"
            />
          </div>
        </div>

        {question.is_enriched && (
          <div>
            <h4 className="text-sm font-medium text-text-secondary mb-2">Feedback Preview</h4>
            <div className="bg-surface border border-border rounded-lg p-3 text-sm text-text-secondary">
              Feedback content would be shown here...
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
