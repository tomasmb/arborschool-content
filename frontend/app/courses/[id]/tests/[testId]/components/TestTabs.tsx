"use client";

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
}

export function TestTabs({ activeTab, onTabChange, counts }: TestTabsProps) {
  const tabs: { id: TestTab; label: string; count?: number; countLabel?: string }[] = [
    { id: "splitting", label: "PDF Splitting", count: counts.split },
    { id: "parsing", label: "QTI Parsing", count: counts.qti, countLabel: `${counts.qti}/${counts.split}` },
    {
      id: "questions",
      label: "Questions",
      count: counts.questions,
      countLabel: `${counts.enriched}/${counts.questions}`,
    },
    { id: "variants", label: "Variants", count: counts.variants },
    { id: "sync", label: "Sync", count: counts.validated },
  ];

  return (
    <div className="border-b border-border">
      <nav className="flex gap-1 -mb-px overflow-x-auto">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className={cn(
              "px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap",
              activeTab === tab.id
                ? "border-accent text-accent"
                : "border-transparent text-text-secondary hover:text-text-primary hover:border-border"
            )}
          >
            {tab.label}
            {tab.countLabel && (
              <span
                className={cn(
                  "ml-2 px-2 py-0.5 text-xs rounded-full",
                  activeTab === tab.id ? "bg-accent/20" : "bg-surface"
                )}
              >
                {tab.countLabel}
              </span>
            )}
          </button>
        ))}
      </nav>
    </div>
  );
}
