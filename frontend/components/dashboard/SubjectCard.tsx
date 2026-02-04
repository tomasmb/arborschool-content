"use client";

import Link from "next/link";
import { ArrowRight, CheckCircle2, Circle, AlertCircle } from "lucide-react";
import { type SubjectBrief } from "@/lib/api";
import { cn } from "@/lib/utils";
import { ProgressBar } from "@/components/ui/ProgressBar";

interface SubjectCardProps {
  subject: SubjectBrief;
}

/**
 * Compute overall progress for a subject based on pipeline stages.
 * Knowledge pipeline: temario (10%) + standards (20%) + atoms (20%) = 50%
 * Questions pipeline: tagging (25%) + enrichment/validation (25%) = 50%
 */
function computeSubjectProgress(stats: SubjectBrief["stats"]): {
  percent: number;
  needsAttention: boolean;
  nextAction: string | null;
} {
  let progress = 0;

  // Knowledge pipeline (50% total)
  if (stats.temario_exists) progress += 10;
  if (stats.standards_count > 0) progress += 20;
  if (stats.atoms_count > 0) progress += 20;

  // Questions pipeline (50% total) - based on tagging completion
  // Tagging represents about half of the question work
  progress += Math.round(stats.tagging_completion * 50);

  // Determine next action
  let nextAction: string | null = null;
  if (!stats.temario_exists) {
    nextAction = "Upload temario";
  } else if (stats.standards_count === 0) {
    nextAction = "Generate standards";
  } else if (stats.atoms_count === 0) {
    nextAction = "Generate atoms";
  } else if (stats.tests_count === 0) {
    nextAction = "Upload test PDFs";
  } else if (stats.tagging_completion < 1) {
    nextAction = "Tag questions";
  }

  // Needs attention if there's incomplete work
  const needsAttention = progress < 100 && nextAction !== null;

  return { percent: progress, needsAttention, nextAction };
}

export function SubjectCard({ subject }: SubjectCardProps) {
  const { stats } = subject;
  const { percent, needsAttention, nextAction } = computeSubjectProgress(stats);

  const StatusIcon = ({ done }: { done: boolean }) =>
    done ? (
      <CheckCircle2 className="w-3.5 h-3.5 text-success" />
    ) : (
      <Circle className="w-3.5 h-3.5 text-text-secondary" />
    );

  return (
    <div className="bg-surface border border-border rounded-lg p-5 hover:border-accent/50 transition-colors">
      {/* Header with badge */}
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-semibold text-lg">{subject.name}</h3>
          <p className="text-text-secondary text-sm">{subject.year}</p>
        </div>
        {needsAttention && (
          <span className="flex items-center gap-1 px-2 py-0.5 bg-warning/10 text-warning text-xs rounded-full">
            <AlertCircle className="w-3 h-3" />
            Action needed
          </span>
        )}
        {percent === 100 && (
          <span className="flex items-center gap-1 px-2 py-0.5 bg-success/10 text-success text-xs rounded-full">
            <CheckCircle2 className="w-3 h-3" />
            Complete
          </span>
        )}
      </div>

      {/* Progress bar */}
      <ProgressBar
        current={percent}
        total={100}
        showPercent
        size="sm"
        className="mb-3"
      />

      {/* Next action hint */}
      {nextAction && (
        <p className="text-xs text-accent mb-3">
          Next: {nextAction}
        </p>
      )}

      {/* Pipeline status - compact */}
      <div className="flex items-center gap-3 text-xs mb-3">
        <div className="flex items-center gap-1">
          <StatusIcon done={stats.temario_exists} />
          <span className="text-text-secondary">Temario</span>
        </div>
        <div className="flex items-center gap-1">
          <StatusIcon done={stats.standards_count > 0} />
          <span className="text-text-secondary">{stats.standards_count} Std</span>
        </div>
        <div className="flex items-center gap-1">
          <StatusIcon done={stats.atoms_count > 0} />
          <span className="text-text-secondary">{stats.atoms_count} Atoms</span>
        </div>
      </div>

      {/* Stats row */}
      <div className="flex items-center justify-between text-xs text-text-secondary mb-4">
        <span>{stats.tests_count} tests</span>
        <span>{stats.questions_count} questions</span>
        <span>{stats.variants_count} variants</span>
      </div>

      {/* Action */}
      <Link
        href={`/courses/${subject.id}`}
        className={cn(
          "flex items-center justify-center gap-2 w-full py-2 px-4",
          "bg-accent/10 text-accent rounded-lg text-sm font-medium",
          "hover:bg-accent/20 transition-colors"
        )}
      >
        {needsAttention ? "Continue" : "View"}
        <ArrowRight className="w-4 h-4" />
      </Link>
    </div>
  );
}
