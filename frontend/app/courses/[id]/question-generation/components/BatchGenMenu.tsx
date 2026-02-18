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
        <div className="font-medium">Pending — no-image atoms only</div>
        <div className="text-xs text-text-secondary mt-0.5">
          Only atoms that don&apos;t require images, skip already-generated
        </div>
      </button>
      <button
        onClick={() => onSelect({ mode: "pending_only", skip_images: "false" })}
        className="w-full px-4 py-2.5 text-left text-sm hover:bg-white/5"
      >
        <div className="font-medium">Pending — all atoms</div>
        <div className="text-xs text-text-secondary mt-0.5">
          All pending atoms including those with images
        </div>
      </button>
      <button
        onClick={() => onSelect({ mode: "all", skip_images: "true" })}
        className="w-full px-4 py-2.5 text-left text-sm hover:bg-white/5 text-warning rounded-b-lg"
      >
        <div className="font-medium">Re-run all — no-image atoms only</div>
        <div className="text-xs text-text-secondary mt-0.5">
          Re-generate all atoms that don&apos;t require images
        </div>
      </button>
    </div>
  );
}
