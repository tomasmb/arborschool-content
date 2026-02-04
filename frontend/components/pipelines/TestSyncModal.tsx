"use client";

import { useState, useEffect } from "react";
import {
  X,
  Loader2,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Plus,
  Pencil,
  Minus,
} from "lucide-react";
import {
  getTestSyncPreview,
  executeTestSync,
  type TestSyncPreview,
  type TestSyncResult,
} from "@/lib/api";

type ModalStep = "loading" | "preview" | "syncing" | "complete";

interface TestSyncModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  testId: string;
  subjectId: string;
  stats: {
    validated_count: number;
    total: number;
  };
  onSuccess?: () => void;
}

/**
 * Modal for syncing validated questions to the production database.
 * Flow: load preview → confirm options → sync → show results
 */
export function TestSyncModal({
  open,
  onOpenChange,
  testId,
  subjectId,
  stats,
  onSuccess,
}: TestSyncModalProps) {
  const [step, setStep] = useState<ModalStep>("loading");
  const [preview, setPreview] = useState<TestSyncPreview | null>(null);
  const [syncResult, setSyncResult] = useState<TestSyncResult | null>(null);
  const [includeVariants, setIncludeVariants] = useState(true);
  const [uploadImages, setUploadImages] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const canSync = stats.validated_count > 0;

  // Load preview when modal opens
  useEffect(() => {
    if (open && canSync) {
      loadPreview();
    } else if (open) {
      setStep("preview");
    }
  }, [open, canSync]);

  // Reset state when modal closes
  useEffect(() => {
    if (!open) {
      setStep("loading");
      setPreview(null);
      setSyncResult(null);
      setError(null);
    }
  }, [open]);

  const loadPreview = async () => {
    setStep("loading");
    setError(null);

    try {
      const data = await getTestSyncPreview(subjectId, testId, {
        include_variants: includeVariants,
        upload_images: uploadImages,
      });
      setPreview(data);
      setStep("preview");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load preview");
      setStep("preview");
    }
  };

  const handleExecuteSync = async () => {
    setStep("syncing");
    setError(null);

    try {
      const result = await executeTestSync(subjectId, testId, {
        include_variants: includeVariants,
        upload_images: uploadImages,
      });
      setSyncResult(result);
      setStep("complete");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sync failed");
      setStep("preview");
    }
  };

  const handleClose = () => {
    if (step === "syncing") return; // Don't allow closing while syncing

    if (step === "complete" && onSuccess) {
      onSuccess();
    }
    onOpenChange(false);
  };

  // Handle escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape" && step !== "syncing") {
        handleClose();
      }
    };
    if (open) {
      document.addEventListener("keydown", handleEscape);
      return () => document.removeEventListener("keydown", handleEscape);
    }
  }, [open, step]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={step !== "syncing" ? handleClose : undefined}
      />

      {/* Modal */}
      <div className="relative w-full max-w-md bg-surface border border-border rounded-xl shadow-xl mx-4">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <h2 className="font-semibold">Sync Test to Database</h2>
          {step !== "syncing" && (
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
          {/* Cannot sync - no validated questions */}
          {!canSync && (
            <div className="space-y-4">
              <div className="flex items-center gap-3 p-4 bg-error/10 border border-error/20 rounded-lg">
                <AlertTriangle className="w-5 h-5 text-error flex-shrink-0" />
                <div>
                  <p className="font-medium text-error">Cannot sync</p>
                  <p className="text-sm text-error/80">No validated questions</p>
                </div>
              </div>

              <p className="text-sm text-text-secondary">
                To sync questions, you must:
              </p>
              <ol className="text-sm list-decimal list-inside space-y-1 text-text-secondary">
                <li>Tag questions with atoms</li>
                <li>Run "Enrich Feedback" to add educational content</li>
                <li>Run "Validate" to verify quality</li>
              </ol>
            </div>
          )}

          {/* Loading state */}
          {canSync && step === "loading" && (
            <div className="flex flex-col items-center py-8">
              <Loader2 className="w-8 h-8 text-accent animate-spin mb-4" />
              <p className="text-text-secondary">Loading sync preview...</p>
            </div>
          )}

          {/* Preview state */}
          {canSync && step === "preview" && (
            <div className="space-y-4">
              {error && (
                <div className="flex items-center gap-2 p-3 bg-error/10 border border-error/20 rounded-lg">
                  <XCircle className="w-4 h-4 text-error flex-shrink-0" />
                  <p className="text-sm text-error">{error}</p>
                </div>
              )}

              {preview && (
                <>
                  {/* Summary grid */}
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div className="flex items-center gap-2 p-3 bg-success/10 rounded-lg">
                      <Plus className="w-4 h-4 text-success" />
                      <span>Create: {preview.summary.create}</span>
                    </div>
                    <div className="flex items-center gap-2 p-3 bg-accent/10 rounded-lg">
                      <Pencil className="w-4 h-4 text-accent" />
                      <span>Update: {preview.summary.update}</span>
                    </div>
                    <div className="flex items-center gap-2 p-3 bg-white/5 rounded-lg">
                      <Minus className="w-4 h-4 text-text-secondary" />
                      <span>Unchanged: {preview.summary.unchanged}</span>
                    </div>
                    <div className="flex items-center gap-2 p-3 bg-warning/10 rounded-lg">
                      <AlertTriangle className="w-4 h-4 text-warning" />
                      <span>Skipped: {preview.summary.skipped}</span>
                    </div>
                  </div>

                  {/* Warnings */}
                  {preview.summary.skipped > 0 && (
                    <div className="flex items-center gap-2 p-3 bg-warning/10 border border-warning/20 rounded-lg">
                      <AlertTriangle className="w-4 h-4 text-warning flex-shrink-0" />
                      <p className="text-sm text-warning">
                        {preview.summary.skipped} questions will be skipped (not validated)
                      </p>
                    </div>
                  )}

                  {preview.summary.update > 0 && (
                    <p className="text-sm text-text-secondary">
                      <AlertTriangle className="w-4 h-4 inline mr-1 text-warning" />
                      {preview.summary.update} questions will be overwritten in database.
                    </p>
                  )}

                  {/* Options */}
                  <div className="space-y-2 border-t border-border pt-4">
                    <label className="flex items-center gap-3 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={includeVariants}
                        onChange={(e) => setIncludeVariants(e.target.checked)}
                        className="w-4 h-4 accent-accent rounded"
                      />
                      <span className="text-sm">Include approved variants</span>
                    </label>
                    <label className="flex items-center gap-3 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={uploadImages}
                        onChange={(e) => setUploadImages(e.target.checked)}
                        className="w-4 h-4 accent-accent rounded"
                      />
                      <span className="text-sm">Upload images to S3 first</span>
                    </label>
                  </div>
                </>
              )}
            </div>
          )}

          {/* Syncing state */}
          {step === "syncing" && (
            <div className="flex flex-col items-center py-8">
              <Loader2 className="w-8 h-8 text-accent animate-spin mb-4" />
              <p className="font-medium">Syncing to database...</p>
              <p className="text-sm text-text-secondary mt-1">
                This may take a moment
              </p>
            </div>
          )}

          {/* Complete state */}
          {step === "complete" && syncResult && (
            <div className="space-y-4">
              <div className="flex flex-col items-center py-4">
                {syncResult.success ? (
                  <CheckCircle2 className="w-12 h-12 text-success mb-4" />
                ) : (
                  <XCircle className="w-12 h-12 text-error mb-4" />
                )}
                <p className="font-semibold text-lg">
                  {syncResult.success ? "Sync Complete!" : "Sync Failed"}
                </p>
              </div>

              {syncResult.success && (
                <div className="grid grid-cols-3 gap-2 text-sm text-center">
                  <div className="p-3 bg-success/10 rounded-lg">
                    <p className="font-semibold text-success">{syncResult.created}</p>
                    <p className="text-text-secondary">Created</p>
                  </div>
                  <div className="p-3 bg-accent/10 rounded-lg">
                    <p className="font-semibold text-accent">{syncResult.updated}</p>
                    <p className="text-text-secondary">Updated</p>
                  </div>
                  <div className="p-3 bg-warning/10 rounded-lg">
                    <p className="font-semibold text-warning">{syncResult.skipped}</p>
                    <p className="text-text-secondary">Skipped</p>
                  </div>
                </div>
              )}

              {syncResult.errors.length > 0 && (
                <div className="max-h-32 overflow-y-auto border border-error/20 rounded-lg p-3">
                  {syncResult.errors.map((err, i) => (
                    <p key={i} className="text-sm text-error">
                      {err}
                    </p>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-border flex justify-end gap-3">
          {!canSync && (
            <button
              onClick={handleClose}
              className="px-4 py-2 bg-accent text-white rounded-lg text-sm font-medium hover:bg-accent/90 transition-colors"
            >
              Close
            </button>
          )}

          {canSync && step === "preview" && preview && (
            <>
              <button
                onClick={handleClose}
                className="px-4 py-2 text-sm font-medium hover:bg-white/5 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleExecuteSync}
                disabled={preview.summary.create + preview.summary.update === 0}
                className="px-4 py-2 bg-accent text-white rounded-lg text-sm font-medium
                  hover:bg-accent/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Sync {preview.summary.create + preview.summary.update} Questions
              </button>
            </>
          )}

          {step === "complete" && (
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
