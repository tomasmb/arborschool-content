"use client";

import { CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";

export type QGenTab = "overview" | "generation" | "results" | "sync";

export interface QuestionGenTabsProps {
  activeTab: QGenTab;
  onTabChange: (tab: QGenTab) => void;
  atomCount: number;
  atomsWithQuestions: number;
}

interface TabConfig {
  id: QGenTab;
  step: number;
  label: string;
}

const tabConfigs: TabConfig[] = [
  { id: "overview", step: 1, label: "Overview" },
  { id: "generation", step: 2, label: "Generate" },
  { id: "results", step: 3, label: "Results" },
  { id: "sync", step: 4, label: "Sync" },
];

export function QuestionGenTabs({
  activeTab,
  onTabChange,
  atomCount,
  atomsWithQuestions,
}: QuestionGenTabsProps) {
  return (
    <div className="border-b border-border bg-surface/50">
      <nav className="flex -mb-px overflow-x-auto">
        {tabConfigs.map((tab) => {
          const isActive = activeTab === tab.id;
          const isComplete =
            tab.id === "overview" && atomCount > 0;

          return (
            <button
              key={tab.id}
              onClick={() => onTabChange(tab.id)}
              className={cn(
                "flex items-center gap-2 px-4 py-3 text-sm font-medium",
                "border-b-2 transition-colors whitespace-nowrap",
                isActive
                  ? "border-accent text-accent bg-accent/5"
                  : "border-transparent text-text-secondary hover:text-text-primary hover:bg-white/5",
              )}
            >
              <span
                className={cn(
                  "flex items-center justify-center w-5 h-5 rounded-full text-xs font-semibold",
                  isActive
                    ? "bg-accent text-white"
                    : isComplete
                      ? "bg-success/20 text-success"
                      : "bg-text-secondary/20 text-text-secondary",
                )}
              >
                {isComplete ? (
                  <CheckCircle2 className="w-3.5 h-3.5" />
                ) : (
                  tab.step
                )}
              </span>

              <span>{tab.label}</span>

              {/* Count badge for Results tab */}
              {tab.id === "results" && atomsWithQuestions > 0 && (
                <span
                  className={cn(
                    "px-1.5 py-0.5 text-xs rounded",
                    isActive
                      ? "bg-accent/20"
                      : "bg-surface text-text-secondary",
                  )}
                >
                  {atomsWithQuestions}/{atomCount}
                </span>
              )}
            </button>
          );
        })}
      </nav>
    </div>
  );
}
