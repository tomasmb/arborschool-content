"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { X, CheckCircle2, AlertTriangle, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  startAtomValidation,
  getAtomValidationStatus,
  type AtomValidationStatusResponse,
} from "@/lib/api";

// Cost per standard (Gemini 3 Pro, high thinking)
const COST_PER_STANDARD = 0.08;

type ModalStep = "configure" | "progress" | "results";
type SelectionMode = "unvalidated" | "all" | "specific";

interface AtomValidationModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  subjectId: string;
  stats: {
    standards_count: number;
    standards_validated: number;
  };
  onSuccess?: () => void;
}

export function AtomValidationModal({
  open,
  onOpenChange,
  subjectId,
  stats,
  onSuccess,
}: AtomValidationModalProps) {
  const [step, setStep] = useState<ModalStep>("configure");
  const [selection, setSelection] =
    useState<SelectionMode>("unvalidated");
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] =
    useState<AtomValidationStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval>>();

  // Calculate items to process
  const unvalidatedCount =
    stats.standards_count - stats.standards_validated;
  const itemsToProcess =
    selection === "unvalidated"
      ? unvalidatedCount
      : stats.standards_count;
  const estimatedCost = (
    itemsToProcess * COST_PER_STANDARD
  ).toFixed(2);

  // Cleanup on close
  useEffect(() => {
    if (!open) {
      if (intervalRef.current) clearInterval(intervalRef.current);
      // Reset state after animation
      const t = setTimeout(() => {
        setStep("configure");
        setJobId(null);
        setStatus(null);
        setError(null);
        setSelection("unvalidated");
      }, 300);
      return () => clearTimeout(t);
    }
  }, [open]);

  // Poll for progress
  const pollProgress = useCallback(
    async (jid: string) => {
      try {
        const result = await getAtomValidationStatus(
          subjectId,
          jid,
        );
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
        // Job may have been lost (server restart)
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
      const resp = await startAtomValidation(subjectId, {
        selection_mode: selection,
      });
      setJobId(resp.job_id);
      setStep("progress");
      // Start polling
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
    if (step === "progress") return; // Block close during progress
    onOpenChange(false);
  };

  if (!open) return null;

  const progress = status?.progress;
  const progressPct =
    progress && progress.total > 0
      ? (progress.completed / progress.total) * 100
      : 0;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      onClick={step !== "progress" ? handleClose : undefined}
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60" />

      {/* Modal */}
      <div
        className="relative bg-surface border border-border rounded-xl shadow-xl w-full max-w-lg mx-4"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <h2 className="font-semibold">
            Atom Quality Validation
          </h2>
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
            <div className="space-y-5">
              <p className="text-sm text-text-secondary">
                Run LLM-based quality validation on atoms per
                standard. Checks fidelity, granularity, coverage,
                and prerequisites.
              </p>

              {/* Selection mode */}
              <div className="space-y-2">
                <label className="text-sm font-medium">
                  Standards to validate
                </label>
                <div className="space-y-2">
                  <RadioOption
                    selected={selection === "unvalidated"}
                    onSelect={() => setSelection("unvalidated")}
                    label={`Unvalidated only (${unvalidatedCount})`}
                    disabled={unvalidatedCount === 0}
                  />
                  <RadioOption
                    selected={selection === "all"}
                    onSelect={() => setSelection("all")}
                    label={`All standards (${stats.standards_count})`}
                  />
                </div>
              </div>

              {/* Cost estimate */}
              <div className="bg-background rounded-lg p-3 text-sm">
                <span className="text-text-secondary">
                  Estimated cost:{" "}
                </span>
                <span className="font-medium">
                  ~${estimatedCost}
                </span>
                <span className="text-text-secondary">
                  {" "}
                  ({itemsToProcess} standard
                  {itemsToProcess !== 1 ? "s" : ""})
                </span>
              </div>

              {error && (
                <div className="text-sm text-error">{error}</div>
              )}
            </div>
          )}

          {step === "progress" && (
            <div className="space-y-4">
              <p className="text-sm text-text-secondary">
                Validating atoms against standards...
              </p>

              {/* Progress bar */}
              <div>
                <div className="flex justify-between text-xs text-text-secondary mb-1">
                  <span>
                    {progress?.completed ?? 0}/
                    {progress?.total ?? 0} standards
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

              {/* Counts */}
              <div className="flex gap-4 text-sm">
                <span className="text-success">
                  {progress?.passed ?? 0} passed
                </span>
                <span className="text-amber-500">
                  {progress?.with_issues ?? 0} with issues
                </span>
              </div>
            </div>
          )}

          {step === "results" && (
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
                  Validation Complete
                </div>
              ) : (
                <div className="flex items-center gap-2 text-error text-sm font-medium">
                  <XCircle className="w-5 h-5" />
                  Validation Failed
                </div>
              )}

              {/* Results summary */}
              {progress && (
                <div className="grid grid-cols-3 gap-3">
                  <div className="bg-background rounded-lg p-3 text-center">
                    <div className="text-lg font-bold">
                      {progress.total}
                    </div>
                    <div className="text-xs text-text-secondary">
                      Total
                    </div>
                  </div>
                  <div className="bg-background rounded-lg p-3 text-center">
                    <div className="text-lg font-bold text-success">
                      {progress.passed}
                    </div>
                    <div className="text-xs text-text-secondary">
                      Passed
                    </div>
                  </div>
                  <div className="bg-background rounded-lg p-3 text-center">
                    <div className="text-lg font-bold text-amber-500">
                      {progress.with_issues}
                    </div>
                    <div className="text-xs text-text-secondary">
                      Issues
                    </div>
                  </div>
                </div>
              )}

              {/* Per-standard results */}
              {status?.results && status.results.length > 0 && (
                <div className="max-h-48 overflow-y-auto space-y-1">
                  {status.results.map((r) => (
                    <div
                      key={r.standard_id}
                      className="flex items-center gap-2 text-sm px-2 py-1"
                    >
                      {r.status === "pass" ? (
                        <CheckCircle2 className="w-3.5 h-3.5 text-success flex-shrink-0" />
                      ) : r.status === "error" ? (
                        <XCircle className="w-3.5 h-3.5 text-error flex-shrink-0" />
                      ) : (
                        <AlertTriangle className="w-3.5 h-3.5 text-amber-500 flex-shrink-0" />
                      )}
                      <span className="font-mono text-xs">
                        {r.standard_id}
                      </span>
                      {r.error && (
                        <span className="text-xs text-error truncate">
                          {r.error}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-3 px-6 py-4 border-t border-border">
          {step === "configure" && (
            <>
              <button
                onClick={handleClose}
                className="px-4 py-2 text-sm rounded-lg text-text-secondary hover:text-text-primary transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleStart}
                disabled={itemsToProcess === 0}
                className={cn(
                  "px-4 py-2 text-sm rounded-lg font-medium transition-colors",
                  itemsToProcess > 0
                    ? "bg-accent text-white hover:bg-accent/90"
                    : "bg-surface text-text-secondary cursor-not-allowed",
                )}
              >
                Start Validation (~${estimatedCost})
              </button>
            </>
          )}
          {step === "results" && (
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

// -----------------------------------------------------------------------------
// Radio option helper
// -----------------------------------------------------------------------------

function RadioOption({
  selected,
  onSelect,
  label,
  disabled,
}: {
  selected: boolean;
  onSelect: () => void;
  label: string;
  disabled?: boolean;
}) {
  return (
    <button
      onClick={onSelect}
      disabled={disabled}
      className={cn(
        "flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sm text-left transition-colors",
        selected
          ? "bg-accent/10 border border-accent/30"
          : "bg-background border border-transparent hover:border-border",
        disabled && "opacity-50 cursor-not-allowed",
      )}
    >
      <div
        className={cn(
          "w-4 h-4 rounded-full border-2 flex items-center justify-center",
          selected ? "border-accent" : "border-text-secondary/40",
        )}
      >
        {selected && (
          <div className="w-2 h-2 rounded-full bg-accent" />
        )}
      </div>
      <span>{label}</span>
    </button>
  );
}
