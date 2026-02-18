"use client";

import { Sparkles, Play, Lock } from "lucide-react";
import { cn } from "@/lib/utils";

const PHASES = [
  { id: "enrich", label: "Enrich", phases: "0-1",
    description: "Scope guardrails + difficulty rubric", requiredPhase: null },
  { id: "plan", label: "Plan", phases: "2-3",
    description: "Diverse item specs + plan validation", requiredPhase: 1 },
  { id: "generate", label: "Generate QTI", phases: "4",
    description: "Base QTI 3.0 XML items", requiredPhase: 3 },
  { id: "validate", label: "Validate", phases: "5-6",
    description: "Dedup, XSD, solvability, PAES checks", requiredPhase: 4 },
  { id: "feedback", label: "Feedback", phases: "7-8",
    description: "Per-option feedback + worked solutions", requiredPhase: 6 },
  { id: "final_validate", label: "Final Validate", phases: "9",
    description: "Final LLM validation", requiredPhase: 8 },
] as const;

export function PhaseControls({
  atomId,
  lastCompletedPhase,
  onRunPhase,
}: {
  atomId: string;
  lastCompletedPhase: number | null;
  onRunPhase: (atomId: string, phase: string) => void;
}) {
  const isUnlocked = (
    requiredPhase: number | null,
  ): boolean => {
    if (requiredPhase === null) return true;
    if (lastCompletedPhase === null) return false;
    return lastCompletedPhase >= requiredPhase;
  };

  return (
    <div className="px-6 py-4 border-b border-border">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-semibold text-text-secondary uppercase tracking-wide">
          Run Individual Phases
        </span>
        <button
          onClick={() => onRunPhase(atomId, "all")}
          className={cn(
            "flex items-center gap-1.5 px-3 py-1.5",
            "bg-accent text-white rounded-md text-xs",
            "font-medium hover:bg-accent/90 transition-colors",
          )}
        >
          <Sparkles className="w-3 h-3" />
          Run All
        </button>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
        {PHASES.map((phase, idx) => {
          const unlocked = isUnlocked(phase.requiredPhase);
          return (
            <button
              key={phase.id}
              disabled={!unlocked}
              onClick={() => onRunPhase(atomId, phase.id)}
              title={
                unlocked
                  ? phase.description
                  : "Complete the previous phase first"
              }
              className={cn(
                "flex items-center gap-2 px-3 py-2 text-left",
                "border rounded-md transition-colors",
                unlocked
                  ? "bg-surface border-border group hover:border-accent/30"
                  : "bg-surface/50 border-border/50 opacity-50 cursor-not-allowed",
              )}
            >
              <span
                className={cn(
                  "flex items-center justify-center w-5 h-5",
                  "rounded-full text-xs font-semibold flex-shrink-0",
                  unlocked
                    ? "bg-accent/10 text-accent"
                    : "bg-white/5 text-text-secondary",
                )}
              >
                {idx + 1}
              </span>
              <div className="min-w-0 flex-1">
                <div
                  className={cn(
                    "text-xs font-medium transition-colors",
                    unlocked && "group-hover:text-accent",
                  )}
                >
                  {phase.label}
                </div>
                <div className="text-[10px] text-text-secondary truncate">
                  {phase.description}
                </div>
              </div>
              {unlocked ? (
                <Play className="w-3 h-3 text-text-secondary group-hover:text-accent transition-colors flex-shrink-0" />
              ) : (
                <Lock className="w-3 h-3 text-text-secondary flex-shrink-0" />
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
