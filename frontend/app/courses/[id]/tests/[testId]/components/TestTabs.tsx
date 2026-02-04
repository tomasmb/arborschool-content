"use client";

import { CheckCircle2, Circle, Lock } from "lucide-react";
import { cn } from "@/lib/utils";

export type TestTab = "splitting" | "parsing" | "questions" | "variants" | "sync";

export interface TestTabsProps {
  activeTab: TestTab;
  onTabChange: (tab: TestTab) => void;
  counts: {
    split: number;
    qti: number;
    questions: number;
    enriched: number;
    validated: number;
    variants: number;
  };
  /** Whether the test has a raw PDF uploaded */
  hasPdf?: boolean;
}

interface TabConfig {
  id: TestTab;
  step: number;
  label: string;
  getStatus: (counts: TestTabsProps["counts"], hasPdf: boolean) => TabStatus;
  getLabel: (counts: TestTabsProps["counts"]) => string;
}

type TabStatus = "complete" | "in_progress" | "not_started" | "blocked";

/**
 * Determine the status of each workflow stage based on counts.
 */
const tabConfigs: TabConfig[] = [
  {
    id: "splitting",
    step: 1,
    label: "Split",
    getStatus: (counts, hasPdf) => {
      if (!hasPdf) return "blocked";
      if (counts.split > 0) return "complete";
      return "not_started";
    },
    getLabel: (counts) => (counts.split > 0 ? `${counts.split}` : ""),
  },
  {
    id: "parsing",
    step: 2,
    label: "Parse",
    getStatus: (counts) => {
      if (counts.split === 0) return "blocked";
      if (counts.qti >= counts.split && counts.qti > 0) return "complete";
      if (counts.qti > 0) return "in_progress";
      return "not_started";
    },
    getLabel: (counts) =>
      counts.split > 0 ? `${counts.qti}/${counts.split}` : "",
  },
  {
    id: "questions",
    step: 3,
    label: "Questions",
    getStatus: (counts) => {
      if (counts.questions === 0) return "blocked";
      if (counts.validated >= counts.questions && counts.validated > 0) return "complete";
      if (counts.enriched > 0 || counts.validated > 0) return "in_progress";
      return "not_started";
    },
    getLabel: (counts) =>
      counts.questions > 0 ? `${counts.validated}/${counts.questions}` : "",
  },
  {
    id: "variants",
    step: 4,
    label: "Variants",
    getStatus: (counts) => {
      if (counts.validated === 0) return "blocked";
      if (counts.variants > 0) return "in_progress"; // Always in_progress since we can add more
      return "not_started";
    },
    getLabel: (counts) => (counts.variants > 0 ? `${counts.variants}` : ""),
  },
  {
    id: "sync",
    step: 5,
    label: "Sync",
    getStatus: (counts) => {
      if (counts.validated === 0) return "blocked";
      return "not_started"; // Sync is never "complete" in this view
    },
    getLabel: (counts) =>
      counts.validated > 0 ? `${counts.validated} ready` : "",
  },
];

function StatusIndicator({ status }: { status: TabStatus }) {
  switch (status) {
    case "complete":
      return <CheckCircle2 className="w-4 h-4 text-success" />;
    case "in_progress":
      return <Circle className="w-4 h-4 text-accent fill-accent/20" />;
    case "blocked":
      return <Lock className="w-3.5 h-3.5 text-text-secondary/50" />;
    default:
      return <Circle className="w-4 h-4 text-text-secondary" />;
  }
}

export function TestTabs({ activeTab, onTabChange, counts, hasPdf = true }: TestTabsProps) {
  // Find the first incomplete tab to highlight as "current"
  const firstIncomplete = tabConfigs.find((tab) => {
    const status = tab.getStatus(counts, hasPdf);
    return status === "not_started" || status === "in_progress";
  });

  return (
    <div className="border-b border-border bg-surface/50">
      <nav className="flex -mb-px overflow-x-auto">
        {tabConfigs.map((tab) => {
          const status = tab.getStatus(counts, hasPdf);
          const label = tab.getLabel(counts);
          const isActive = activeTab === tab.id;
          const isBlocked = status === "blocked";
          const isCurrent = firstIncomplete?.id === tab.id && !isActive;

          return (
            <button
              key={tab.id}
              onClick={() => !isBlocked && onTabChange(tab.id)}
              disabled={isBlocked}
              className={cn(
                "flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap",
                isActive
                  ? "border-accent text-accent bg-accent/5"
                  : isBlocked
                    ? "border-transparent text-text-secondary/50 cursor-not-allowed"
                    : isCurrent
                      ? "border-transparent text-accent/80 bg-accent/5 hover:bg-accent/10"
                      : "border-transparent text-text-secondary hover:text-text-primary hover:bg-white/5"
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
                        : "bg-text-secondary/20 text-text-secondary"
                )}
              >
                {status === "complete" ? (
                  <CheckCircle2 className="w-3.5 h-3.5" />
                ) : (
                  tab.step
                )}
              </span>

              {/* Label */}
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
                        : "bg-surface text-text-secondary"
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
