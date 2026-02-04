"use client";

import { useState } from "react";
import { X, Loader2, AlertTriangle, CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";

export interface BulkAction {
  id: string;
  label: string;
  icon?: React.ReactNode;
  variant?: "default" | "primary" | "danger" | "warning";
  disabled?: boolean;
  /** Called when action is triggered. Return true for success, false for failure. */
  onAction: () => Promise<boolean>;
}

export interface BulkActionBarProps {
  /** Number of items selected */
  selectedCount: number;
  /** Total number of items */
  totalCount: number;
  /** Label for the items (e.g., "questions", "variants") */
  itemLabel: string;
  /** Actions to display */
  actions: BulkAction[];
  /** Optional cost estimate to display */
  costEstimate?: {
    min: number;
    max: number;
  };
  /** Called when selection is cleared */
  onClearSelection?: () => void;
  /** Whether the bar is visible */
  visible?: boolean;
  /** Additional class names */
  className?: string;
}

export function BulkActionBar({
  selectedCount,
  totalCount,
  itemLabel,
  actions,
  costEstimate,
  onClearSelection,
  visible = true,
  className,
}: BulkActionBarProps) {
  const [executing, setExecuting] = useState<string | null>(null);
  const [result, setResult] = useState<{ success: boolean; message: string } | null>(null);

  if (!visible || selectedCount === 0) return null;

  const handleAction = async (action: BulkAction) => {
    if (executing || action.disabled) return;

    setExecuting(action.id);
    setResult(null);

    try {
      const success = await action.onAction();
      setResult({
        success,
        message: success
          ? `${action.label} completed successfully`
          : `${action.label} failed`,
      });
    } catch (err) {
      setResult({
        success: false,
        message: err instanceof Error ? err.message : "Action failed",
      });
    } finally {
      setExecuting(null);
    }
  };

  const getVariantStyles = (variant: BulkAction["variant"] = "default") => {
    switch (variant) {
      case "primary":
        return "bg-accent text-white hover:bg-accent/90";
      case "danger":
        return "bg-error text-white hover:bg-error/90";
      case "warning":
        return "bg-warning text-white hover:bg-warning/90";
      default:
        return "bg-surface border border-border hover:bg-white/5";
    }
  };

  return (
    <div
      className={cn(
        "fixed bottom-0 left-0 right-0 z-40",
        "bg-surface/95 backdrop-blur-sm border-t border-border",
        "px-6 py-3 shadow-lg",
        className
      )}
      style={{ animation: "slideUp 200ms ease-out" }}
    >
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        {/* Selection info */}
        <div className="flex items-center gap-4">
          {onClearSelection && (
            <button
              onClick={onClearSelection}
              className="p-1 hover:bg-white/10 rounded"
              title="Clear selection"
            >
              <X className="w-4 h-4 text-text-secondary" />
            </button>
          )}
          <div>
            <span className="font-medium">{selectedCount}</span>
            <span className="text-text-secondary"> of {totalCount} {itemLabel} selected</span>
          </div>
        </div>

        {/* Cost estimate */}
        {costEstimate && (
          <div className="text-sm text-text-secondary">
            Est. cost: ${costEstimate.min.toFixed(2)} - ${costEstimate.max.toFixed(2)}
          </div>
        )}

        {/* Result message */}
        {result && (
          <div
            className={cn(
              "flex items-center gap-2 text-sm",
              result.success ? "text-success" : "text-error"
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
        <div className="flex items-center gap-2">
          {actions.map((action) => (
            <button
              key={action.id}
              onClick={() => handleAction(action)}
              disabled={executing !== null || action.disabled}
              className={cn(
                "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors",
                "disabled:opacity-50 disabled:cursor-not-allowed",
                getVariantStyles(action.variant)
              )}
            >
              {executing === action.id ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                action.icon
              )}
              {action.label}
            </button>
          ))}
        </div>
      </div>

      <style jsx>{`
        @keyframes slideUp {
          from {
            opacity: 0;
            transform: translateY(100%);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>
    </div>
  );
}

/**
 * Simple confirmation dialog for bulk actions.
 * Shows a confirmation prompt before executing a destructive action.
 */
export interface ConfirmDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmLabel?: string;
  confirmVariant?: "danger" | "warning" | "primary";
  /** Require checkbox acknowledgment */
  requireAcknowledgment?: boolean;
  acknowledgmentText?: string;
}

export function ConfirmDialog({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmLabel = "Confirm",
  confirmVariant = "danger",
  requireAcknowledgment = false,
  acknowledgmentText = "I understand this action cannot be undone",
}: ConfirmDialogProps) {
  const [acknowledged, setAcknowledged] = useState(false);

  if (!isOpen) return null;

  const canConfirm = !requireAcknowledgment || acknowledged;

  const handleConfirm = () => {
    if (canConfirm) {
      onConfirm();
      setAcknowledged(false);
    }
  };

  const handleClose = () => {
    setAcknowledged(false);
    onClose();
  };

  const getButtonStyles = () => {
    switch (confirmVariant) {
      case "danger":
        return "bg-error text-white hover:bg-error/90";
      case "warning":
        return "bg-warning text-white hover:bg-warning/90";
      default:
        return "bg-accent text-white hover:bg-accent/90";
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60" onClick={handleClose} />

      {/* Dialog */}
      <div className="relative bg-surface border border-border rounded-lg p-6 max-w-md w-full mx-4 shadow-xl">
        <button
          onClick={handleClose}
          className="absolute top-4 right-4 text-text-secondary hover:text-text-primary"
        >
          <X className="w-5 h-5" />
        </button>

        <h2 className="text-lg font-semibold mb-2">{title}</h2>
        <p className="text-sm text-text-secondary mb-4">{message}</p>

        {requireAcknowledgment && (
          <label className="flex items-center gap-2 mb-4 cursor-pointer">
            <input
              type="checkbox"
              checked={acknowledged}
              onChange={(e) => setAcknowledged(e.target.checked)}
              className="w-4 h-4 rounded border-border"
            />
            <span className="text-sm text-text-secondary">{acknowledgmentText}</span>
          </label>
        )}

        <div className="flex gap-3 justify-end">
          <button
            onClick={handleClose}
            className="px-4 py-2 text-sm font-medium rounded-lg border border-border hover:bg-white/5"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={!canConfirm}
            className={cn(
              "px-4 py-2 text-sm font-medium rounded-lg disabled:opacity-50",
              getButtonStyles()
            )}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
