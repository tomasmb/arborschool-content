"use client";

import { useCallback, useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  XCircle,
  Clock,
  Code2,
  RotateCcw,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { QTIRenderer } from "@/components/qti/QTIRenderer";
import { revalidateSingleItem } from "@/lib/api";
import type {
  GeneratedItem,
  PlanSlot,
  ValidatorStatuses,
} from "@/lib/api-types-question-gen";
import { DifficultyBadge } from "./EnrichmentSection";
import {
  CopyButton,
  PlanSpec,
  ValidatorBreakdown,
  XmlViewer,
  type OverallStatus,
} from "./shared";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface QuestionCardDetailProps {
  item: GeneratedItem;
  status: OverallStatus;
  planSlot: PlanSlot | null;
  /** Atom ID for per-item revalidation API call. */
  atomId?: string;
  /** Called after revalidation completes to refresh parent data. */
  onRevalidated?: () => void;
}

// Status visual configuration
const STATUS_CONFIG = {
  pass: {
    border: "border-l-success",
    bg: "",
    Icon: CheckCircle2,
    iconCls: "text-success",
  },
  fail: {
    border: "border-l-error",
    bg: "bg-error/[0.02]",
    Icon: XCircle,
    iconCls: "text-error",
  },
  pending: {
    border: "border-l-border",
    bg: "",
    Icon: Clock,
    iconCls: "text-text-secondary",
  },
} as const;

// ---------------------------------------------------------------------------
// Main card component
// ---------------------------------------------------------------------------

export function QuestionCardDetail({
  item,
  status,
  planSlot,
  atomId,
  onRevalidated,
}: QuestionCardDetailProps) {
  const [expanded, setExpanded] = useState(false);
  const [showXml, setShowXml] = useState(false);

  // Revalidation state
  const [revalLoading, setRevalLoading] = useState(false);
  const [revalResult, setRevalResult] = useState<{
    passed: boolean;
    errors: string[];
    validators: Record<string, string>;
  } | null>(null);

  const meta = item.pipeline_meta;

  // Use revalidation result if available, otherwise original
  const displayValidators: ValidatorStatuses = revalResult
    ? (revalResult.validators as unknown as ValidatorStatuses)
    : meta.validators;

  const displayStatus: OverallStatus = revalResult
    ? (revalResult.passed ? "pass" : "fail")
    : status;

  const cfg = STATUS_CONFIG[displayStatus];

  const handleRevalidate = useCallback(async () => {
    if (!atomId || revalLoading) return;
    setRevalLoading(true);
    setRevalResult(null);
    try {
      const result = await revalidateSingleItem(
        atomId, item.item_id,
      );
      setRevalResult(result);
      // Refresh parent data so filter counts match persisted state
      onRevalidated?.();
    } catch (err) {
      setRevalResult({
        passed: false,
        errors: [
          err instanceof Error ? err.message : "Revalidation failed",
        ],
        validators: meta.validators as unknown as Record<string, string>,
      });
    } finally {
      setRevalLoading(false);
    }
  }, [atomId, item.item_id, meta.validators, revalLoading, onRevalidated]);

  return (
    <div
      id={`question-${item.slot_index}`}
      className={cn(
        "bg-surface border border-border rounded-lg overflow-hidden",
        "border-l-[3px]",
        cfg.border,
        cfg.bg,
        "transition-all duration-200",
      )}
    >
      {/* Compact header — always visible */}
      <button
        onClick={() => setExpanded(!expanded)}
        className={cn(
          "w-full px-4 py-3 flex items-center gap-3",
          "hover:bg-white/[0.02] transition-colors text-left",
        )}
      >
        <cfg.Icon
          className={cn("w-4 h-4 shrink-0", cfg.iconCls)}
        />
        <span
          className={cn(
            "text-xs font-mono text-text-secondary",
            "truncate max-w-[200px]",
          )}
        >
          {item.item_id}
        </span>
        <DifficultyBadge level={meta.difficulty_level} />
        <span className="text-[10px] text-text-secondary">
          #{item.slot_index}
        </span>

        {/* Validator pills pushed right */}
        <div className="flex-1 flex justify-end">
          <ValidatorPills validators={displayValidators} />
        </div>

        {expanded ? (
          <ChevronDown className="w-4 h-4 text-text-secondary shrink-0" />
        ) : (
          <ChevronRight className="w-4 h-4 text-text-secondary shrink-0" />
        )}
      </button>

      {/* Expanded detail */}
      {expanded && (
        <ExpandedContent
          item={item}
          planSlot={planSlot}
          showXml={showXml}
          onToggleXml={() => setShowXml(!showXml)}
          displayValidators={displayValidators}
          revalLoading={revalLoading}
          revalResult={revalResult}
          onRevalidate={atomId ? handleRevalidate : undefined}
        />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Expanded content (split out to keep main component readable)
// ---------------------------------------------------------------------------

function ExpandedContent({
  item,
  planSlot,
  showXml,
  onToggleXml,
  displayValidators,
  revalLoading,
  revalResult,
  onRevalidate,
}: {
  item: GeneratedItem;
  planSlot: PlanSlot | null;
  showXml: boolean;
  onToggleXml: () => void;
  displayValidators: ValidatorStatuses;
  revalLoading: boolean;
  revalResult: { passed: boolean; errors: string[] } | null;
  onRevalidate?: () => void;
}) {
  return (
    <div className="border-t border-border">
      {/* Action bar */}
      <div
        className={cn(
          "px-4 py-2 flex items-center gap-2 flex-wrap",
          "border-b border-border bg-white/[0.01]",
        )}
      >
        <CopyButton text={item.qti_xml} label="Copy XML" />
        <button
          onClick={onToggleXml}
          className={cn(
            "inline-flex items-center gap-1.5",
            "px-2.5 py-1 rounded-md border text-xs",
            "transition-all duration-150",
            showXml
              ? "bg-accent/10 text-accent border-accent/30"
              : "border-border text-text-secondary" +
                " hover:text-text-primary hover:bg-white/[0.06]",
          )}
        >
          <Code2 className="w-3 h-3" />
          {showXml ? "Hide XML" : "View XML"}
        </button>
        <button
          onClick={onRevalidate}
          disabled={!onRevalidate || revalLoading}
          className={cn(
            "inline-flex items-center gap-1.5",
            "px-2.5 py-1 rounded-md border border-border text-xs",
            "transition-all duration-150",
            revalLoading
              ? "text-accent cursor-wait"
              : onRevalidate
                ? "text-text-secondary hover:text-text-primary" +
                  " hover:bg-white/[0.06]"
                : "text-text-secondary/30 cursor-not-allowed",
          )}
          title="Re-run validation checks for this question"
        >
          {revalLoading ? (
            <Loader2 className="w-3 h-3 animate-spin" />
          ) : (
            <RotateCcw className="w-3 h-3" />
          )}
          {revalLoading ? "Validating..." : "Revalidate"}
        </button>

        {/* Inline revalidation result badge */}
        {revalResult && !revalLoading && (
          <RevalResultBadge
            passed={revalResult.passed}
            errorCount={revalResult.errors.length}
          />
        )}
      </div>

      {/* Revalidation errors (if any) */}
      {revalResult && revalResult.errors.length > 0 && (
        <RevalErrors errors={revalResult.errors} />
      )}

      {/* Two-column: metadata + QTI preview */}
      <div className="grid grid-cols-1 lg:grid-cols-3">
        <div
          className={cn(
            "p-4 space-y-4",
            "border-b lg:border-b-0 lg:border-r border-border",
          )}
        >
          <PlanSpec
            meta={item.pipeline_meta}
            planSlot={planSlot}
          />
          <ValidatorBreakdown validators={displayValidators} />
        </div>
        <div className="lg:col-span-2 p-4">
          <QTIRenderer
            qtiXml={item.qti_xml}
            showCorrectAnswer
            showFeedback={false}
            showWorkedSolution={false}
            size="sm"
          />
        </div>
      </div>

      {showXml && <XmlViewer xml={item.qti_xml} />}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Revalidation result badge (inline in action bar)
// ---------------------------------------------------------------------------

function RevalResultBadge({
  passed,
  errorCount,
}: {
  passed: boolean;
  errorCount: number;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 px-2 py-0.5 rounded-full",
        "text-[10px] font-medium",
        passed
          ? "bg-success/10 text-success"
          : "bg-error/10 text-error",
      )}
    >
      {passed ? (
        <>
          <CheckCircle2 className="w-3 h-3" /> All checks passed
        </>
      ) : (
        <>
          <XCircle className="w-3 h-3" /> {errorCount} check(s) failed
        </>
      )}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Revalidation errors panel
// ---------------------------------------------------------------------------

function RevalErrors({ errors }: { errors: string[] }) {
  return (
    <div
      className={cn(
        "px-4 py-2 border-b border-border",
        "bg-error/[0.03] space-y-1",
      )}
    >
      <span
        className={cn(
          "text-[10px] font-semibold uppercase tracking-wide",
          "text-error/70",
        )}
      >
        Validation errors
      </span>
      {errors.map((err, i) => (
        <div
          key={i}
          className="flex items-start gap-1.5 text-xs text-error/80"
        >
          <XCircle className="w-3 h-3 mt-0.5 shrink-0" />
          <span className="break-all">{err}</span>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Validator pills (compact, for card header)
// ---------------------------------------------------------------------------

function ValidatorPills({
  validators,
}: {
  validators: ValidatorStatuses;
}) {
  const entries = (
    Object.entries(validators) as [string, string][]
  ).filter(([, v]) => v !== "pending");

  if (entries.length === 0) {
    return (
      <span className="text-[10px] text-text-secondary/50">
        validators pending
      </span>
    );
  }

  return (
    <div className="flex items-center gap-1 flex-wrap justify-end">
      {entries.map(([key, value]) => (
        <span
          key={key}
          className={cn(
            "px-1.5 py-0.5 rounded text-[10px] font-medium",
            value === "pass"
              ? "bg-success/10 text-success"
              : "bg-error/10 text-error",
          )}
        >
          {key.replace(/_/g, " ")}
        </span>
      ))}
    </div>
  );
}

