"use client";

import { useState, useEffect, useCallback } from "react";
import { X, Loader2, CheckCircle2, XCircle, AlertTriangle } from "lucide-react";
import {
  startEnrichment,
  startVariantEnrichment,
  getEnrichmentStatus,
  type EnrichmentResult,
} from "@/lib/api";

type ModalStep = "configure" | "progress" | "results";
type SelectionMode = "all" | "unenriched";
type EnrichmentTarget = "questions" | "variants";

interface EnrichmentModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  testId: string;
  subjectId: string;
  /** Target type - questions or variants. Defaults to questions. */
  target?: EnrichmentTarget;
  stats: {
    tagged_count: number;
    enriched_count: number;
  };
  onSuccess?: () => void;
}

/**
 * Modal for enriching questions or variants with educational feedback.
 * Flow: configure options → run enrichment → show results
 *
 * Supports both questions and variants (DRY - same UI, different API endpoints).
 */
export function EnrichmentModal({
  open,
  onOpenChange,
  testId,
  subjectId,
  target = "questions",
  stats,
  onSuccess,
}: EnrichmentModalProps) {
  const [step, setStep] = useState<ModalStep>("configure");
  const [selection, setSelection] = useState<SelectionMode>("unenriched");
  const [jobId, setJobId] = useState<string | null>(null);
  const [progress, setProgress] = useState({ completed: 0, total: 0, failed: 0 });
  const [results, setResults] = useState<EnrichmentResult[]>([]);
  const [error, setError] = useState<string | null>(null);

  const isVariants = target === "variants";
  const itemLabel = isVariants ? "variants" : "questions";

  // Calculate items to process based on selection
  const itemsToProcess =
    selection === "all"
      ? stats.tagged_count
      : stats.tagged_count - stats.enriched_count;

  // Estimated cost: ~$0.024 per item (GPT 5.1 medium reasoning)
  const estimatedCost = itemsToProcess * 0.024;

  // Reset state when modal opens
  useEffect(() => {
    if (open) {
      setStep("configure");
      setSelection("unenriched");
      setJobId(null);
      setProgress({ completed: 0, total: 0, failed: 0 });
      setResults([]);
      setError(null);
    }
  }, [open]);

  // Poll for progress when running
  const pollProgress = useCallback(
    async (jid: string) => {
      try {
        const data = await getEnrichmentStatus(subjectId, testId, jid);

        setProgress({
          completed: data.progress.completed,
          total: data.progress.total,
          failed: data.progress.failed,
        });

        if (data.status === "completed") {
          setResults(data.results || []);
          setStep("results");
        } else if (data.status !== "pending" && data.status !== "running") {
          setError("Enrichment job failed unexpectedly");
          setStep("results");
        }
      } catch (err) {
        console.error("Failed to poll enrichment status:", err);
      }
    },
    [subjectId, testId]
  );

  useEffect(() => {
    if (step !== "progress" || !jobId) return;

    const interval = setInterval(() => pollProgress(jobId), 2000);
    return () => clearInterval(interval);
  }, [step, jobId, pollProgress]);

  const handleStartEnrichment = async () => {
    setError(null);
    setStep("progress");

    try {
      // DRY: Same logic, different API endpoint based on target
      const response = isVariants
        ? await startVariantEnrichment(subjectId, testId, {
            skip_already_enriched: selection === "unenriched",
          })
        : await startEnrichment(subjectId, testId, {
            all_tagged: selection === "all",
            skip_already_enriched: selection === "unenriched",
          });

      setJobId(response.job_id);
      setProgress({ completed: 0, total: itemsToProcess, failed: 0 });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start enrichment");
      setStep("configure");
    }
  };

  const handleClose = () => {
    if (step === "progress") return; // Don't allow closing while running

    if (step === "results" && onSuccess) {
      onSuccess();
    }
    onOpenChange(false);
  };

  // Handle escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape" && step !== "progress") {
        handleClose();
      }
    };
    if (open) {
      document.addEventListener("keydown", handleEscape);
      return () => document.removeEventListener("keydown", handleEscape);
    }
  }, [open, step]);

  if (!open) return null;

  const successCount = results.filter((r) => r.status === "success").length;
  const failedCount = results.filter((r) => r.status === "failed").length;
  const progressPercent =
    progress.total > 0 ? Math.round((progress.completed / progress.total) * 100) : 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={step !== "progress" ? handleClose : undefined}
      />

      {/* Modal */}
      <div className="relative w-full max-w-md bg-surface border border-border rounded-xl shadow-xl mx-4">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div>
            <h2 className="font-semibold">
              {step === "configure" && "Enrich Questions with Feedback"}
              {step === "progress" && "Enriching Questions..."}
              {step === "results" && "Enrichment Complete"}
            </h2>
          </div>
          {step !== "progress" && (
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
          {/* Configure step */}
          {step === "configure" && (
            <div className="space-y-4">
              <p className="text-sm text-text-secondary">
                This will add educational feedback to questions:
              </p>
              <ul className="text-sm list-disc list-inside space-y-1 text-text-secondary">
                <li>Per-choice rationales (why each answer is right/wrong)</li>
                <li>Step-by-step worked solutions</li>
              </ul>

              {/* Selection options */}
              <div className="space-y-2">
                <label className="flex items-center gap-3 p-3 border border-border rounded-lg cursor-pointer hover:bg-white/5">
                  <input
                    type="radio"
                    name="selection"
                    checked={selection === "unenriched"}
                    onChange={() => setSelection("unenriched")}
                    className="w-4 h-4 accent-accent"
                  />
                  <span className="text-sm">
                    Only questions without feedback ({stats.tagged_count - stats.enriched_count})
                  </span>
                </label>
                <label className="flex items-center gap-3 p-3 border border-border rounded-lg cursor-pointer hover:bg-white/5">
                  <input
                    type="radio"
                    name="selection"
                    checked={selection === "all"}
                    onChange={() => setSelection("all")}
                    className="w-4 h-4 accent-accent"
                  />
                  <span className="text-sm">
                    All tagged questions ({stats.tagged_count})
                  </span>
                </label>
              </div>

              {/* Cost estimate */}
              <div className="p-4 bg-background border border-border rounded-lg">
                <h3 className="font-medium text-sm mb-2">Cost Estimate</h3>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div>
                    <p className="text-text-secondary">{isVariants ? "Variants" : "Questions"}</p>
                    <p className="font-mono">{itemsToProcess}</p>
                  </div>
                  <div>
                    <p className="text-text-secondary">Estimated Cost</p>
                    <p className="font-mono text-warning">~${estimatedCost.toFixed(2)}</p>
                  </div>
                </div>
                <p className="text-xs text-text-secondary mt-2">Model: GPT 5.1 (medium reasoning)</p>
              </div>

              {itemsToProcess === 0 && (
                <div className="flex items-center gap-2 p-3 bg-warning/10 border border-warning/20 rounded-lg">
                  <AlertTriangle className="w-4 h-4 text-warning flex-shrink-0" />
                  <p className="text-sm text-warning">
                    All tagged questions already have feedback.
                  </p>
                </div>
              )}

              {error && (
                <div className="flex items-center gap-2 p-3 bg-error/10 border border-error/20 rounded-lg">
                  <XCircle className="w-4 h-4 text-error flex-shrink-0" />
                  <p className="text-sm text-error">{error}</p>
                </div>
              )}
            </div>
          )}

          {/* Progress step */}
          {step === "progress" && (
            <div className="space-y-4">
              <div className="flex flex-col items-center py-4">
                <Loader2 className="w-8 h-8 text-accent animate-spin mb-4" />
                <p className="font-medium">Adding feedback to questions...</p>
              </div>

              {/* Progress bar */}
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-text-secondary">Progress</span>
                  <span>
                    {progress.completed} / {progress.total}
                  </span>
                </div>
                <div className="h-2 bg-background rounded-full overflow-hidden">
                  <div
                    className="h-full bg-accent transition-all duration-300"
                    style={{ width: `${progressPercent}%` }}
                  />
                </div>
              </div>

              {progress.failed > 0 && (
                <p className="text-sm text-error">
                  {progress.failed} question(s) failed XSD validation
                </p>
              )}
            </div>
          )}

          {/* Results step */}
          {step === "results" && (
            <div className="space-y-4">
              <div className="flex flex-col items-center py-4">
                {failedCount === 0 ? (
                  <CheckCircle2 className="w-12 h-12 text-success mb-4" />
                ) : (
                  <AlertTriangle className="w-12 h-12 text-warning mb-4" />
                )}
                <p className="font-semibold text-lg">Enrichment Complete</p>
              </div>

              <div className="space-y-2 text-sm">
                <p className="text-success">
                  <CheckCircle2 className="w-4 h-4 inline mr-2" />
                  {successCount} questions enriched successfully
                </p>
                {failedCount > 0 && (
                  <p className="text-error">
                    <XCircle className="w-4 h-4 inline mr-2" />
                    {failedCount} questions failed
                  </p>
                )}
              </div>

              <p className="text-sm text-text-secondary">
                Next step: Run Validation to verify content quality
              </p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-border flex justify-end gap-3">
          {step === "configure" && (
            <>
              <button
                onClick={handleClose}
                className="px-4 py-2 text-sm font-medium hover:bg-white/5 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleStartEnrichment}
                disabled={itemsToProcess === 0}
                className="px-4 py-2 bg-accent text-white rounded-lg text-sm font-medium
                  hover:bg-accent/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Start Enrichment
              </button>
            </>
          )}

          {step === "results" && (
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
