"use client";

import { useState } from "react";
import { Sparkles } from "lucide-react";

interface VariantOptionsDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (count: number) => void;
  existingCount: number;
}

/**
 * Dialog for configuring variant generation options.
 * Shows that variants are additive and allows specifying count.
 */
export function VariantOptionsDialog({
  isOpen,
  onClose,
  onConfirm,
  existingCount,
}: VariantOptionsDialogProps) {
  const [count, setCount] = useState(3);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />
      <div className="relative w-full max-w-sm bg-surface border border-border rounded-xl shadow-xl mx-4 p-6">
        <h2 className="font-semibold text-lg mb-2">Generate Variants</h2>
        <p className="text-sm text-text-secondary mb-4">
          New variants will be{" "}
          <span className="text-success font-medium">added</span> to existing
          ones.
          {existingCount > 0 && (
            <span className="block mt-1">
              Currently: {existingCount} variant{existingCount !== 1 ? "s" : ""}
            </span>
          )}
        </p>

        <div className="mb-6">
          <label className="block text-sm font-medium mb-2">
            Variants per question
          </label>
          <input
            type="number"
            min={1}
            max={10}
            value={count}
            onChange={(e) =>
              setCount(Math.max(1, Math.min(10, parseInt(e.target.value) || 1)))
            }
            className="w-full px-3 py-2 bg-background border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent"
          />
          <p className="text-xs text-text-secondary mt-1">
            1-10 variants per question
          </p>
        </div>

        <div className="flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium hover:bg-white/5 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={() => onConfirm(count)}
            className="flex items-center gap-2 px-4 py-2 bg-accent text-white rounded-lg text-sm font-medium hover:bg-accent/90 transition-colors"
          >
            <Sparkles className="w-4 h-4" />
            Continue
          </button>
        </div>
      </div>
    </div>
  );
}
