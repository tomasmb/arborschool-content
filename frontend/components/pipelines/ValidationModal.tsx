"use client";

import { useState, useEffect, useCallback } from "react";
import { X, Loader2, CheckCircle2, XCircle, AlertTriangle, Download } from "lucide-react";
import {
  startValidation,
  startVariantValidation,
  getValidationStatus,
  type ValidationResult,
} from "@/lib/api";

type ModalStep = "configure" | "progress" | "results";
type SelectionMode = "unvalidated" | "all" | "revalidate";
type ValidationTarget = "questions" | "variants";

interface ValidationModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  testId: string;
  subjectId: string;
  /** Target type - questions or variants. Defaults to questions. */
  target?: ValidationTarget;
  stats: {
    enriched_count: number;
    validated_count: number;
  };
  onSuccess?: () => void;
}

/**
 * Modal for running final validation on enriched questions or variants.
 * Flow: configure options → run validation → show results with export option
 *
 * Supports both questions and variants (DRY - same UI, different API endpoints).
 */
export function ValidationModal({
  open,
  onOpenChange,
  testId,
  subjectId,
  target = "questions",
  stats,
  onSuccess,
}: ValidationModalProps) {
  const [step, setStep] = useState<ModalStep>("configure");
  const [selection, setSelection] = useState<SelectionMode>("unvalidated");
  const [jobId, setJobId] = useState<string | null>(null);
  const [progress, setProgress] = useState({
    completed: 0,
    total: 0,
    passed: 0,
    failed: 0,
  });
  const [results, setResults] = useState<ValidationResult[]>([]);
  const [error, setError] = useState<string | null>(null);

  const isVariants = target === "variants";
  const itemLabel = isVariants ? "variants" : "questions";

  // Calculate items to validate based on selection
  const itemsToValidate =
    selection === "unvalidated"
      ? stats.enriched_count - stats.validated_count
      : stats.enriched_count;

  // Estimated cost: ~$0.015 per item (GPT 5.1 high reasoning)
  const estimatedCost = itemsToValidate * 0.015;

  // Reset state when modal opens
  useEffect(() => {
    if (open) {
      setStep("configure");
      setSelection("unvalidated");
      setJobId(null);
      setProgress({ completed: 0, total: 0, passed: 0, failed: 0 });
      setResults([]);
      setError(null);
    }
  }, [open]);

  // Poll for progress when running
  const pollProgress = useCallback(
    async (jid: string) => {
      try {
        const data = await getValidationStatus(subjectId, testId, jid);

        setProgress({
          completed: data.progress.completed,
          total: data.progress.total,
          passed: data.progress.passed,
          failed: data.progress.failed,
        });

        if (data.status === "completed") {
          setResults(data.results || []);
          setStep("results");
        } else if (data.status === "failed") {
          // Only treat explicit "failed" status as an error
          setError("Validation job failed unexpectedly");
          setStep("results");
        }
        // "started" and "in_progress" continue polling
      } catch (err) {
        console.error("Failed to poll validation status:", err);
      }
    },
    [subjectId, testId]
  );

  useEffect(() => {
    if (step !== "progress" || !jobId) return;

    const interval = setInterval(() => pollProgress(jobId), 2000);
    return () => clearInterval(interval);
  }, [step, jobId, pollProgress]);

  const handleStartValidation = async () => {
    setError(null);
    setStep("progress");

    try {
      // DRY: Same logic, different API endpoint based on target
      const response = isVariants
        ? await startVariantValidation(subjectId, testId, {
            revalidate_passed: selection === "revalidate",
          })
        : await startValidation(subjectId, testId, {
            all_enriched: selection === "all" || selection === "revalidate",
            revalidate_passed: selection === "revalidate",
          });

      setJobId(response.job_id);
      setProgress({ completed: 0, total: itemsToValidate, passed: 0, failed: 0 });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start validation");
      setStep("configure");
    }
  };

  const handleExportReport = () => {
    const failedResults = results.filter((r) => r.status === "fail");
    const report = {
      test_id: testId,
      subject_id: subjectId,
      timestamp: new Date().toISOString(),
      summary: {
        total: results.length,
        passed: progress.passed,
        failed: progress.failed,
      },
      failed_questions: failedResults,
    };

    const blob = new Blob([JSON.stringify(report, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `validation-report-${testId}.json`;
    a.click();
    URL.revokeObjectURL(url);
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

  const failedResults = results.filter((r) => r.status === "fail");
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
              {step === "configure" && "Validate Questions"}
              {step === "progress" && "Validating Questions..."}
              {step === "results" && "Validation Complete"}
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
                Final validation checks:
              </p>
              <ul className="text-sm list-disc list-inside space-y-1 text-text-secondary">
                <li>Correct answer is mathematically correct</li>
                <li>Feedback accurately explains right/wrong</li>
                <li>No typos or character issues</li>
                <li>Images align with question stem</li>
              </ul>

              {/* Selection options */}
              <div className="space-y-2">
                <label className="flex items-center gap-3 p-3 border border-border rounded-lg cursor-pointer hover:bg-white/5">
                  <input
                    type="radio"
                    name="validation-selection"
                    checked={selection === "unvalidated"}
                    onChange={() => setSelection("unvalidated")}
                    className="w-4 h-4 accent-accent"
                  />
                  <span className="text-sm">
                    Only unvalidated questions ({stats.enriched_count - stats.validated_count})
                  </span>
                </label>
                <label className="flex items-center gap-3 p-3 border border-border rounded-lg cursor-pointer hover:bg-white/5">
                  <input
                    type="radio"
                    name="validation-selection"
                    checked={selection === "all"}
                    onChange={() => setSelection("all")}
                    className="w-4 h-4 accent-accent"
                  />
                  <span className="text-sm">
                    All enriched questions ({stats.enriched_count})
                  </span>
                </label>
                <label className="flex items-center gap-3 p-3 border border-border rounded-lg cursor-pointer hover:bg-white/5">
                  <input
                    type="radio"
                    name="validation-selection"
                    checked={selection === "revalidate"}
                    onChange={() => setSelection("revalidate")}
                    className="w-4 h-4 accent-accent"
                  />
                  <span className="text-sm">Re-validate all (including passed)</span>
                </label>
              </div>

              {/* Cost estimate */}
              <div className="p-4 bg-background border border-border rounded-lg">
                <h3 className="font-medium text-sm mb-2">Cost Estimate</h3>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div>
                    <p className="text-text-secondary">{isVariants ? "Variants" : "Questions"}</p>
                    <p className="font-mono">{itemsToValidate}</p>
                  </div>
                  <div>
                    <p className="text-text-secondary">Estimated Cost</p>
                    <p className="font-mono text-warning">~${estimatedCost.toFixed(2)}</p>
                  </div>
                </div>
                <p className="text-xs text-text-secondary mt-2">Model: GPT 5.1 (high reasoning)</p>
              </div>

              {itemsToValidate === 0 && (
                <div className="flex items-center gap-2 p-3 bg-warning/10 border border-warning/20 rounded-lg">
                  <AlertTriangle className="w-4 h-4 text-warning flex-shrink-0" />
                  <p className="text-sm text-warning">
                    No questions to validate with current selection.
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
                <p className="font-medium">Validating questions...</p>
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

              <div className="flex gap-4 text-sm">
                <span className="text-success">
                  <CheckCircle2 className="w-4 h-4 inline mr-1" />
                  {progress.passed} passed
                </span>
                <span className="text-error">
                  <XCircle className="w-4 h-4 inline mr-1" />
                  {progress.failed} failed
                </span>
              </div>
            </div>
          )}

          {/* Results step */}
          {step === "results" && (
            <div className="space-y-4">
              <div className="flex gap-4 justify-center py-4">
                <div className="flex items-center gap-2 text-success">
                  <CheckCircle2 className="w-6 h-6" />
                  <span className="text-lg font-semibold">{progress.passed} passed</span>
                </div>
                <div className="flex items-center gap-2 text-error">
                  <XCircle className="w-6 h-6" />
                  <span className="text-lg font-semibold">{progress.failed} failed</span>
                </div>
              </div>

              {/* Failed questions list */}
              {failedResults.length > 0 && (
                <div className="max-h-48 overflow-y-auto border border-border rounded-lg">
                  {failedResults.map((r, i) => (
                    <div
                      key={i}
                      className="p-3 border-b border-border last:border-b-0"
                    >
                      <p className="font-medium text-sm">{r.question_id}</p>
                      <p className="text-xs text-text-secondary">
                        Failed: {r.failed_checks?.join(", ")}
                      </p>
                      {r.issues?.[0] && (
                        <p className="text-xs text-error mt-1">{r.issues[0]}</p>
                      )}
                    </div>
                  ))}
                </div>
              )}

              <p className="text-sm text-text-secondary">
                {progress.passed} questions ready to sync to database
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
                onClick={handleStartValidation}
                disabled={itemsToValidate === 0}
                className="px-4 py-2 bg-accent text-white rounded-lg text-sm font-medium
                  hover:bg-accent/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Start Validation
              </button>
            </>
          )}

          {step === "results" && (
            <>
              {failedResults.length > 0 && (
                <button
                  onClick={handleExportReport}
                  className="flex items-center gap-2 px-4 py-2 text-sm font-medium hover:bg-white/5 rounded-lg transition-colors"
                >
                  <Download className="w-4 h-4" />
                  Export Report
                </button>
              )}
              <button
                onClick={handleClose}
                className="px-4 py-2 bg-accent text-white rounded-lg text-sm font-medium hover:bg-accent/90 transition-colors"
              >
                Close
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
