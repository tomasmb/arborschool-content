/**
 * Step sub-components for the AtomFixModal.
 *
 * Extracted to keep the main modal file under 500 lines.
 * Each step renders the body content for one phase of the fix flow:
 *   - ConfigureStep: dry-run toggle, issue count, start button
 *   - ProgressStep:  progress bar + counters during execution
 *   - ResultsStep:   summary, change report, per-action results
 */

import {
  CheckCircle2, AlertTriangle, XCircle, Play,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { AtomFixStatusResponse } from "@/lib/api";

// ---------------------------------------------------------------------------
// ConfigureStep
// ---------------------------------------------------------------------------

export function ConfigureStep({
  issuesCount,
  dryRun,
  onDryRunChange,
  error,
}: {
  issuesCount: number;
  dryRun: boolean;
  onDryRunChange: (v: boolean) => void;
  error: string | null;
}) {
  return (
    <div className="space-y-5">
      <p className="text-sm text-text-secondary">
        Use GPT-5.1 to automatically fix atoms with validation
        issues. Handles splits, merges, content quality, fidelity,
        prerequisites, and coverage gaps.
      </p>

      <div className="bg-background rounded-lg p-3 text-sm">
        <span className="text-text-secondary">
          Standards with issues:{" "}
        </span>
        <span className="font-medium">{issuesCount}</span>
      </div>

      {/* Dry-run toggle */}
      <label className="flex items-center gap-3 cursor-pointer">
        <input
          type="checkbox"
          checked={dryRun}
          onChange={(e) => onDryRunChange(e.target.checked)}
          className="w-4 h-4 accent-accent rounded"
        />
        <div>
          <span className="text-sm font-medium">Dry run</span>
          <p className="text-xs text-text-secondary mt-0.5">
            Preview changes without modifying files
          </p>
        </div>
      </label>

      {!dryRun && (
        <div className="flex items-start gap-2 p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
          <AlertTriangle className="w-4 h-4 text-amber-500 mt-0.5 flex-shrink-0" />
          <p className="text-xs text-amber-400">
            This will modify the atoms file, update prerequisites,
            and rewrite question mappings. Make sure you have a
            backup or can revert via git.
          </p>
        </div>
      )}

      {error && (
        <div className="text-sm text-error">{error}</div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// ProgressStep
// ---------------------------------------------------------------------------

export function ProgressStep({
  progress,
  progressPct,
  dryRun,
}: {
  progress: AtomFixStatusResponse["progress"] | undefined;
  progressPct: number;
  dryRun: boolean;
}) {
  return (
    <div className="space-y-4">
      <p className="text-sm text-text-secondary">
        {dryRun
          ? "Analysing fixes (dry run)..."
          : "Applying fixes..."}
      </p>

      <div>
        <div className="flex justify-between text-xs text-text-secondary mb-1">
          <span>
            {progress?.completed ?? 0}/{progress?.total ?? 0}{" "}
            actions
          </span>
          <span>{progressPct.toFixed(0)}%</span>
        </div>
        <div className="h-2 bg-background rounded-full">
          <div
            className="h-full bg-accent rounded-full transition-all"
            style={{ width: `${progressPct}%` }}
          />
        </div>
      </div>

      <div className="flex gap-4 text-sm">
        <span className="text-success">
          {progress?.succeeded ?? 0} succeeded
        </span>
        <span className="text-error">
          {progress?.failed ?? 0} failed
        </span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// ResultsStep
// ---------------------------------------------------------------------------

export function ResultsStep({
  error,
  status,
  progress,
  report,
  dryRun,
}: {
  error: string | null;
  status: AtomFixStatusResponse | null;
  progress: AtomFixStatusResponse["progress"] | undefined;
  report: AtomFixStatusResponse["change_report"];
  dryRun: boolean;
}) {
  return (
    <div className="space-y-4">
      {/* Status banner */}
      {error ? (
        <div className="flex items-center gap-2 text-error text-sm">
          <XCircle className="w-4 h-4" />
          {error}
        </div>
      ) : status?.status === "completed" ? (
        <div className="flex items-center gap-2 text-success text-sm font-medium">
          <CheckCircle2 className="w-5 h-5" />
          {dryRun ? "Dry Run Complete" : "Fixes Applied"}
        </div>
      ) : (
        <div className="flex items-center gap-2 text-error text-sm font-medium">
          <XCircle className="w-5 h-5" />
          Fix Pipeline Failed
        </div>
      )}

      {/* Dry-run hint */}
      {dryRun && status?.status === "completed" && (
        <div className="flex items-start gap-2 p-3 rounded-lg bg-accent/10 border border-accent/20">
          <Play className="w-4 h-4 text-accent mt-0.5 flex-shrink-0" />
          <p className="text-xs text-text-secondary">
            Results are saved. Review below, then click{" "}
            <span className="font-medium text-text-primary">
              Apply Results
            </span>{" "}
            to write changes — no LLM re-run needed.
          </p>
        </div>
      )}

      {/* Counters */}
      {progress && (
        <div className="grid grid-cols-3 gap-3">
          <StatCard label="Total" value={progress.total} />
          <StatCard
            label="Succeeded"
            value={progress.succeeded}
            className="text-success"
          />
          <StatCard
            label="Failed"
            value={progress.failed}
            className="text-error"
          />
        </div>
      )}

      {/* Change report */}
      {report && <ChangeReportSection report={report} />}

      {/* Per-action results */}
      {status?.results && status.results.length > 0 && (
        <ActionResultsList results={status.results} />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Small reusable pieces
// ---------------------------------------------------------------------------

function StatCard({
  label,
  value,
  className,
}: {
  label: string;
  value: number;
  className?: string;
}) {
  return (
    <div className="bg-background rounded-lg p-3 text-center">
      <div className={cn("text-lg font-bold", className)}>
        {value}
      </div>
      <div className="text-xs text-text-secondary">{label}</div>
    </div>
  );
}

function ChangeReportSection({
  report,
}: {
  report: NonNullable<AtomFixStatusResponse["change_report"]>;
}) {
  const items = [
    { label: "Atoms added", value: report.atoms_added.length },
    { label: "Atoms removed", value: report.atoms_removed.length },
    { label: "Atoms modified", value: report.atoms_modified.length },
    {
      label: "Prereq cascades",
      value: report.prerequisite_cascades,
    },
    {
      label: "Q-mapping updates",
      value: report.question_mapping_updates,
    },
  ];
  const hasManualReview = report.manual_review_needed.length > 0;

  return (
    <div className="bg-background rounded-lg p-3 space-y-2">
      <h4 className="text-xs font-medium text-text-secondary uppercase tracking-wide">
        Change Report
      </h4>
      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
        {items.map((item) => (
          <div key={item.label} className="flex justify-between">
            <span className="text-text-secondary">
              {item.label}
            </span>
            <span className="font-medium">{item.value}</span>
          </div>
        ))}
      </div>
      {hasManualReview && (
        <div className="mt-2 pt-2 border-t border-border">
          <p className="text-xs text-amber-400 font-medium mb-1">
            Manual review needed:
          </p>
          <ul className="text-xs text-text-secondary space-y-0.5">
            {report.manual_review_needed.map((msg, i) => (
              <li key={i}>- {msg}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function ActionResultsList({
  results,
}: {
  results: AtomFixStatusResponse["results"];
}) {
  return (
    <div className="max-h-40 overflow-y-auto space-y-1">
      {results.map((r, i) => (
        <div
          key={`${r.standard_id}-${r.fix_type}-${i}`}
          className="flex items-center gap-2 text-sm px-2 py-1"
        >
          {r.success ? (
            <CheckCircle2 className="w-3.5 h-3.5 text-success flex-shrink-0" />
          ) : (
            <XCircle className="w-3.5 h-3.5 text-error flex-shrink-0" />
          )}
          <span className="font-mono text-xs">
            {r.fix_type}
          </span>
          <span className="text-xs text-text-secondary truncate">
            {r.atom_ids.join(", ") || r.standard_id}
          </span>
          {r.error && (
            <span className="text-xs text-error truncate ml-auto">
              {r.error}
            </span>
          )}
        </div>
      ))}
    </div>
  );
}
