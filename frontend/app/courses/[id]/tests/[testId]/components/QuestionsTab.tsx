"use client";

import { useState, useCallback } from "react";
import { CheckCircle2, Circle, Tag, MessageSquarePlus, ShieldCheck, RefreshCw, ChevronDown, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { ProgressRatio, ActionButton, ActionsDropdown, StepBanner } from "@/components/ui";
import { type QuestionBrief, type TestDetail } from "@/lib/api";
import { QuestionsExpandedContent } from "./QuestionsExpandedContent";

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

type QuestionsFilter =
  | "all"
  | "not_tagged"
  | "not_enriched"
  | "enriched"
  | "not_validated"
  | "validated";

// ─── Helpers ──────────────────────────────────────────

/** Determine which pipeline phase is the current "next action". */
function getNextAction(counts: {
  notTagged: number;
  notEnriched: number;
  notValidated: number;
  tagged: number;
  enriched: number;
}): "tag" | "enrich" | "validate" | "done" {
  if (counts.notTagged > 0) return "tag";
  if (counts.notEnriched > 0) return "enrich";
  if (counts.notValidated > 0) return "validate";
  return "done";
}

// ─── Main Component ───────────────────────────────────

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

  // Counts
  const finalizedQuestions = questions.filter((q) => q.is_finalized);
  const taggedCount = questions.filter((q) => q.is_tagged).length;
  const enrichedCount = questions.filter((q) => q.is_enriched).length;
  const validatedCount = questions.filter((q) => q.is_validated).length;
  const notTaggedCount = finalizedQuestions.length - taggedCount;
  const notEnrichedCount = taggedCount - enrichedCount;
  const notValidatedCount = enrichedCount - validatedCount;

  const nextAction = getNextAction({
    notTagged: notTaggedCount,
    notEnriched: notEnrichedCount,
    notValidated: notValidatedCount,
    tagged: taggedCount,
    enriched: enrichedCount,
  });

  // Filter
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
      if (next.has(questionNum)) next.delete(questionNum);
      else next.add(questionNum);
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

  // Build secondary actions for the dropdown
  const secondaryActions = buildSecondaryActions({
    nextAction,
    taggedCount,
    enrichedCount,
    onRunTagging,
    onOpenEnrichment,
    onOpenValidation,
  });

  return (
    <div className="p-6 space-y-5">
      {/* Header: progress + smart CTA */}
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-2">
          <h3 className="font-semibold">Questions Pipeline</h3>
          <div className="flex gap-4 text-sm">
            <ProgressStat label="Tagged" current={taggedCount} total={finalizedQuestions.length} />
            <ProgressStat label="Enriched" current={enrichedCount} total={taggedCount} />
            <ProgressStat label="Validated" current={validatedCount} total={enrichedCount} />
          </div>
        </div>

        {/* Primary CTA + overflow menu */}
        <div className="flex items-center gap-2 shrink-0">
          <PrimaryCTA
            nextAction={nextAction}
            notTaggedCount={notTaggedCount}
            notEnrichedCount={notEnrichedCount}
            notValidatedCount={notValidatedCount}
            onRunTagging={onRunTagging}
            onOpenEnrichment={onOpenEnrichment}
            onOpenValidation={onOpenValidation}
          />
          <ActionsDropdown actions={secondaryActions} label="More" />
        </div>
      </div>

      {/* Next-step guidance banner */}
      <StepGuidance
        nextAction={nextAction}
        notEnrichedCount={notEnrichedCount}
        notValidatedCount={notValidatedCount}
        onOpenEnrichment={onOpenEnrichment}
        onOpenValidation={onOpenValidation}
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
              <th className="px-4 py-3 font-medium text-center">Tagged</th>
              <th className="px-4 py-3 font-medium text-center">Enriched</th>
              <th className="px-4 py-3 font-medium text-center">Validated</th>
              <th className="px-4 py-3 font-medium text-center">Atoms</th>
              <th className="px-4 py-3 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredQuestions.map((q) => (
              <QuestionRow
                key={q.id}
                subjectId={subjectId}
                testId={testId}
                question={q}
                isExpanded={expandedRows.has(q.question_number)}
                onToggle={() => toggleRow(q.question_number)}
                onViewDetail={() => onSelectQuestion(q.question_number)}
              />
            ))}
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

// ─── Sub-components ───────────────────────────────────

/** Inline progress stat used in the header. */
function ProgressStat({
  label,
  current,
  total,
}: {
  label: string;
  current: number;
  total: number;
}) {
  return (
    <div>
      <span className="text-text-secondary">{label}:</span>{" "}
      <ProgressRatio current={current} total={total} />
    </div>
  );
}

