"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  X, CheckCircle2, AlertTriangle, XCircle, Wrench,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  startAtomFix,
  getAtomFixStatus,
  type AtomFixStatusResponse,
} from "@/lib/api";

type ModalStep = "configure" | "progress" | "results";

interface AtomFixModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  subjectId: string;
  issuesCount: number;
  onSuccess?: () => void;
}

export function AtomFixModal({
  open,
  onOpenChange,
  subjectId,
  issuesCount,
  onSuccess,
}: AtomFixModalProps) {
  const [step, setStep] = useState<ModalStep>("configure");
  const [dryRun, setDryRun] = useState(true);
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] =
    useState<AtomFixStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [estimatedCost, setEstimatedCost] = useState<number>(0);
  const intervalRef = useRef<ReturnType<typeof setInterval>>();

  // Cleanup on close
  useEffect(() => {
    if (!open) {
      if (intervalRef.current) clearInterval(intervalRef.current);
      const t = setTimeout(() => {
        setStep("configure");
        setDryRun(true);
        setJobId(null);
        setStatus(null);
        setError(null);
        setEstimatedCost(0);
      }, 300);
      return () => clearTimeout(t);
    }
  }, [open]);

  // Poll for progress
  const pollProgress = useCallback(
    async (jid: string) => {
      try {
        const result = await getAtomFixStatus(subjectId, jid);
        setStatus(result);
        if (
          result.status === "completed" ||
          result.status === "failed"
        ) {
          if (intervalRef.current)
            clearInterval(intervalRef.current);
          setStep("results");
          if (result.status === "completed") onSuccess?.();
        }
      } catch {
        if (intervalRef.current)
          clearInterval(intervalRef.current);
        setError("Job lost (server restarted). Please retry.");
        setStep("results");
      }
    },
    [subjectId, onSuccess],
  );

  const handleStart = async () => {
    setError(null);
    try {
      const resp = await startAtomFix(subjectId, {
        dry_run: dryRun,
      });
      setJobId(resp.job_id);
      setEstimatedCost(resp.estimated_cost_usd);
      setStep("progress");
      intervalRef.current = setInterval(
        () => pollProgress(resp.job_id),
        2000,
      );
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : "Failed to start",
      );
    }
  };

  const handleClose = () => {
    if (step === "progress") return;
    onOpenChange(false);
  };

  if (!open) return null;

  const progress = status?.progress;
  const progressPct =
    progress && progress.total > 0
      ? (progress.completed / progress.total) * 100
      : 0;
  const report = status?.change_report ?? null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      onClick={step !== "progress" ? handleClose : undefined}
    >
      <div className="absolute inset-0 bg-black/60" />

      <div
        className={cn(
          "relative bg-surface border border-border rounded-xl",
          "shadow-xl w-full max-w-lg mx-4",
        )}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div className="flex items-center gap-2">
            <Wrench className="w-4 h-4 text-accent" />
            <h2 className="font-semibold">
              Fix Validation Issues
            </h2>
          </div>
          {step !== "progress" && (
            <button
              onClick={handleClose}
              className="p-1 hover:bg-white/10 rounded"
            >
              <X className="w-4 h-4 text-text-secondary" />
            </button>
          )}
        </div>

        {/* Body */}
        <div className="px-6 py-5">
          {step === "configure" && (
            <ConfigureStep
              issuesCount={issuesCount}
              dryRun={dryRun}
              onDryRunChange={setDryRun}
              error={error}
            />
          )}

          {step === "progress" && (
            <ProgressStep
              progress={progress}
              progressPct={progressPct}
              dryRun={dryRun}
            />
          )}

          {step === "results" && (
            <ResultsStep
              error={error}
              status={status}
              progress={progress}
              report={report}
              dryRun={dryRun}
            />
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-3 px-6 py-4 border-t border-border">
          {step === "configure" && (
            <>
              <button
                onClick={handleClose}
                className={cn(
                  "px-4 py-2 text-sm rounded-lg",
                  "text-text-secondary hover:text-text-primary",
                  "transition-colors",
                )}
              >
                Cancel
              </button>
              <button
                onClick={handleStart}
                disabled={issuesCount === 0}
                className={cn(
                  "px-4 py-2 text-sm rounded-lg font-medium",
                  "transition-colors",
                  issuesCount > 0
                    ? "bg-accent text-white hover:bg-accent/90"
                    : "bg-surface text-text-secondary cursor-not-allowed",
                )}
              >
                {dryRun ? "Start Dry Run" : "Start Fix"}
              </button>
            </>
          )}
          {step === "results" && (
            <button
              onClick={handleClose}
              className={cn(
                "px-4 py-2 text-sm rounded-lg bg-accent",
                "text-white font-medium hover:bg-accent/90",
                "transition-colors",
              )}
            >
              Done
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Step sub-components (keep modal file under 500 lines)
// ---------------------------------------------------------------------------

function ConfigureStep({
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

function ProgressStep({
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
        {dryRun ? "Analysing fixes (dry run)..." : "Applying fixes..."}
      </p>

      <div>
        <div className="flex justify-between text-xs text-text-secondary mb-1">
          <span>
            {progress?.completed ?? 0}/{progress?.total ?? 0} actions
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

function ResultsStep({
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
        <div className="max-h-40 overflow-y-auto space-y-1">
          {status.results.map((r, i) => (
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
    { label: "Prereq cascades", value: report.prerequisite_cascades },
    { label: "Q-mapping updates", value: report.question_mapping_updates },
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
              <li key={i}>• {msg}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
