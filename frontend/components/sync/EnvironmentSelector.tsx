"use client";

import { AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";

/** Database environment targets for sync operations. */
export type SyncEnvironment = "local" | "staging" | "prod";

/** Human-readable label for a sync environment. */
export function envLabel(env: SyncEnvironment): string {
  return env === "prod"
    ? "Production"
    : env.charAt(0).toUpperCase() + env.slice(1);
}

interface EnvironmentSelectorProps {
  selected: SyncEnvironment;
  onChange: (env: SyncEnvironment) => void;
}

/** Shared environment selector used across all sync tabs. */
export function EnvironmentSelector({
  selected,
  onChange,
}: EnvironmentSelectorProps) {
  return (
    <div className="flex items-center gap-4">
      <span className="text-sm text-text-secondary">Environment:</span>
      <div className="flex gap-1 bg-surface border border-border rounded-lg p-1">
        {(["local", "staging", "prod"] as const).map((env) => (
          <button
            key={env}
            onClick={() => onChange(env)}
            className={cn(
              "px-4 py-1.5 text-sm rounded-md transition-colors",
              selected === env
                ? "bg-accent text-white"
                : "text-text-secondary hover:text-text-primary",
            )}
          >
            {envLabel(env)}
          </button>
        ))}
      </div>
      {selected === "prod" && (
        <span className="text-xs text-warning flex items-center gap-1">
          <AlertTriangle className="w-3 h-3" />
          Production database
        </span>
      )}
    </div>
  );
}
