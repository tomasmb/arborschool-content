"use client";

import { useEffect, useState, useCallback } from "react";
import {
  X,
  Loader2,
  DollarSign,
  Play,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Trash2,
} from "lucide-react";
import {
  estimatePipelineCost,
  getConfirmationToken,
  runPipeline,
  getJob,
  type CostEstimate,
  type JobStatus,
} from "@/lib/api";

type ModalState =
  | "estimating"
  | "confirm"
  | "running"
  | "completed"
  | "failed"
  | "error";

/** Label overrides for common parameter keys */
const PARAM_LABELS: Record<string, string> = {
  atom_id: "Atom",
  phase: "Phase",
  test_id: "Test",
  dry_run: "Dry Run",
  variants_per_question: "Variants / Question",
};

interface GeneratePipelineModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  pipelineId: string;
  pipelineName: string;
  pipelineDescription: string;
  params: Record<string, unknown>;
  /** Optional display labels for param values (e.g. atom title) */
  paramLabels?: Record<string, string>;
}

/**
 * Modal for running generation pipelines with cost estimation and progress tracking.
 * Flow: estimate cost → confirm → run → poll status → show result
 */
export function GeneratePipelineModal({
  isOpen,
  onClose,
  onSuccess,
  pipelineId,
  pipelineName,
  pipelineDescription,
  params,
  paramLabels,
}: GeneratePipelineModalProps) {
  const [state, setState] = useState<ModalState>("estimating");
  const [estimate, setEstimate] = useState<CostEstimate | null>(null);
  const [job, setJob] = useState<JobStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Fetch cost estimate on mount
  const fetchEstimate = useCallback(async () => {
    setState("estimating");
    setError(null);
    try {
      const est = await estimatePipelineCost(pipelineId, params);
      setEstimate(est);
      setState("confirm");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to estimate cost");
      setState("error");
    }
  }, [pipelineId, params]);

  useEffect(() => {
    if (isOpen) {
      fetchEstimate();
    }
  }, [isOpen, fetchEstimate]);

  // Poll job status while running
  useEffect(() => {
    if (state !== "running" || !job?.job_id) return;

    const pollInterval = setInterval(async () => {
      try {
        const updatedJob = await getJob(job.job_id);
        setJob(updatedJob);

        if (updatedJob.status === "completed") {
          setState("completed");
          clearInterval(pollInterval);
        } else if (
          updatedJob.status === "failed" ||
          updatedJob.status === "cancelled"
        ) {
          setState("failed");
          setError(updatedJob.error || "Pipeline failed");
          clearInterval(pollInterval);
        }
      } catch (err) {
        console.error("Failed to poll job status:", err);
      }
    }, 2000);

    return () => clearInterval(pollInterval);
  }, [state, job?.job_id]);

  // Handle escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape" && state !== "running") {
        handleClose();
      }
    };
    if (isOpen) {
      document.addEventListener("keydown", handleEscape);
      return () => document.removeEventListener("keydown", handleEscape);
    }
  }, [isOpen, state]);

  const handleConfirm = async () => {
    setState("running");
    setError(null);
    try {
      // Get confirmation token
      const { confirmation_token } = await getConfirmationToken(
        pipelineId,
        params
      );

      // Start the pipeline
      const result = await runPipeline(pipelineId, params, confirmation_token);
      const jobStatus = await getJob(result.job_id);
      setJob(jobStatus);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start pipeline");
      setState("error");
    }
  };

  const handleClose = () => {
    if (state === "running") return; // Don't allow closing while running

    // Reset state for next open
    setState("estimating");
    setEstimate(null);
    setJob(null);
    setError(null);

    if (state === "completed") {
      onSuccess();
    }
    onClose();
  };

  if (!isOpen) return null;

  const progress =
    job && job.total_items > 0
      ? Math.round((job.completed_items / job.total_items) * 100)
      : 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={state !== "running" ? handleClose : undefined}
      />

      {/* Modal */}
      <div className="relative w-full max-w-md bg-surface border border-border rounded-xl shadow-xl mx-4">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div>
            <h2 className="font-semibold">{pipelineName}</h2>
            <p className="text-sm text-text-secondary mt-0.5">
              {pipelineDescription}
            </p>
          </div>
          {state !== "running" && (
            <button
              onClick={handleClose}
              className="p-2 hover:bg-white/5 rounded-lg transition-colors"
            >
              <X className="w-5 h-5 text-text-secondary" />
            </button>
          )}
        </div>

        {/* Content */}
        <div className="p-6">
          {/* Estimating state */}
          {state === "estimating" && (
            <div className="flex flex-col items-center py-8">
              <Loader2 className="w-8 h-8 text-accent animate-spin mb-4" />
              <p className="text-text-secondary">Estimating cost...</p>
            </div>
          )}

          {/* Confirm state - show params + cost estimate */}
          {state === "confirm" && estimate && (
            <div className="space-y-4">
              {/* Parameters summary */}
              <ParamsSummary
                params={params}
                paramLabels={paramLabels}
              />

              {/* Stale artifact cleanup warning */}
              {estimate.stale_artifacts?.has_stale_data && (
                <StaleArtifactsWarning
                  artifacts={estimate.stale_artifacts}
                />
              )}

              <div className="p-4 bg-background border border-border rounded-lg">
                <div className="flex items-center gap-2 mb-3">
                  <DollarSign className="w-5 h-5 text-warning" />
                  <h3 className="font-medium">Estimated Cost</h3>
                </div>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-text-secondary">Model</p>
                    <p className="font-mono">{estimate.model}</p>
                  </div>
                  <div>
                    <p className="text-text-secondary">Cost Range</p>
                    <p className="font-mono text-warning">
                      ${estimate.estimated_cost_min.toFixed(2)} - $
                      {estimate.estimated_cost_max.toFixed(2)}
                    </p>
                  </div>
                  <div>
                    <p className="text-text-secondary">Input Tokens</p>
                    <p className="font-mono">
                      {estimate.input_tokens.toLocaleString()}
                    </p>
                  </div>
                  <div>
                    <p className="text-text-secondary">Output Tokens</p>
                    <p className="font-mono">
                      {estimate.output_tokens.toLocaleString()}
                    </p>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2 p-3 bg-warning/10 border border-warning/20 rounded-lg">
                <AlertTriangle className="w-4 h-4 text-warning flex-shrink-0" />
                <p className="text-sm text-warning">
                  This will call the AI API and incur charges.
                </p>
              </div>
            </div>
          )}

          {/* Running state - show progress */}
          {state === "running" && job && (
            <div className="space-y-4">
              <div className="flex flex-col items-center py-4">
                <Loader2 className="w-8 h-8 text-accent animate-spin mb-4" />
                <p className="font-medium">Running pipeline...</p>
                {job.current_item && (
                  <p className="text-sm text-text-secondary mt-1">
                    Processing: {job.current_item}
                  </p>
                )}
              </div>

              {/* Progress bar */}
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-text-secondary">Progress</span>
                  <span>
                    {job.completed_items} / {job.total_items}
                  </span>
                </div>
                <div className="h-2 bg-background rounded-full overflow-hidden">
                  <div
                    className="h-full bg-accent transition-all duration-300"
                    style={{ width: `${progress}%` }}
                  />
                </div>
              </div>

              {job.failed_items > 0 && (
                <p className="text-sm text-error">
                  {job.failed_items} item(s) failed
                </p>
              )}
            </div>
          )}

          {/* Completed state */}
          {state === "completed" && job && (
            <div className="flex flex-col items-center py-8">
              <CheckCircle2 className="w-12 h-12 text-success mb-4" />
              <p className="font-semibold text-lg">Generation Complete!</p>
              <p className="text-text-secondary mt-1">
                {job.completed_items} item(s) generated successfully
              </p>
              {job.failed_items > 0 && (
                <p className="text-sm text-warning mt-2">
                  {job.failed_items} item(s) failed
                </p>
              )}
            </div>
          )}

          {/* Failed state */}
          {state === "failed" && (
            <div className="flex flex-col items-center py-8">
              <XCircle className="w-12 h-12 text-error mb-4" />
              <p className="font-semibold text-lg">Generation Failed</p>
              {error && (
                <p className="text-sm text-error mt-2 text-center">{error}</p>
              )}
            </div>
          )}

          {/* Error state */}
          {state === "error" && (
            <div className="flex flex-col items-center py-8">
              <XCircle className="w-12 h-12 text-error mb-4" />
              <p className="font-semibold text-lg">Error</p>
              {error && (
                <p className="text-sm text-error mt-2 text-center">{error}</p>
              )}
            </div>
          )}
        </div>

        {/* Footer with action buttons */}
        <div className="px-6 py-4 border-t border-border flex justify-end gap-3">
          {state === "confirm" && (
            <>
              <button
                onClick={handleClose}
                className="px-4 py-2 text-sm font-medium hover:bg-white/5 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirm}
                className="flex items-center gap-2 px-4 py-2 bg-accent text-white rounded-lg text-sm font-medium hover:bg-accent/90 transition-colors"
              >
                <Play className="w-4 h-4" />
                Confirm & Run
              </button>
            </>
          )}

          {state === "error" && (
            <>
              <button
                onClick={handleClose}
                className="px-4 py-2 text-sm font-medium hover:bg-white/5 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={fetchEstimate}
                className="px-4 py-2 bg-accent text-white rounded-lg text-sm font-medium hover:bg-accent/90 transition-colors"
              >
                Retry
              </button>
            </>
          )}

          {(state === "completed" || state === "failed") && (
            <button
              onClick={handleClose}
              className="px-4 py-2 bg-accent text-white rounded-lg text-sm font-medium hover:bg-accent/90 transition-colors"
            >
              Close
            </button>
          )}
        </div>
      </div>
    </div>
  );
}


