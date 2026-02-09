"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { X, Wrench, RotateCcw, Play } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  startAtomFix,
  getAtomFixStatus,
  applyAtomFixSaved,
  retryAtomFixFailed,
  type AtomFixStatusResponse,
} from "@/lib/api";
import {
  ConfigureStep,
  ProgressStep,
  ResultsStep,
} from "./AtomFixModalSteps";

type ModalStep = "configure" | "progress" | "results";

interface AtomFixModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  subjectId: string;
  issuesCount: number;
  hasSavedResults?: boolean;
  onSuccess?: () => void;
}

export function AtomFixModal({
  open,
  onOpenChange,
  subjectId,
  issuesCount,
  hasSavedResults = false,
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

  // Cleanup on close.
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

  // Poll for progress.
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
          if (
            result.status === "completed" && !result.dry_run
          ) {
            onSuccess?.();
          }
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

  // Start polling a new job.
  const startPolling = useCallback(
    (jid: string) => {
      setJobId(jid);
      setStep("progress");
      setError(null);
      intervalRef.current = setInterval(
        () => pollProgress(jid), 2000,
      );
    },
    [pollProgress],
  );

  // Start fresh fix run.
  const handleStart = async () => {
    setError(null);
    setStatus(null);
    try {
      const resp = await startAtomFix(subjectId, {
        dry_run: dryRun,
      });
      setEstimatedCost(resp.estimated_cost_usd);
      startPolling(resp.job_id);
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : "Failed to start",
      );
    }
  };

  // Apply previously saved dry-run results (no LLM re-run).
  const handleApplySaved = async () => {
    setError(null);
    setStatus(null);
    try {
      const resp = await applyAtomFixSaved(subjectId);
      setDryRun(false);
      setEstimatedCost(0);
      startPolling(resp.job_id);
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to apply saved results",
      );
    }
  };

  // Retry only failed actions.
  const handleRetryFailed = async () => {
    setError(null);
    setStatus(null);
    try {
      const resp = await retryAtomFixFailed(subjectId, {
        dry_run: true,
      });
      setDryRun(true);
      setEstimatedCost(resp.estimated_cost_usd);
      startPolling(resp.job_id);
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to retry",
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
  const hasFailed = (progress?.failed ?? 0) > 0;
  const hasSucceeded = (progress?.succeeded ?? 0) > 0;
  const isDryRunDone =
    step === "results" &&
    status?.dry_run === true &&
    status?.status === "completed";
  const canApply = isDryRunDone && hasSucceeded;
  const canRetry = step === "results" && hasFailed;

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
              hasSavedResults={hasSavedResults}
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
            <ConfigureFooter
              onClose={handleClose}
              onStart={handleStart}
              onApplySaved={handleApplySaved}
              dryRun={dryRun}
              issuesCount={issuesCount}
              hasSavedResults={hasSavedResults}
            />
          )}
          {step === "results" && (
            <ResultsFooter
              canApply={canApply}
              canRetry={canRetry}
              onApply={handleApplySaved}
              onRetry={handleRetryFailed}
              onClose={handleClose}
            />
          )}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Footer sub-components (tightly coupled to modal actions)
// ---------------------------------------------------------------------------

function ConfigureFooter({
  onClose,
  onStart,
  onApplySaved,
  dryRun,
  issuesCount,
  hasSavedResults,
}: {
  onClose: () => void;
  onStart: () => void;
  onApplySaved: () => void;
  dryRun: boolean;
  issuesCount: number;
  hasSavedResults: boolean;
}) {
  return (
    <>
      <button
        onClick={onClose}
        className={cn(
          "px-4 py-2 text-sm rounded-lg",
          "text-text-secondary hover:text-text-primary",
          "transition-colors",
        )}
      >
        Cancel
      </button>
      {hasSavedResults && (
        <button
          onClick={onApplySaved}
          className={cn(
            "flex items-center gap-1.5",
            "px-4 py-2 text-sm rounded-lg font-medium",
            "bg-success text-white hover:bg-success/90",
            "transition-colors",
          )}
        >
          <Play className="w-3.5 h-3.5" />
          Apply Saved Results
        </button>
      )}
      <button
        onClick={onStart}
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
  );
}

function ResultsFooter({
  canApply,
  canRetry,
  onApply,
  onRetry,
  onClose,
}: {
  canApply: boolean;
  canRetry: boolean;
  onApply: () => void;
  onRetry: () => void;
  onClose: () => void;
}) {
  return (
    <>
      <button
        onClick={onClose}
        className={cn(
          "px-4 py-2 text-sm rounded-lg",
          "text-text-secondary hover:text-text-primary",
          "transition-colors",
        )}
      >
        Done
      </button>
      {canRetry && (
        <button
          onClick={onRetry}
          className={cn(
            "flex items-center gap-1.5",
            "px-4 py-2 text-sm rounded-lg font-medium",
            "bg-amber-500/10 text-amber-400 border",
            "border-amber-500/20 hover:bg-amber-500/20",
            "transition-colors",
          )}
        >
          <RotateCcw className="w-3.5 h-3.5" />
          Retry Failed
        </button>
      )}
      {canApply && (
        <button
          onClick={onApply}
          className={cn(
            "flex items-center gap-1.5",
            "px-4 py-2 text-sm rounded-lg font-medium",
            "bg-success text-white hover:bg-success/90",
            "transition-colors",
          )}
        >
          <Play className="w-3.5 h-3.5" />
          Apply Results
        </button>
      )}
    </>
  );
}
