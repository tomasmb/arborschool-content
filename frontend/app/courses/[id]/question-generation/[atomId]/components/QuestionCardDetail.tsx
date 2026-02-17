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
import { revalidateSingleItem, revalidateFinalItem } from "@/lib/api";
import type {
  GeneratedItem,
  PlanSlot,
  ValidatorStatuses,
} from "@/lib/api-types-question-gen";
import type { FailedGate } from "./QuestionCards";
import { DifficultyBadge } from "./EnrichmentSection";
import {
  CopyButton,
  PlanSpec,
  ValidatorBreakdown,
  ValidatorPills,
  XmlViewer,
  type OverallStatus,
} from "./shared";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Revalidation result shape (shared by base + final). */
interface RevalResult {
  passed: boolean;
  errors: string[];
  validators: Record<string, string>;
}

interface QuestionCardDetailProps {
  item: GeneratedItem;
  status: OverallStatus;
  /** Which validation gate the item failed at (null = passed). */
  failedGate?: FailedGate;
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
  failedGate,
  planSlot,
  atomId,
  onRevalidated,
}: QuestionCardDetailProps) {
  const [expanded, setExpanded] = useState(false);
  const [showXml, setShowXml] = useState(false);

  const [revalLoading, setRevalLoading] = useState(false);
  const [revalResult, setRevalResult] = useState<RevalResult | null>(null);
  const [finalRevalLoading, setFinalRevalLoading] = useState(false);
  const [finalRevalResult, setFinalRevalResult] =
    useState<RevalResult | null>(null);

  const meta = item.pipeline_meta;

  // Use revalidation result if available, otherwise original
  const latestResult = finalRevalResult ?? revalResult;
  const displayValidators: ValidatorStatuses = latestResult
    ? (latestResult.validators as unknown as ValidatorStatuses)
    : meta.validators;

  const displayStatus: OverallStatus = latestResult
    ? (latestResult.passed ? "pass" : "fail")
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

  const handleRevalidateFinal = useCallback(async () => {
    if (!atomId || finalRevalLoading) return;
    setFinalRevalLoading(true);
    setFinalRevalResult(null);
    try {
      const result = await revalidateFinalItem(
        atomId, item.item_id,
      );
      setFinalRevalResult(result);
      onRevalidated?.();
    } catch (err) {
      setFinalRevalResult({
        passed: false,
        errors: [
          err instanceof Error
            ? err.message
            : "Final revalidation failed",
        ],
        validators: meta.validators as unknown as Record<string, string>,
      });
    } finally {
      setFinalRevalLoading(false);
    }
  }, [
    atomId, item.item_id, meta.validators,
    finalRevalLoading, onRevalidated,
  ]);

  const anyLoading = revalLoading || finalRevalLoading;

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

        {/* Failed-gate badge */}
        {failedGate && !latestResult && (
          <FailedGateBadge gate={failedGate} />
        )}

        {/* Validator pills pushed right */}
        <div className="flex-1 flex justify-end">
          <ValidatorPills validators={displayValidators} />
        </div>

        {expanded ? (
          <ChevronDown
            className="w-4 h-4 text-text-secondary shrink-0"
          />
        ) : (
          <ChevronRight
            className="w-4 h-4 text-text-secondary shrink-0"
          />
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
          finalRevalLoading={finalRevalLoading}
          finalRevalResult={finalRevalResult}
          onRevalidateFinal={
            atomId ? handleRevalidateFinal : undefined
          }
          failedGate={failedGate}
          anyLoading={anyLoading}
        />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Expanded content (split out to keep main component readable)
// ---------------------------------------------------------------------------

interface ExpandedContentProps {
  item: GeneratedItem;
  planSlot: PlanSlot | null;
  showXml: boolean;
  onToggleXml: () => void;
  displayValidators: ValidatorStatuses;
  revalLoading: boolean;
  revalResult: RevalResult | null;
  onRevalidate?: () => void;
  finalRevalLoading: boolean;
  finalRevalResult: RevalResult | null;
  onRevalidateFinal?: () => void;
  failedGate?: FailedGate;
  anyLoading: boolean;
}

function ExpandedContent(props: ExpandedContentProps) {
  const {
    item, planSlot, showXml, onToggleXml,
    displayValidators, revalLoading, revalResult,
    onRevalidate, finalRevalLoading, finalRevalResult,
    onRevalidateFinal, failedGate, anyLoading,
  } = props;

  const activeResult = finalRevalResult ?? revalResult;
  const activeLoading = finalRevalLoading || revalLoading;

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
              : "border-border text-text-secondary"
                + " hover:text-text-primary hover:bg-white/[0.06]",
          )}
        >
          <Code2 className="w-3 h-3" />
          {showXml ? "Hide XML" : "View XML"}
        </button>

        {/* Base revalidation button */}
        <RevalidateButton
          label="Revalidate (Base)"
          title="Re-run base validation checks"
          loading={revalLoading}
          disabled={anyLoading}
          onClick={onRevalidate}
        />

        {/* Final revalidation button */}
        {(failedGate === "final" || failedGate === null) && (
          <RevalidateButton
            label="Revalidate (Final)"
            title="Re-run final LLM validation"
            loading={finalRevalLoading}
            disabled={anyLoading}
            onClick={onRevalidateFinal}
          />
        )}

        {/* Inline revalidation result badge */}
        {activeResult && !activeLoading && (
          <RevalResultBadge
            passed={activeResult.passed}
            errorCount={activeResult.errors.length}
          />
        )}
      </div>

      {/* Revalidation errors (if any) */}
      {activeResult && activeResult.errors.length > 0 && (
        <RevalErrors errors={activeResult.errors} />
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
// Failed gate badge (shown in card header)
// ---------------------------------------------------------------------------

function FailedGateBadge({ gate }: { gate: "base" | "final" }) {
  const label = gate === "base"
    ? "Failed: Base"
    : "Failed: Final";
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 px-2 py-0.5",
        "rounded-full text-[10px] font-medium",
        "bg-error/10 text-error",
      )}
    >
      <XCircle className="w-3 h-3" />
      {label}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Revalidation button (reused for base + final)
// ---------------------------------------------------------------------------

function RevalidateButton({
  label,
  title,
  loading,
  disabled,
  onClick,
}: {
  label: string;
  title: string;
  loading: boolean;
  disabled: boolean;
  onClick?: () => void;
}) {
  return (
    <button
      onClick={onClick}
      disabled={!onClick || disabled}
      className={cn(
        "inline-flex items-center gap-1.5",
        "px-2.5 py-1 rounded-md border border-border text-xs",
        "transition-all duration-150",
        loading
          ? "text-accent cursor-wait"
          : onClick && !disabled
            ? "text-text-secondary hover:text-text-primary"
              + " hover:bg-white/[0.06]"
            : "text-text-secondary/30 cursor-not-allowed",
      )}
      title={title}
    >
      {loading ? (
        <Loader2 className="w-3 h-3 animate-spin" />
      ) : (
        <RotateCcw className="w-3 h-3" />
      )}
      {loading ? "Validating..." : label}
    </button>
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


