"use client";

import { AlertTriangle, Server, Cloud, Database } from "lucide-react";
import { cn } from "@/lib/utils";
import type { SyncEnvironment } from "@/lib/api";

const ENVIRONMENTS: { id: SyncEnvironment; label: string; icon: typeof Server }[] = [
  { id: "local", label: "Local", icon: Server },
  { id: "staging", label: "Staging", icon: Cloud },
  { id: "prod", label: "Production", icon: Database },
];

interface EnvironmentSelectorProps {
  environment: SyncEnvironment;
  setEnvironment: (env: SyncEnvironment) => void;
  isEnvConfigured: (env: SyncEnvironment) => boolean;
}

export function EnvironmentSelector({
  environment,
  setEnvironment,
  isEnvConfigured,
}: EnvironmentSelectorProps) {
  return (
    <div>
      <p className="text-sm font-medium mb-3">Target environment:</p>
      <div className="flex gap-2">
        {ENVIRONMENTS.map((env) => {
          const Icon = env.icon;
          const configured = isEnvConfigured(env.id);
          const isSelected = environment === env.id;
          const isProd = env.id === "prod";

          return (
            <button
              key={env.id}
              onClick={() => configured && setEnvironment(env.id)}
              disabled={!configured}
              className={cn(
                "flex items-center gap-2 px-4 py-2 rounded-lg border transition-colors",
                isSelected && configured
                  ? isProd
                    ? "border-error bg-error/10 text-error"
                    : "border-accent bg-accent/10 text-accent"
                  : configured
                    ? "border-border hover:border-border/80"
                    : "border-border/50 opacity-50 cursor-not-allowed"
              )}
            >
              <Icon className="w-4 h-4" />
              <span className="text-sm font-medium">{env.label}</span>
              {isProd && isSelected && <AlertTriangle className="w-4 h-4 text-error" />}
            </button>
          );
        })}
      </div>
      {environment === "prod" && (
        <p className="text-xs text-error mt-2">
          Warning: You are syncing to production. This will affect live data.
        </p>
      )}
    </div>
  );
}

export { ENVIRONMENTS };
