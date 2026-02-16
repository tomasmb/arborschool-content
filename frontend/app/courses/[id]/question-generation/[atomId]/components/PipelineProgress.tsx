"use client";

import { CheckCircle2, Circle, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";
import type { PipelineReport } from "@/lib/api-types-question-gen";

// Phase groups matching the backend pipeline structure.
const PHASE_GROUPS = [
  { id: "enrich", label: "Enrich", phases: [0, 1], statKey: null },
  { id: "plan", label: "Plan", phases: [2, 3], statKey: null },
  {
    id: "generate", label: "Generate", phases: [4],
    statKey: "total_generated" as const,
  },
  {
    id: "validate", label: "Validate", phases: [5, 6],
    statKey: "total_passed_base_validation" as const,
  },
  {
    id: "feedback", label: "Feedback", phases: [7, 8],
    statKey: "total_passed_feedback" as const,
  },
  {
    id: "finalize", label: "Finalize", phases: [9, 10],
    statKey: "total_synced" as const,
  },
] as const;

type StatKey = (typeof PHASE_GROUPS)[number]["statKey"];

interface PipelineProgressProps {
  availablePhases: number[];
  report: PipelineReport | null;
}

export function PipelineProgress({
  availablePhases,
  report,
}: PipelineProgressProps) {
  const phaseSet = new Set(availablePhases);

  /** A group is "complete" if ALL its phases have checkpoints. */
  const isGroupComplete = (phases: readonly number[]) =>
    phases.every((p) => phaseSet.has(p));

  /** A group has "errors" if the report lists errors for it. */
  const groupHasErrors = (groupId: string) => {
    if (!report) return false;
    return report.phases.some(
      (p) => p.errors.length > 0 && p.name.toLowerCase().includes(groupId),
    );
  };

  const getStatValue = (key: StatKey): number | null => {
    if (!key || !report) return null;
    const val = report[key];
    return typeof val === "number" ? val : null;
  };

  return (
    <div className="bg-surface border border-border rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold">Pipeline Progress</h2>
        {report && (
          <StatusBadge success={report.success} />
        )}
      </div>

      {/* Stepper */}
      <div className="flex items-center gap-1">
        {PHASE_GROUPS.map((group, idx) => {
          const complete = isGroupComplete(group.phases);
          const hasErrors = groupHasErrors(group.id);
          const stat = getStatValue(group.statKey);

          return (
            <div key={group.id} className="flex items-center flex-1">
              <StepItem
                label={group.label}
                complete={complete}
                hasErrors={hasErrors}
                stat={stat}
              />
              {idx < PHASE_GROUPS.length - 1 && (
                <div
                  className={cn(
                    "h-px flex-1 mx-1",
                    complete ? "bg-success/40" : "bg-border",
                  )}
                />
              )}
            </div>
          );
        })}
      </div>

      {/* Stats row */}
      {report && <StatsRow report={report} />}
    </div>
  );
}


function StepItem({
  label,
  complete,
  hasErrors,
  stat,
}: {
  label: string;
  complete: boolean;
  hasErrors: boolean;
  stat: number | null;
}) {
  const Icon = hasErrors
    ? AlertTriangle
    : complete
      ? CheckCircle2
      : Circle;

  return (
    <div className="flex flex-col items-center gap-1 min-w-[60px]">
      <Icon
        className={cn(
          "w-5 h-5",
          hasErrors
            ? "text-warning"
            : complete
              ? "text-success"
              : "text-text-secondary/40",
        )}
      />
      <span
        className={cn(
          "text-[11px] font-medium",
          complete ? "text-text-primary" : "text-text-secondary",
        )}
      >
        {label}
      </span>
      {stat !== null && stat > 0 && (
        <span className="text-[10px] text-text-secondary">
          {stat}
        </span>
      )}
    </div>
  );
}


function StatusBadge({ success }: { success: boolean }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium",
        success
          ? "bg-success/10 text-success"
          : "bg-warning/10 text-warning",
      )}
    >
      {success ? (
        <><CheckCircle2 className="w-3 h-3" /> Complete</>
      ) : (
        <><AlertTriangle className="w-3 h-3" /> In Progress</>
      )}
    </span>
  );
}


function StatsRow({ report }: { report: PipelineReport }) {
  const stats = [
    { label: "Planned", value: report.total_planned },
    { label: "Generated", value: report.total_generated },
    { label: "Passed Dedupe", value: report.total_passed_dedupe },
    { label: "Validated", value: report.total_passed_base_validation },
    { label: "Feedback", value: report.total_passed_feedback },
    { label: "Final", value: report.total_final },
    { label: "Synced", value: report.total_synced },
  ].filter((s) => s.value > 0);

  if (stats.length === 0) return null;

  return (
    <div className="flex gap-4 mt-3 pt-3 border-t border-border">
      {stats.map((s) => (
        <div key={s.label} className="text-center">
          <div className="text-sm font-semibold">{s.value}</div>
          <div className="text-[10px] text-text-secondary">{s.label}</div>
        </div>
      ))}
    </div>
  );
}
