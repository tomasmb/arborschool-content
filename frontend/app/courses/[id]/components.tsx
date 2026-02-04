"use client";

import { useState } from "react";
import { RefreshCw, AlertTriangle, X, Loader2 } from "lucide-react";
import { clearPipelineOutputs } from "@/lib/api";

// -----------------------------------------------------------------------------
// Regenerate Dialog Component
// -----------------------------------------------------------------------------

export interface RegenerateDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  pipelineId: string;
  pipelineName: string;
  itemCount: number;
  itemLabel: string;
  subjectId?: string;
  testId?: string;
}

export function RegenerateDialog({
  isOpen,
  onClose,
  onConfirm,
  pipelineId,
  pipelineName,
  itemCount,
  itemLabel,
  subjectId,
  testId,
}: RegenerateDialogProps) {
  const [clearing, setClearing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleConfirm = async () => {
    setClearing(true);
    setError(null);
    try {
      await clearPipelineOutputs(pipelineId, { subject_id: subjectId, test_id: testId });
      onConfirm();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to clear outputs");
    } finally {
      setClearing(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />

      {/* Dialog */}
      <div className="relative bg-surface border border-border rounded-lg p-6 max-w-md w-full mx-4 shadow-xl">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-text-secondary hover:text-text-primary"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-3 mb-4">
          <AlertTriangle className="w-6 h-6 text-warning" />
          <h2 className="text-lg font-semibold">Regenerate {pipelineName}?</h2>
        </div>

        <div className="mb-4">
          <p className="text-sm text-text-secondary mb-2">This will DELETE:</p>
          <div className="bg-error/10 border border-error/20 rounded-lg p-3">
            <p className="text-sm text-error">
              {itemCount} existing {itemLabel}
            </p>
          </div>
        </div>

        <p className="text-sm text-text-secondary mb-4">
          Then generate new {itemLabel.toLowerCase()} from the current data.
          This action cannot be undone.
        </p>

        {error && (
          <div className="bg-error/10 border border-error/20 rounded-lg p-3 mb-4">
            <p className="text-sm text-error">{error}</p>
          </div>
        )}

        <div className="flex gap-3 justify-end">
          <button
            onClick={onClose}
            disabled={clearing}
            className="px-4 py-2 text-sm font-medium rounded-lg border border-border hover:bg-white/5"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={clearing}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-error text-white hover:bg-error/90 disabled:opacity-50"
          >
            {clearing ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <RefreshCw className="w-4 h-4" />
            )}
            Delete & Regenerate
          </button>
        </div>
      </div>
    </div>
  );
}
