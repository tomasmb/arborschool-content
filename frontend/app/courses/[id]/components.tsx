"use client";

import { useState } from "react";
import Link from "next/link";
import {
  CheckCircle2,
  Circle,
  Play,
  RefreshCw,
  AlertTriangle,
  Lock,
  X,
  Loader2,
} from "lucide-react";
import { clearPipelineOutputs } from "@/lib/api";

// -----------------------------------------------------------------------------
// Pipeline Card Component
// -----------------------------------------------------------------------------

export interface PipelineCardProps {
  step: number;
  title: string;
  done: boolean;
  description: string;
  detail?: string | null;
  canGenerate?: boolean;
  canRegenerate?: boolean;
  isBlocked?: boolean;
  blockedReason?: string;
  onGenerate?: () => void;
  onRegenerate?: () => void;
  linkHref?: string;
  linkText?: string;
  children?: React.ReactNode;
}

export function PipelineCard({
  step,
  title,
  done,
  description,
  detail,
  canGenerate,
  canRegenerate,
  isBlocked,
  blockedReason,
  onGenerate,
  onRegenerate,
  linkHref,
  linkText,
  children,
}: PipelineCardProps) {
  return (
    <div className="bg-surface border border-border rounded-lg p-4">
      <div className="flex items-center gap-3 mb-3">
        {done ? (
          <CheckCircle2 className="w-5 h-5 text-success" />
        ) : (
          <Circle className="w-5 h-5 text-text-secondary" />
        )}
        <h3 className="font-medium">
          {step}. {title}
        </h3>
      </div>

      <p className="text-text-secondary text-sm mb-3">{description}</p>

      {detail && (
        <p className="text-xs text-text-secondary font-mono truncate mb-3">
          {detail}
        </p>
      )}

      {children}

      {/* Action buttons */}
      <div className="mt-4 flex items-center gap-2">
        {canGenerate && onGenerate && (
          <button
            onClick={onGenerate}
            className={[
              "flex items-center gap-2 px-3 py-1.5 bg-accent text-white rounded",
              "text-sm font-medium hover:bg-accent/90 transition-colors",
            ].join(" ")}
          >
            <Play className="w-3 h-3" />
            Generate
          </button>
        )}

        {canRegenerate && onRegenerate && (
          <button
            onClick={onRegenerate}
            className={[
              "flex items-center gap-2 px-3 py-1.5 bg-warning/10 text-warning rounded",
              "text-sm font-medium hover:bg-warning/20 transition-colors border border-warning/20",
            ].join(" ")}
          >
            <RefreshCw className="w-3 h-3" />
            Regenerate
          </button>
        )}

        {isBlocked && !done && (
          <span className="flex items-center gap-1.5 text-xs text-text-secondary">
            <Lock className="w-3 h-3" />
            {blockedReason}
          </span>
        )}

        {linkHref && linkText && (
          <Link href={linkHref} className="text-accent text-sm hover:underline">
            {linkText}
          </Link>
        )}
      </div>
    </div>
  );
}

// -----------------------------------------------------------------------------
// Sync Item Component
// -----------------------------------------------------------------------------

export interface SyncItemProps {
  label: string;
  count: number;
  status: "synced" | "pending" | "empty" | "warning";
  warning?: string;
}

export function SyncItem({ label, count, status, warning }: SyncItemProps) {
  const getStatusIcon = () => {
    switch (status) {
      case "synced":
        return <CheckCircle2 className="w-4 h-4 text-success" />;
      case "pending":
        return <RefreshCw className="w-4 h-4 text-warning" />;
      case "warning":
        return <AlertTriangle className="w-4 h-4 text-warning" />;
      default:
        return <Circle className="w-4 h-4 text-text-secondary" />;
    }
  };

  return (
    <div className="flex items-center gap-2">
      {getStatusIcon()}
      <div>
        <p className="text-sm font-medium">{label}</p>
        {warning ? (
          <p className="text-xs text-warning">{warning}</p>
        ) : (
          <p className="text-xs text-text-secondary">{count} items</p>
        )}
      </div>
    </div>
  );
}

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
