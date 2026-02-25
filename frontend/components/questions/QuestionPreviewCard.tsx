"use client";

import { useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  XCircle,
  Clock,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { QTIInteractive } from "@/components/qti/QTIInteractive";

// -----------------------------------------------------------------------------
// Types
// -----------------------------------------------------------------------------

export type QuestionStatus = "pass" | "fail" | "pending";

export interface QuestionPreviewItem {
  item_id: string;
  atom_id: string;
  atom_titulo?: string;
  eje?: string;
  qti_xml: string;
  difficulty?: string;
  context?: string;
  status: QuestionStatus;
  phase?: number;
  slot_index?: number;
}

interface QuestionPreviewCardProps {
  item: QuestionPreviewItem;
  /** Show atom ID badge (useful in cross-atom views) */
  showAtomId?: boolean;
  /** Compact mode for dense lists */
  compact?: boolean;
  className?: string;
}

// -----------------------------------------------------------------------------
// Status config
// -----------------------------------------------------------------------------

const STATUS_CONFIG = {
  pass: {
    border: "border-l-success",
    bg: "",
    Icon: CheckCircle2,
    iconCls: "text-success",
    label: "Passed",
  },
  fail: {
    border: "border-l-error",
    bg: "bg-error/[0.02]",
    Icon: XCircle,
    iconCls: "text-error",
    label: "Failed",
  },
  pending: {
    border: "border-l-border",
    bg: "",
    Icon: Clock,
    iconCls: "text-text-secondary",
    label: "Pending",
  },
} as const;

const DIFFICULTY_STYLES: Record<string, string> = {
  easy: "bg-success/10 text-success",
  medium: "bg-warning/10 text-warning",
  hard: "bg-error/10 text-error",
};

// -----------------------------------------------------------------------------
// Component
// -----------------------------------------------------------------------------

export function QuestionPreviewCard({
  item,
  showAtomId = false,
  compact = false,
  className,
}: QuestionPreviewCardProps) {
  const [expanded, setExpanded] = useState(false);
  const cfg = STATUS_CONFIG[item.status];

  const diffStyle =
    DIFFICULTY_STYLES[item.difficulty ?? ""] ??
    "bg-white/10 text-text-secondary";
  const diffLabel = item.difficulty
    ? item.difficulty.charAt(0).toUpperCase() +
      item.difficulty.slice(1)
    : null;

  return (
    <div
      className={cn(
        "bg-surface border border-border rounded-lg overflow-hidden",
        "border-l-[3px] transition-all duration-200",
        cfg.border,
        cfg.bg,
        className,
      )}
    >
      {/* Header -- always visible */}
      <button
        onClick={() => setExpanded(!expanded)}
        className={cn(
          "w-full flex items-center gap-3 text-left",
          "hover:bg-white/[0.02] transition-colors",
          compact ? "px-3 py-2" : "px-4 py-3",
        )}
      >
        <cfg.Icon
          className={cn("w-4 h-4 shrink-0", cfg.iconCls)}
        />

        <span
          className={cn(
            "text-xs font-mono text-text-secondary",
            "truncate max-w-[180px]",
          )}
        >
          {item.item_id}
        </span>

        {showAtomId && (
          <span
            className={cn(
              "hidden sm:inline-flex px-1.5 py-0.5",
              "rounded text-[10px] font-medium",
              "bg-accent/10 text-accent truncate max-w-[160px]",
            )}
            title={item.atom_titulo ?? item.atom_id}
          >
            {item.atom_id}
          </span>
        )}

        {diffLabel && (
          <span
            className={cn(
              "inline-flex px-1.5 py-0.5 rounded",
              "text-[10px] font-semibold",
              diffStyle,
            )}
          >
            {diffLabel}
          </span>
        )}

        {item.slot_index !== undefined && (
          <span className="text-[10px] text-text-secondary">
            #{item.slot_index}
          </span>
        )}

        <div className="flex-1" />

        {expanded ? (
          <ChevronDown className="w-4 h-4 text-text-secondary shrink-0" />
        ) : (
          <ChevronRight className="w-4 h-4 text-text-secondary shrink-0" />
        )}
      </button>

      {/* Expanded: interactive QTI renderer */}
      {expanded && (
        <div
          className={cn(
            "border-t border-border",
            compact ? "p-3" : "p-4",
          )}
        >
          <QTIInteractive
            qtiXml={item.qti_xml}
            showCorrectAnswer
            size="sm"
          />
        </div>
      )}
    </div>
  );
}
