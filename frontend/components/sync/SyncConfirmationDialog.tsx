"use client";

import { useState } from "react";
import { X, AlertTriangle, Database, Upload, CheckCircle2, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

export interface SyncSummary {
  environment: "local" | "staging" | "prod";
  questions: {
    insert: number;
    update: number;
    delete: number;
  };
  variants: {
    insert: number;
    update: number;
    delete: number;
  };
  images: {
    upload: number;
    skip: number;
  };
}

export interface SyncConfirmationDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => Promise<boolean>;
  summary: SyncSummary;
  testName?: string;
  databaseName?: string;
}

export function SyncConfirmationDialog({
  isOpen,
  onClose,
  onConfirm,
  summary,
  testName,
  databaseName = "arborschool.cl",
}: SyncConfirmationDialogProps) {
  const [acknowledged, setAcknowledged] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [result, setResult] = useState<{ success: boolean; message: string } | null>(null);

  if (!isOpen) return null;

  const isProduction = summary.environment === "prod";
  const totalChanges =
    summary.questions.insert +
    summary.questions.update +
    summary.questions.delete +
    summary.variants.insert +
    summary.variants.update +
    summary.variants.delete;

  const handleConfirm = async () => {
    if (!acknowledged && isProduction) return;

    setExecuting(true);
    setResult(null);

    try {
      const success = await onConfirm();
      setResult({
        success,
        message: success ? "Sync completed successfully!" : "Sync failed",
      });
      if (success) {
        // Auto close after success
        setTimeout(() => {
          handleClose();
        }, 2000);
      }
    } catch (err) {
      setResult({
        success: false,
        message: err instanceof Error ? err.message : "Sync failed",
      });
    } finally {
      setExecuting(false);
    }
  };

  const handleClose = () => {
    setAcknowledged(false);
    setResult(null);
    onClose();
  };

  const envLabel =
    summary.environment === "prod"
      ? "Production"
      : summary.environment === "staging"
        ? "Staging"
        : "Local";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60" onClick={handleClose} />

      {/* Dialog */}
      <div className="relative bg-surface border border-border rounded-lg p-6 max-w-lg w-full mx-4 shadow-xl">
        <button
          onClick={handleClose}
          disabled={executing}
          className="absolute top-4 right-4 text-text-secondary hover:text-text-primary disabled:opacity-50"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Header */}
        <div className="flex items-center gap-3 mb-4">
          {isProduction ? (
            <AlertTriangle className="w-6 h-6 text-error" />
          ) : (
            <Database className="w-6 h-6 text-accent" />
          )}
          <h2 className="text-lg font-semibold">
            Confirm Sync to {envLabel}
          </h2>
        </div>

        {/* Warning for production */}
        {isProduction && (
          <div className="mb-4 p-3 bg-error/10 border border-error/20 rounded-lg">
            <p className="text-sm text-error flex items-center gap-2">
              <AlertTriangle className="w-4 h-4" />
              You are about to sync to PRODUCTION database
            </p>
          </div>
        )}

        {/* Summary */}
        <div className="mb-4 space-y-3">
          <p className="text-sm text-text-secondary">This sync will:</p>

          {/* Questions */}
          <div className="bg-background rounded-lg p-3">
            <p className="text-sm font-medium mb-2">Questions</p>
            <div className="flex flex-wrap gap-3 text-sm">
              {summary.questions.insert > 0 && (
                <span className="text-success">✚ INSERT {summary.questions.insert} new</span>
              )}
              {summary.questions.update > 0 && (
                <span className="text-accent">✎ UPDATE {summary.questions.update} existing</span>
              )}
              {summary.questions.delete > 0 && (
                <span className="text-error">✗ DELETE {summary.questions.delete}</span>
              )}
              {summary.questions.insert === 0 &&
                summary.questions.update === 0 &&
                summary.questions.delete === 0 && (
                  <span className="text-text-secondary">No changes</span>
                )}
            </div>
          </div>

          {/* Variants */}
          <div className="bg-background rounded-lg p-3">
            <p className="text-sm font-medium mb-2">Variants</p>
            <div className="flex flex-wrap gap-3 text-sm">
              {summary.variants.insert > 0 && (
                <span className="text-success">✚ INSERT {summary.variants.insert} new</span>
              )}
              {summary.variants.update > 0 && (
                <span className="text-accent">✎ UPDATE {summary.variants.update} existing</span>
              )}
              {summary.variants.delete > 0 && (
                <span className="text-error">✗ DELETE {summary.variants.delete}</span>
              )}
              {summary.variants.insert === 0 &&
                summary.variants.update === 0 &&
                summary.variants.delete === 0 && (
                  <span className="text-text-secondary">No changes</span>
                )}
            </div>
          </div>

          {/* Images */}
          <div className="bg-background rounded-lg p-3">
            <p className="text-sm font-medium mb-2">Images</p>
            <div className="flex flex-wrap gap-3 text-sm">
              {summary.images.upload > 0 && (
                <span className="text-success">✚ UPLOAD {summary.images.upload} to S3</span>
              )}
              {summary.images.skip > 0 && (
                <span className="text-text-secondary">○ SKIP {summary.images.skip} (existing)</span>
              )}
            </div>
          </div>

          {/* Database info */}
          <div className="text-sm text-text-secondary">
            <span className="font-medium">Database:</span> {databaseName}
            {testName && (
              <>
                <br />
                <span className="font-medium">Test:</span> {testName}
              </>
            )}
          </div>
        </div>

        {/* Acknowledgment for production */}
        {isProduction && (
          <label className="flex items-start gap-2 mb-4 cursor-pointer">
            <input
              type="checkbox"
              checked={acknowledged}
              onChange={(e) => setAcknowledged(e.target.checked)}
              disabled={executing}
              className="w-4 h-4 rounded border-border mt-0.5"
            />
            <span className="text-sm text-text-secondary">
              I understand this will overwrite production data and cannot be undone
            </span>
          </label>
        )}

        {/* Result message */}
        {result && (
          <div
            className={cn(
              "mb-4 p-3 rounded-lg flex items-center gap-2 text-sm",
              result.success
                ? "bg-success/10 text-success border border-success/20"
                : "bg-error/10 text-error border border-error/20"
            )}
          >
            {result.success ? (
              <CheckCircle2 className="w-4 h-4" />
            ) : (
              <AlertTriangle className="w-4 h-4" />
            )}
            {result.message}
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-3 justify-end">
          <button
            onClick={handleClose}
            disabled={executing}
            className="px-4 py-2 text-sm font-medium rounded-lg border border-border hover:bg-white/5 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={(isProduction && !acknowledged) || executing}
            className={cn(
              "flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg disabled:opacity-50",
              isProduction
                ? "bg-error text-white hover:bg-error/90"
                : "bg-accent text-white hover:bg-accent/90"
            )}
          >
            {executing ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Upload className="w-4 h-4" />
            )}
            {executing ? "Syncing..." : `Sync to ${envLabel}`}
          </button>
        </div>
      </div>
    </div>
  );
}