/** Single prominent CTA that changes based on pipeline state. */
function PrimaryCTA({
  nextAction,
  notTaggedCount,
  notEnrichedCount,
  notValidatedCount,
  onRunTagging,
  onOpenEnrichment,
  onOpenValidation,
}: {
  nextAction: "tag" | "enrich" | "validate" | "done";
  notTaggedCount: number;
  notEnrichedCount: number;
  notValidatedCount: number;
  onRunTagging: () => void;
  onOpenEnrichment: () => void;
  onOpenValidation: () => void;
}) {
  switch (nextAction) {
    case "tag":
      return (
        <ActionButton
          variant="primary"
          icon={<Tag className="w-4 h-4" />}
          onClick={onRunTagging}
        >
          Tag {notTaggedCount} Questions
        </ActionButton>
      );
    case "enrich":
      return (
        <ActionButton
          variant="primary"
          icon={<MessageSquarePlus className="w-4 h-4" />}
          onClick={onOpenEnrichment}
        >
          Enrich {notEnrichedCount} Questions
        </ActionButton>
      );
    case "validate":
      return (
        <ActionButton
          variant="primary"
          icon={<ShieldCheck className="w-4 h-4" />}
          onClick={onOpenValidation}
        >
          Validate {notValidatedCount} Questions
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

/** Build the dropdown actions list based on current state. */
function buildSecondaryActions({
  nextAction,
  taggedCount,
  enrichedCount,
  onRunTagging,
  onOpenEnrichment,
  onOpenValidation,
}: {
  nextAction: "tag" | "enrich" | "validate" | "done";
  taggedCount: number;
  enrichedCount: number;
  onRunTagging: () => void;
  onOpenEnrichment: () => void;
  onOpenValidation: () => void;
}) {
  return [
    {
      id: "retag",
      label: "Re-tag All Questions",
      icon: <RefreshCw className="w-4 h-4" />,
      onClick: onRunTagging,
      disabled: taggedCount === 0,
    },
    {
      id: "reenrich",
      label: "Re-enrich All Questions",
      icon: <RefreshCw className="w-4 h-4" />,
      onClick: onOpenEnrichment,
      // Hide when enrich is the primary action (avoid duplication)
      disabled: nextAction === "enrich" || taggedCount === 0,
    },
    {
      id: "revalidate",
      label: "Re-validate All Questions",
      icon: <RefreshCw className="w-4 h-4" />,
      onClick: onOpenValidation,
      disabled: nextAction === "validate" || enrichedCount === 0,
    },
  ];
}

/** Contextual banner guiding the user to the next step. */
function StepGuidance({
  nextAction,
  notEnrichedCount,
  notValidatedCount,
  onOpenEnrichment,
  onOpenValidation,
}: {
  nextAction: "tag" | "enrich" | "validate" | "done";
  notEnrichedCount: number;
  notValidatedCount: number;
  onOpenEnrichment: () => void;
  onOpenValidation: () => void;
}) {
  if (nextAction === "done") {
    return (
      <StepBanner
        variant="complete"
        message="All questions are tagged, enriched, and validated."
      />
    );
  }
  // Show a nudge only when the primary CTA is for an earlier step but
  // a later step also has pending work (e.g. tagged done, enrich pending).
  if (nextAction === "enrich") {
    return (
      <StepBanner
        variant="action"
        message={`Tagging complete. ${notEnrichedCount} questions need enrichment.`}
        actionLabel={`Enrich ${notEnrichedCount}`}
        onAction={onOpenEnrichment}
      />
    );
  }
  if (nextAction === "validate") {
    return (
      <StepBanner
        variant="action"
        message={`Enrichment complete. ${notValidatedCount} questions need validation.`}
        actionLabel={`Validate ${notValidatedCount}`}
        onAction={onOpenValidation}
      />
    );
  }
  // "tag" state — no banner needed, the primary CTA is enough
  return null;
}

// ─── Table Row ────────────────────────────────────────

interface QuestionRowProps {
  subjectId: string;
  testId: string;
  question: QuestionBrief;
  isExpanded: boolean;
  onToggle: () => void;
  onViewDetail: () => void;
}

function QuestionRow({
  subjectId,
  testId,
  question: q,
  isExpanded,
  onToggle,
  onViewDetail,
}: QuestionRowProps) {
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
          <span className="inline-flex items-center justify-center w-5 h-5 rounded hover:bg-white/10">
            {isExpanded ? (
              <ChevronDown className="w-4 h-4 text-text-secondary" />
            ) : (
              <ChevronRight className="w-4 h-4 text-text-secondary" />
            )}
          </span>
        </td>
        <td className="px-4 py-3 font-mono text-sm">Q{q.question_number}</td>
        <StatusCell done={q.is_tagged} blocked={false} />
        <StatusCell done={q.is_enriched} blocked={!q.is_tagged} />
        <StatusCell done={q.is_validated} blocked={!q.is_enriched} />
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

      {isExpanded && (
        <tr className="bg-background/50">
          <td colSpan={7} className="p-0">
            <div className="p-4 border-b border-border">
              <QuestionsExpandedContent
                subjectId={subjectId}
                testId={testId}
                questionNum={q.question_number}
                question={q}
              />
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

/** Reusable cell for tagged / enriched / validated columns. */
function StatusCell({ done, blocked }: { done: boolean; blocked: boolean }) {
  return (
    <td className="px-4 py-3 text-center">
      {blocked ? (
        <span className="text-text-secondary text-sm">—</span>
      ) : done ? (
        <CheckCircle2 className="w-4 h-4 text-success mx-auto" />
      ) : (
        <Circle className="w-4 h-4 text-text-secondary mx-auto" />
      )}
    </td>
  );
}
