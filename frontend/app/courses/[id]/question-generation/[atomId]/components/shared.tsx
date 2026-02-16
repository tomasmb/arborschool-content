"use client";

import { useState, type ReactNode } from "react";
import { ChevronDown, ChevronRight, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Collapsible section wrapper (reused by Enrichment, Plan, etc.)
// ---------------------------------------------------------------------------

interface CollapsibleSectionProps {
  icon: LucideIcon;
  title: string;
  subtitle?: string;
  defaultExpanded?: boolean;
  children: ReactNode;
}

export function CollapsibleSection({
  icon: Icon,
  title,
  subtitle,
  defaultExpanded = false,
  children,
}: CollapsibleSectionProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  return (
    <div className="bg-surface border border-border rounded-lg">
      <button
        onClick={() => setExpanded(!expanded)}
        className={cn(
          "w-full px-4 py-3 flex items-center justify-between",
          "hover:bg-white/5 transition-colors rounded-lg",
        )}
      >
        <div className="flex items-center gap-2">
          <Icon className="w-4 h-4 text-accent" />
          <h2 className="text-sm font-semibold">{title}</h2>
          {subtitle && (
            <span className="text-xs text-text-secondary">
              {subtitle}
            </span>
          )}
        </div>
        {expanded ? (
          <ChevronDown className="w-4 h-4 text-text-secondary" />
        ) : (
          <ChevronRight className="w-4 h-4 text-text-secondary" />
        )}
      </button>
      {expanded && children}
    </div>
  );
}


// ---------------------------------------------------------------------------
// Formatting helpers (used by PlanTable and QuestionCards)
// ---------------------------------------------------------------------------

/** Format "ALGEBRA.TRADUCCION" -> "Traduccion" */
export function formatTag(tag: string): string {
  const parts = tag.split(".");
  const last = parts[parts.length - 1];
  return last.charAt(0) + last.slice(1).toLowerCase();
}

/** Format "pure_math" -> "Pure math" */
export function formatContext(ctx: string): string {
  return ctx.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
}
