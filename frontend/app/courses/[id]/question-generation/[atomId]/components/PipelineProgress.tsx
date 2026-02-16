"use client";

import { useState } from "react";
import {
  CheckCircle2,
  Circle,
  AlertTriangle,
  XCircle,
  Clock,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type {
  PipelineReport,
  PhaseReport,
} from "@/lib/api-types-question-gen";

// Phase groups matching the actual checkpoint file numbers.
// Each group is "complete" when ALL listed phases have a checkpoint.
// Only list phases that actually produce checkpoint files.
const PHASE_GROUPS = [
  { id: "enrich", label: "Enrich", phases: [1], statKey: null },
  { id: "plan", label: "Plan", phases: [3], statKey: null },
  {
    id: "generate", label: "Generate", phases: [4],
    statKey: "total_generated" as const,
  },
  {
    id: "validate", label: "Validate", phases: [6],
    statKey: "total_passed_base_validation" as const,
  },
  {
    id: "feedback", label: "Feedback", phases: [8],
    statKey: "total_passed_feedback" as const,
  },
  {
    id: "finalize", label: "Finalize", phases: [10],
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
  const [expandedGroup, setExpandedGroup] = useState<string | null>(
    null,
  );
  const phaseSet = new Set(availablePhases);

  const isComplete = (phases: readonly number[]) =>
    phases.every((p) => phaseSet.has(p));

  const isPartial = (phases: readonly number[]) =>
    phases.some((p) => phaseSet.has(p)) && !isComplete(phases);

  const getErrors = (gid: string): PhaseReport[] => {
    if (!report) return [];
    return report.phases.filter(
      (p) =>
        p.errors.length > 0 &&
        p.name.toLowerCase().includes(gid),
    );
  };

  const getStatValue = (key: StatKey): number | null => {
    if (!key || !report) return null;
    const val = report[key];
    return typeof val === "number" ? val : null;
  };

  const toggle = (id: string) =>
    setExpandedGroup(expandedGroup === id ? null : id);

  return (
    <div className="bg-surface border border-border rounded-lg">
      {/* Header */}
      <div
        className={cn(
          "px-4 py-3 flex items-center justify-between",
          "border-b border-border",
        )}
      >
        <h2 className="text-sm font-semibold">Pipeline Progress</h2>
        {report && <OverallBadge success={report.success} />}
      </div>

      {/* Stepper row */}
      <div className="px-4 py-5">
        <div className="flex items-start">
          {PHASE_GROUPS.map((group, idx) => {
            const done = isComplete(group.phases);
            const partial = isPartial(group.phases);
            const errors = getErrors(group.id);
            const stat = getStatValue(group.statKey);
            const hasDetail = errors.length > 0;

            return (
              <div
                key={group.id}
                className="flex items-start flex-1"
              >
                {/* Step column */}
                <div className="flex flex-col items-center">
                  <button
                    onClick={() => hasDetail && toggle(group.id)}
                    className={cn(
                      "flex flex-col items-center gap-1.5",
                      hasDetail && "cursor-pointer group",
                    )}
                    disabled={!hasDetail}
                  >
                    <StepIcon
                      complete={done}
                      partial={partial}
                      hasErrors={errors.length > 0}
                    />
                    <span
                      className={cn(
                        "text-[11px] font-medium leading-tight",
                        done
                          ? "text-text-primary"
                          : "text-text-secondary",
                      )}
                    >
                      {group.label}
                    </span>
                    {stat !== null && stat > 0 && (
                      <span className="text-[10px] text-accent font-medium">
                        {stat}
                      </span>
                    )}
                    {hasDetail && (
                      <span className="text-[9px] text-warning/70">
                        {errors.flatMap((e) => e.errors).length} errors
                      </span>
                    )}
                  </button>
                </div>

                {/* Connector */}
                {idx < PHASE_GROUPS.length - 1 && (
                  <div className="flex-1 pt-[14px] px-1">
                    <div
                      className={cn(
                        "h-px",
                        done ? "bg-success/40" : "bg-border",
                      )}
                    />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Expanded phase detail panel */}
      {expandedGroup && (
        <PhaseDetailPanel
          groupId={expandedGroup}
          report={report}
        />
      )}

      {/* Stats funnel row */}
      {report && <StatsRow report={report} />}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Step icon (circle with status)
// ---------------------------------------------------------------------------

function StepIcon({
  complete,
  partial,
  hasErrors,
}: {
  complete: boolean;
  partial: boolean;
  hasErrors: boolean;
}) {
  if (hasErrors) {
    return (
      <div
        className={cn(
          "w-8 h-8 rounded-full flex items-center justify-center",
          "bg-warning/10 border-2 border-warning",
        )}
      >
        <AlertTriangle className="w-4 h-4 text-warning" />
      </div>
    );
  }
  if (complete) {
    return (
      <div
        className={cn(
          "w-8 h-8 rounded-full flex items-center justify-center",
          "bg-success/10 border-2 border-success",
        )}
      >
        <CheckCircle2 className="w-4 h-4 text-success" />
      </div>
    );
  }
  if (partial) {
    return (
      <div
        className={cn(
          "w-8 h-8 rounded-full flex items-center justify-center",
          "bg-accent/10 border-2 border-accent/50",
        )}
      >
        <Clock className="w-4 h-4 text-accent" />
      </div>
    );
  }
  return (
    <div
      className={cn(
        "w-8 h-8 rounded-full flex items-center justify-center",
        "bg-white/[0.03] border-2 border-border",
      )}
    >
      <Circle className="w-3.5 h-3.5 text-text-secondary/30" />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Phase detail panel (errors/warnings for selected group)
// ---------------------------------------------------------------------------

function PhaseDetailPanel({
  groupId,
  report,
}: {
  groupId: string;
  report: PipelineReport | null;
}) {
  if (!report) return null;

  const phases = report.phases.filter((p) =>
    p.name.toLowerCase().includes(groupId),
  );
  if (phases.length === 0) return null;

  return (
    <div className="px-4 pb-4 border-t border-border">
      <div className="mt-3 space-y-3">
        {phases.map((phase) => (
          <div key={phase.name} className="space-y-1.5">
            <div className="flex items-center gap-2">
              {phase.success ? (
                <CheckCircle2 className="w-3.5 h-3.5 text-success" />
              ) : (
                <XCircle className="w-3.5 h-3.5 text-error" />
              )}
              <span className="text-xs font-medium">
                {phase.name.replace(/_/g, " ")}
              </span>
            </div>
            {phase.errors.map((err, i) => (
              <div
                key={`e-${i}`}
                className={cn(
                  "ml-6 flex items-start gap-1.5",
                  "text-xs text-error/80",
                )}
              >
                <XCircle className="w-3 h-3 mt-0.5 shrink-0" />
                <span className="break-all">{err}</span>
              </div>
            ))}
            {phase.warnings.map((warn, i) => (
              <div
                key={`w-${i}`}
                className={cn(
                  "ml-6 flex items-start gap-1.5",
                  "text-xs text-warning/80",
                )}
              >
                <AlertTriangle className="w-3 h-3 mt-0.5 shrink-0" />
                <span>{warn}</span>
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Overall status badge
// ---------------------------------------------------------------------------

function OverallBadge({ success }: { success: boolean }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5",
        "px-2.5 py-1 rounded-full text-xs font-medium",
        success
          ? "bg-success/10 text-success"
          : "bg-warning/10 text-warning",
      )}
    >
      {success ? (
        <>
          <CheckCircle2 className="w-3 h-3" /> Complete
        </>
      ) : (
        <>
          <AlertTriangle className="w-3 h-3" /> In Progress
        </>
      )}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Stats funnel row
// ---------------------------------------------------------------------------

function StatsRow({ report }: { report: PipelineReport }) {
  const stats = [
    { label: "Planned", value: report.total_planned },
    { label: "Generated", value: report.total_generated },
    { label: "Deduped", value: report.total_passed_dedupe },
    { label: "Validated", value: report.total_passed_base_validation },
    { label: "Feedback", value: report.total_passed_feedback },
    { label: "Final", value: report.total_final },
    { label: "Synced", value: report.total_synced },
  ].filter((s) => s.value > 0);

  if (stats.length === 0) return null;

  return (
    <div
      className={cn(
        "flex items-center gap-6 px-4 py-3",
        "border-t border-border",
      )}
    >
      {stats.map((s, idx) => (
        <div key={s.label} className="flex items-center gap-3">
          <div className="text-center">
            <div className="text-sm font-semibold">{s.value}</div>
            <div className="text-[10px] text-text-secondary">
              {s.label}
            </div>
          </div>
          {/* Arrow between stats */}
          {idx < stats.length - 1 && (
            <span className="text-text-secondary/30 text-xs">
              &rarr;
            </span>
          )}
        </div>
      ))}
    </div>
  );
}
