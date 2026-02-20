"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import type { BatchGenOptions } from "./GenerationTab";

/**
 * Dropdown menu for choosing batch generation configuration.
 * Includes Batch API toggle (50% discount) and optional atom limit.
 */
export function BatchGenMenu({
  onSelect,
  onClose,
}: {
  onSelect: (options: BatchGenOptions) => void;
  onClose: () => void;
}) {
  const [useBatchApi, setUseBatchApi] = useState(false);
  const [maxAtoms, setMaxAtoms] = useState("");

  const buildOpts = (
    mode: string, skipImages: string,
  ): BatchGenOptions => ({
    mode,
    skip_images: skipImages,
    use_batch_api: useBatchApi,
    ...(maxAtoms ? { max_atoms: maxAtoms } : {}),
  });

  return (
    <div className="absolute right-0 mt-1 w-72 bg-surface border border-border rounded-lg shadow-lg z-10">
      <div className="px-4 py-2 border-b border-border">
        <p className="text-xs font-semibold text-text-secondary uppercase tracking-wide">
          Batch Generate All Atoms
        </p>
      </div>

      {/* Settings section */}
      <div className="px-4 py-3 border-b border-border space-y-3">
        <label className="flex items-center justify-between gap-2 cursor-pointer">
          <div>
            <div className="text-sm font-medium">Use Batch API</div>
            <div className="text-xs text-text-secondary">
              50% cheaper, slower (hours)
            </div>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={useBatchApi}
            onClick={() => setUseBatchApi((v) => !v)}
            className={cn(
              "relative w-10 h-5 rounded-full transition-colors",
              useBatchApi ? "bg-accent" : "bg-border",
            )}
          >
            <span
              className={cn(
                "absolute top-0.5 left-0.5 w-4 h-4 bg-white",
                "rounded-full transition-transform",
                useBatchApi && "translate-x-5",
              )}
            />
          </button>
        </label>
        <div>
          <label className="text-sm font-medium" htmlFor="max-atoms-input">
            Max atoms
          </label>
          <input
            id="max-atoms-input"
            type="number"
            min={1}
            placeholder="All"
            value={maxAtoms}
            onChange={(e) => setMaxAtoms(e.target.value)}
            className={cn(
              "mt-1 w-full px-3 py-1.5 text-sm rounded-md",
              "bg-background border border-border",
              "placeholder:text-text-secondary/50",
              "focus:outline-none focus:ring-1 focus:ring-accent",
            )}
          />
        </div>
      </div>

      {/* Preset buttons */}
      <button
        onClick={() => onSelect(buildOpts("pending_only", "true"))}
        className="w-full px-4 py-2.5 text-left text-sm hover:bg-white/5"
      >
        <div className="font-medium">
          Pending — no-image atoms only
        </div>
        <div className="text-xs text-text-secondary mt-0.5">
          Only atoms that don&apos;t require images,
          skip already-generated
        </div>
      </button>
      <button
        onClick={() => onSelect(buildOpts("pending_only", "false"))}
        className="w-full px-4 py-2.5 text-left text-sm hover:bg-white/5"
      >
        <div className="font-medium">
          Pending — all atoms
        </div>
        <div className="text-xs text-text-secondary mt-0.5">
          All pending atoms including those with images
        </div>
      </button>
      <button
        onClick={() => onSelect(buildOpts("all", "true"))}
        className={cn(
          "w-full px-4 py-2.5 text-left text-sm",
          "hover:bg-white/5 text-warning rounded-b-lg",
        )}
      >
        <div className="font-medium">
          Re-run all — no-image atoms only
        </div>
        <div className="text-xs text-text-secondary mt-0.5">
          Re-generate all atoms that don&apos;t require images
        </div>
      </button>
    </div>
  );
}