// ---------------------------------------------------------------------------
// Parameters summary (shows what the user is about to run)
// ---------------------------------------------------------------------------

function ParamsSummary({
  params,
  paramLabels,
}: {
  params: Record<string, unknown>;
  paramLabels?: Record<string, string>;
}) {
  const entries = Object.entries(params).filter(
    ([, v]) => v !== undefined && v !== null && v !== "",
  );

  if (entries.length === 0) return null;

  return (
    <div className="p-4 bg-background border border-border rounded-lg">
      <h3 className="text-sm font-medium mb-2">
        Run Configuration
      </h3>
      <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
        {entries.map(([key, value]) => {
          const label =
            PARAM_LABELS[key] ||
            key.replace(/_/g, " ").replace(/\b\w/g, (c) =>
              c.toUpperCase(),
            );
          const display =
            paramLabels?.[key] || String(value);

          return (
            <div key={key}>
              <p className="text-text-secondary text-xs">
                {label}
              </p>
              <p className="font-mono truncate" title={display}>
                {display}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}


// ---------------------------------------------------------------------------
// Stale artifacts cleanup warning
// ---------------------------------------------------------------------------

/** Human-readable labels for checkpoint filenames. */
function formatCheckpoint(filename: string): string {
  return filename
    .replace("phase_", "")
    .replace(".json", "")
    .replace(/_/g, " ");
}

function StaleArtifactsWarning({
  artifacts,
}: {
  artifacts: NonNullable<CostEstimate["stale_artifacts"]>;
}) {
  const lines: string[] = [];

  if (artifacts.checkpoint_files.length > 0) {
    const names = artifacts.checkpoint_files
      .map(formatCheckpoint)
      .join(", ");
    lines.push(
      `${artifacts.checkpoint_files.length} checkpoint(s): ${names}`,
    );
  }
  if (artifacts.item_count > 0) {
    lines.push(
      `${artifacts.item_count} generated question file(s)`,
    );
  }
  if (artifacts.has_report) {
    lines.push("Pipeline report");
  }

  if (lines.length === 0) return null;

  return (
    <div className="p-4 bg-error/10 border border-error/20 rounded-lg">
      <div className="flex items-center gap-2 mb-2">
        <Trash2 className="w-4 h-4 text-error flex-shrink-0" />
        <h3 className="text-sm font-medium text-error">
          Previous data will be deleted
        </h3>
      </div>
      <ul className="text-sm text-error/80 space-y-1 ml-6 list-disc">
        {lines.map((line) => (
          <li key={line}>{line}</li>
        ))}
      </ul>
    </div>
  );
}
