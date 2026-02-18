"use client";

import type { BatchGenOptions } from "./GenerationTab";

/**
 * Dropdown menu for choosing batch generation configuration.
 * Shown when the "Batch Generate" button is clicked.
 */
export function BatchGenMenu({
  onSelect,
  onClose,
}: {
  onSelect: (options: BatchGenOptions) => void;
  onClose: () => void;
}) {
  return (
    <div className="absolute right-0 mt-1 w-64 bg-surface border border-border rounded-lg shadow-lg z-10">
      <div className="px-4 py-2 border-b border-border">
        <p className="text-xs font-semibold text-text-secondary uppercase tracking-wide">
          Batch Generate All Atoms
        </p>
      </div>
      <button
        onClick={() => onSelect({ mode: "pending_only", skip_images: "true" })}
        className="w-full px-4 py-2.5 text-left text-sm hover:bg-white/5"
      >
        <div className="font-medium">Pending only (no images)</div>
        <div className="text-xs text-text-secondary mt-0.5">
          Skip already-generated atoms and image gen
        </div>
      </button>
      <button
        onClick={() => onSelect({ mode: "pending_only", skip_images: "false" })}
        className="w-full px-4 py-2.5 text-left text-sm hover:bg-white/5"
      >
        <div className="font-medium">Pending only (with images)</div>
        <div className="text-xs text-text-secondary mt-0.5">
          Skip already-generated atoms, include images
        </div>
      </button>
      <button
        onClick={() => onSelect({ mode: "all", skip_images: "true" })}
        className="w-full px-4 py-2.5 text-left text-sm hover:bg-white/5 text-warning rounded-b-lg"
      >
        <div className="font-medium">Re-run all (no images)</div>
        <div className="text-xs text-text-secondary mt-0.5">
          Regenerate every covered atom, skip images
        </div>
      </button>
    </div>
  );
}
