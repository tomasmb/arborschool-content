"use client";

import { CheckCircle2, Lock } from "lucide-react";
import { cn } from "@/lib/utils";
import type { AtomPipelineSummary } from "@/lib/api";

export type AtomTab =
  | "generation"
  | "validation"
  | "coverage"
  | "graph"
  | "sync";

export interface AtomTabsProps {
  activeTab: AtomTab;
  onTabChange: (tab: AtomTab) => void;
  summary: AtomPipelineSummary;
}

type TabStatus = "complete" | "in_progress" | "not_started" | "blocked";

interface TabConfig {
  id: AtomTab;
  step: number;
  label: string;
  getStatus: (s: AtomPipelineSummary) => TabStatus;
  getLabel: (s: AtomPipelineSummary) => string;
}

const tabConfigs: TabConfig[] = [
  {
    id: "generation",
    step: 1,
    label: "Generate",
    getStatus: (s) => {
      if (!s.has_standards) return "blocked";
      if (s.atom_count > 0) return "complete";
      return "not_started";
    },
    getLabel: (s) => (s.atom_count > 0 ? `${s.atom_count}` : ""),
  },
  {
    id: "validation",
    step: 2,
    label: "Validate",
    getStatus: (s) => {
      if (s.atom_count === 0) return "blocked";
      if (
        s.standards_validated >= s.standards_count &&
        s.standards_validated > 0 &&
        s.standards_with_issues === 0
      )
        return "complete";
      if (s.standards_validated > 0) return "in_progress";
      return "not_started";
    },
    getLabel: (s) =>
      s.atom_count > 0
        ? `${s.standards_validated}/${s.standards_count}`
        : "",
  },
  {
    id: "coverage",
    step: 3,
    label: "Coverage",
    getStatus: (s) => {
      if (s.atom_count === 0) return "blocked";
      return "not_started";
    },
    getLabel: () => "",
  },
  {
    id: "graph",
    step: 4,
    label: "Graph",
    getStatus: (s) => {
      if (s.atom_count === 0) return "blocked";
      return "not_started";
    },
    getLabel: () => "",
  },
  {
    id: "sync",
    step: 5,
    label: "Sync",
    getStatus: (s) => {
      // Blocked until validation has been run AND structural checks pass
      if (s.atom_count === 0) return "blocked";
      if (s.standards_validated === 0) return "blocked";
      if (s.structural_checks_passed === false) return "blocked";
      return "not_started";
    },
    getLabel: (s) =>
      s.atom_count > 0 ? `${s.atom_count} atoms` : "",
  },
];

export function AtomTabs({
  activeTab,
  onTabChange,
  summary,
}: AtomTabsProps) {
  const firstIncomplete = tabConfigs.find((tab) => {
    const status = tab.getStatus(summary);
    return status === "not_started" || status === "in_progress";
  });

  return (
    <div className="border-b border-border bg-surface/50">
      <nav className="flex -mb-px overflow-x-auto">
        {tabConfigs.map((tab) => {
          const status = tab.getStatus(summary);
          const label = tab.getLabel(summary);
          const isActive = activeTab === tab.id;
          const isBlocked = status === "blocked";
          const isCurrent =
            firstIncomplete?.id === tab.id && !isActive;

          return (
            <button
              key={tab.id}
              onClick={() => !isBlocked && onTabChange(tab.id)}
              disabled={isBlocked}
              className={cn(
                "flex items-center gap-2 px-4 py-3 text-sm font-medium",
                "border-b-2 transition-colors whitespace-nowrap",
                isActive
                  ? "border-accent text-accent bg-accent/5"
                  : isBlocked
                    ? "border-transparent text-text-secondary/50 cursor-not-allowed"
                    : isCurrent
                      ? "border-transparent text-accent/80 bg-accent/5 hover:bg-accent/10"
                      : "border-transparent text-text-secondary hover:text-text-primary hover:bg-white/5",
              )}
            >
              {/* Step number */}
              <span
                className={cn(
                  "flex items-center justify-center w-5 h-5 rounded-full text-xs font-semibold",
                  isActive
                    ? "bg-accent text-white"
                    : status === "complete"
                      ? "bg-success/20 text-success"
                      : isBlocked
                        ? "bg-text-secondary/10 text-text-secondary/50"
                        : "bg-text-secondary/20 text-text-secondary",
                )}
              >
                {status === "complete" ? (
                  <CheckCircle2 className="w-3.5 h-3.5" />
                ) : (
                  tab.step
                )}
              </span>

              <span>{tab.label}</span>

              {/* Count badge */}
              {label && !isBlocked && (
                <span
                  className={cn(
                    "px-1.5 py-0.5 text-xs rounded",
                    isActive
                      ? "bg-accent/20"
                      : status === "complete"
                        ? "bg-success/10 text-success"
                        : "bg-surface text-text-secondary",
                  )}
                >
                  {label}
                </span>
              )}
            </button>
          );
        })}
      </nav>
    </div>
  );
}
