"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  X,
  CheckCircle2,
  XCircle,
  DollarSign,
  Sparkles,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  getBatchEnrichEstimate,
  startBatchEnrich,
  getBatchEnrichStatus,
  type BatchEnrichEstimate,
  type BatchEnrichStatus,
} from "@/lib/api";

type ModalStep = "estimating" | "confirm" | "running" | "completed";

interface BatchEnrichModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  subjectId: string;
  mode: string;
  onSuccess?: () => void;
}

export function BatchEnrichModal({
  open, onOpenChange, subjectId, mode, onSuccess,
}: BatchEnrichModalProps) {
  const [step, setStep] = useState<ModalStep>("estimating");
  const [estimate, setEstimate] = useState<BatchEnrichEstimate | null>(null);
  const [jobStatus, setJobStatus] = useState<BatchEnrichStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval>>();

  // Fetch estimate when modal opens
  useEffect(() => {
    if (!open) return;
    setStep("estimating");
    setEstimate(null);
    setJobStatus(null);
    setError(null);

    getBatchEnrichEstimate(subjectId, mode)
      .then((est) => {
        setEstimate(est);
        setStep("confirm");
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to estimate");
        setStep("confirm");
      });
  }, [open, subjectId, mode]);

  // Cleanup on close
  useEffect(() => {
    if (!open && intervalRef.current) {
      clearInterval(intervalRef.current);
    }
  }, [open]);

  // Poll for progress
  const pollProgress = useCallback(
    async (jobId: string) => {
      try {
        const result = await getBatchEnrichStatus(subjectId, jobId);
        setJobStatus(result);
        if (result.status === "completed" || result.status === "failed") {
          if (intervalRef.current) clearInterval(intervalRef.current);
          setStep("completed");
          if (result.status === "completed") onSuccess?.();
        }
      } catch {
        if (intervalRef.current) clearInterval(intervalRef.current);
        setError("Job lost (server restarted). Please retry.");
        setStep("completed");
      }
    },
    [subjectId, onSuccess],
  );

  const handleStart = async () => {
    setError(null);
    try {
      const resp = await startBatchEnrich(subjectId, mode);
      setJobStatus({
        job_id: resp.job_id, status: "started",
        total: resp.atoms_to_process, completed: 0,
        succeeded: 0, failed: 0, skipped: resp.skipped,
        current_atom: null, results: [],
        started_at: new Date().toISOString(), completed_at: null,
      });
      setStep("running");
      intervalRef.current = setInterval(() => pollProgress(resp.job_id), 2000);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to start");
    }
  };

  const handleClose = () => {
    if (step === "running") return;
    onOpenChange(false);
  };

  if (!open) return null;

  const modeLabel = mode === "all" ? "Re-enrich all" : "Unenriched only";
  const progressPct = jobStatus && jobStatus.total > 0
    ? (jobStatus.completed / jobStatus.total) * 100 : 0;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      onClick={step !== "running" ? handleClose : undefined}
    >
      <div className="absolute inset-0 bg-black/60" />
      <div
        className="relative bg-surface border border-border rounded-xl shadow-xl w-full max-w-lg mx-4"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-accent" />
            <h2 className="font-semibold">Batch Enrichment</h2>
          </div>
          {step !== "running" && (
            <button onClick={handleClose} className="p-1 hover:bg-white/10 rounded">
              <X className="w-4 h-4 text-text-secondary" />
            </button>
          )}
        </div>

        {/* Body */}
        <div className="px-6 py-5">
          {step === "estimating" && <EstimatingView />}
          {step === "confirm" && (
            <ConfirmView
              estimate={estimate}
              modeLabel={modeLabel}
              error={error}
            />
          )}
          {step === "running" && (
            <RunningView
              jobStatus={jobStatus}
              progressPct={progressPct}
            />
          )}
          {step === "completed" && (
            <CompletedView
              jobStatus={jobStatus}
              error={error}
            />
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-3 px-6 py-4 border-t border-border">
          {step === "confirm" && (
            <>
              <button
                onClick={handleClose}
                className="px-4 py-2 text-sm rounded-lg text-text-secondary hover:text-text-primary transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleStart}
                disabled={!estimate || estimate.atoms_to_process === 0}
                className={cn(
                  "px-4 py-2 text-sm rounded-lg font-medium transition-colors",
                  estimate && estimate.atoms_to_process > 0
                    ? "bg-accent text-white hover:bg-accent/90"
                    : "bg-surface text-text-secondary cursor-not-allowed",
                )}
              >
                Start Enrichment
                {estimate && ` (~$${estimate.estimated_cost_usd.toFixed(2)})`}
              </button>
            </>
          )}
          {step === "completed" && (
            <button
              onClick={handleClose}
              className="px-4 py-2 text-sm rounded-lg bg-accent text-white font-medium hover:bg-accent/90 transition-colors"
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
// Step views
// ---------------------------------------------------------------------------

function EstimatingView() {
  return (
    <div className="flex items-center justify-center py-8 gap-3 text-text-secondary">
      <Loader2 className="w-5 h-5 animate-spin" />
      <span className="text-sm">Calculating estimate...</span>
    </div>
  );
}

function ConfirmView({
  estimate, modeLabel, error,
}: {
  estimate: BatchEnrichEstimate | null;
  modeLabel: string;
  error: string | null;
}) {
  if (error) {
    return (
      <div className="flex items-center gap-2 text-error text-sm">
        <XCircle className="w-4 h-4" />
        {error}
      </div>
    );
  }
  if (!estimate) return null;

  return (
    <div className="space-y-4">
      <p className="text-sm text-text-secondary">
        Run Phase 1 enrichment (scope guardrails + difficulty rubric)
        for atoms with PAES question coverage.
      </p>

      <div className="bg-background rounded-lg p-4 space-y-3">
        <div className="flex justify-between text-sm">
          <span className="text-text-secondary">Mode</span>
          <span className="font-medium">{modeLabel}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-text-secondary">Atoms to enrich</span>
          <span className="font-medium">{estimate.atoms_to_process}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-text-secondary">Skipped</span>
          <span className="text-text-secondary">{estimate.skipped}</span>
        </div>
        <div className="border-t border-border pt-3 flex justify-between text-sm">
          <span className="flex items-center gap-1.5 text-text-secondary">
            <DollarSign className="w-4 h-4 text-warning" />
            Estimated cost
          </span>
          <span className="font-medium text-warning">
            ~${estimate.estimated_cost_usd.toFixed(2)}
          </span>
        </div>
      </div>

      {estimate.atoms_to_process === 0 && (
        <p className="text-sm text-text-secondary">
          No atoms to enrich in this mode.
        </p>
      )}
    </div>
  );
}

function RunningView({
  jobStatus, progressPct,
}: {
  jobStatus: BatchEnrichStatus | null;
  progressPct: number;
}) {
  return (
    <div className="space-y-4">
      <p className="text-sm text-text-secondary">
        Enriching atoms (5 concurrent)...
      </p>

      {/* Progress bar */}
      <div>
        <div className="flex justify-between text-xs text-text-secondary mb-1">
          <span>
            {jobStatus?.completed ?? 0}/{jobStatus?.total ?? 0} atoms
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

      {/* Current + counts */}
      <div className="space-y-2">
        {jobStatus?.current_atom && (
          <p className="text-xs text-text-secondary truncate">
            Current: <span className="font-mono">{jobStatus.current_atom}</span>
          </p>
        )}
        <div className="flex gap-4 text-sm">
          <span className="text-success">
            {jobStatus?.succeeded ?? 0} succeeded
          </span>
          {(jobStatus?.failed ?? 0) > 0 && (
            <span className="text-error">
              {jobStatus?.failed ?? 0} failed
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

function CompletedView({
  jobStatus, error,
}: {
  jobStatus: BatchEnrichStatus | null;
  error: string | null;
}) {
  return (
    <div className="space-y-4">
      {/* Status banner */}
      {error ? (
        <div className="flex items-center gap-2 text-error text-sm">
          <XCircle className="w-4 h-4" />
          {error}
        </div>
      ) : jobStatus?.status === "completed" ? (
        <div className="flex items-center gap-2 text-success text-sm font-medium">
          <CheckCircle2 className="w-5 h-5" />
          Enrichment Complete
        </div>
      ) : (
        <div className="flex items-center gap-2 text-error text-sm font-medium">
          <XCircle className="w-5 h-5" />
          Enrichment Failed
        </div>
      )}

      {/* Results grid */}
      {jobStatus && (
        <div className="grid grid-cols-3 gap-3">
          <ResultCard value={jobStatus.succeeded} label="Succeeded" cls="text-success" />
          <ResultCard value={jobStatus.failed} label="Failed" cls="text-error" />
          <ResultCard value={jobStatus.skipped} label="Skipped" cls="text-text-secondary" />
        </div>
      )}
    </div>
  );
}

function ResultCard({ value, label, cls }: { value: number; label: string; cls: string }) {
  return (
    <div className="bg-background rounded-lg p-3 text-center">
      <div className={cn("text-lg font-bold", cls)}>{value}</div>
      <div className="text-xs text-text-secondary">{label}</div>
    </div>
  );
}
