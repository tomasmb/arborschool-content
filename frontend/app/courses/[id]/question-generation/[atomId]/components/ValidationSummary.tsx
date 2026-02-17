"use client";

import {
  CheckCircle2,
  XCircle,
  ShieldCheck,
  AlertTriangle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type {
  PipelineReport,
  GeneratedItem,
} from "@/lib/api-types-question-gen";
import { CollapsibleSection } from "./shared";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface ValidationSummaryProps {
  /** Items that passed base validation (phase 6). */
  validatedItems: GeneratedItem[];
  /** All generated items (phase 4) — used to compute fail count. */
  generatedItems: GeneratedItem[] | null;
  /** Pipeline report with phase-level errors. */
  report: PipelineReport | null;
  /** Callback to scroll to questions and filter to failed. */
  onFilterFailed?: () => void;
  /** Items that passed final validation (phase 9). Null = not run. */
  finalItems?: GeneratedItem[] | null;
  /** Items that entered final validation (phase 8 feedback). */
  feedbackItems?: GeneratedItem[] | null;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ValidationSummary({
  validatedItems,
  generatedItems,
  report,
  onFilterFailed,
  finalItems,
  feedbackItems,
}: ValidationSummaryProps) {
  const passCount = validatedItems.length;
  const totalCount = generatedItems?.length ?? passCount;
  const failCount = totalCount - passCount;
  const baseErrors = extractPhaseErrors(report, "base_validation");

  const hasFinal = finalItems !== null && finalItems !== undefined;
  const finalPassCount = finalItems?.length ?? 0;
  const finalTotalCount = feedbackItems?.length ?? 0;
  const finalFailCount = hasFinal
    ? finalTotalCount - finalPassCount
    : 0;
  const finalErrors = extractPhaseErrors(
    report, "final_validation",
  );

  const totalFails = failCount + finalFailCount;
  const subtitle = hasFinal
    ? `Base: ${passCount}/${totalCount}, `
      + `Final: ${finalPassCount}/${finalTotalCount}`
    : `${passCount} passed, ${failCount} failed of ${totalCount}`;

  return (
    <CollapsibleSection
      icon={ShieldCheck}
      title="Validation Results"
      subtitle={subtitle}
      defaultExpanded={totalFails > 0}
    >
      <div className="px-4 pb-4 space-y-5">
        {/* Base Validation */}
        <GateSection
          title="Base Validation"
          passCount={passCount}
          failCount={failCount}
          totalCount={totalCount}
          errors={baseErrors}
          onFilterFailed={
            failCount > 0 ? onFilterFailed : undefined
          }
        />

        {/* Final Validation */}
        {hasFinal && (
          <>
            <div className="border-t border-border" />
            <GateSection
              title="Final Validation"
              passCount={finalPassCount}
              failCount={finalFailCount}
              totalCount={finalTotalCount}
              errors={finalErrors}
              onFilterFailed={
                finalFailCount > 0 ? onFilterFailed : undefined
              }
            />
          </>
        )}

        {/* All-pass message */}
        {totalFails === 0 && (
          <p
            className={cn(
              "text-xs text-success",
              "flex items-center gap-1.5",
            )}
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            All items passed
            {hasFinal ? " all validation gates" : " validation"}
          </p>
        )}
      </div>
    </CollapsibleSection>
  );
}

// ---------------------------------------------------------------------------
// Gate sub-section (reused for base + final)
// ---------------------------------------------------------------------------

function GateSection({
  title,
  passCount,
  failCount,
  totalCount,
  errors,
  onFilterFailed,
}: {
  title: string;
  passCount: number;
  failCount: number;
  totalCount: number;
  errors: string[];
  onFilterFailed?: () => void;
}) {
  return (
    <div className="space-y-3">
      <h3
        className={cn(
          "text-[11px] font-semibold uppercase tracking-wide",
          "text-text-secondary",
        )}
      >
        {title}
      </h3>

      <div className="flex items-center gap-4 flex-wrap">
        <StatBadge
          icon={CheckCircle2}
          label="Passed"
          value={passCount}
          variant="success"
        />
        <StatBadge
          icon={XCircle}
          label="Failed"
          value={failCount}
          variant={failCount > 0 ? "error" : "muted"}
        />
        {failCount > 0 && onFilterFailed && (
          <button
            onClick={onFilterFailed}
            className={cn(
              "ml-auto inline-flex items-center gap-1.5",
              "px-3 py-1.5 rounded-md text-xs font-medium",
              "bg-error/10 text-error hover:bg-error/20",
              "transition-colors",
            )}
          >
            <XCircle className="w-3.5 h-3.5" />
            Show failed
          </button>
        )}
      </div>

      <PassRateBar pass={passCount} total={totalCount} />

      {errors.length > 0 && (
        <div className="space-y-1 max-h-[200px] overflow-y-auto">
          {errors.map((err, idx) => (
            <ErrorRow key={idx} message={err} />
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function extractPhaseErrors(
  report: PipelineReport | null,
  phaseName: string,
): string[] {
  if (!report) return [];
  const phase = report.phases.find(
    (p) => p.name === phaseName,
  );
  return phase?.errors ?? [];
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function PassRateBar({
  pass,
  total,
}: {
  pass: number;
  total: number;
}) {
  if (total === 0) return null;
  const pct = Math.round((pass / total) * 100);

  return (
    <div className="space-y-1">
      <div className="h-2 rounded-full bg-white/5 overflow-hidden">
        <div
          className={cn(
            "h-full rounded-full transition-all duration-500",
            "bg-gradient-to-r from-success to-success/80",
          )}
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="text-[10px] text-text-secondary text-right">
        {pct}% pass rate
      </div>
    </div>
  );
}

function StatBadge({
  icon: Icon,
  label,
  value,
  variant,
}: {
  icon: typeof CheckCircle2;
  label: string;
  value: number;
  variant: "success" | "error" | "muted";
}) {
  const colors = {
    success: "bg-success/10 text-success",
    error: "bg-error/10 text-error",
    muted: "bg-white/5 text-text-secondary",
  };

  return (
    <div
      className={cn(
        "flex items-center gap-2 px-3 py-1.5 rounded-md",
        colors[variant],
      )}
    >
      <Icon className="w-4 h-4" />
      <span className="text-sm font-semibold">{value}</span>
      <span className="text-xs opacity-80">{label}</span>
    </div>
  );
}

function ErrorRow({ message }: { message: string }) {
  const colonIdx = message.indexOf(":");
  const itemId =
    colonIdx > 0 ? message.slice(0, colonIdx).trim() : null;
  const reason =
    colonIdx > 0 ? message.slice(colonIdx + 1).trim() : message;

  return (
    <div
      className={cn(
        "flex items-start gap-2 text-xs",
        "py-1 px-2 rounded hover:bg-white/[0.03]",
      )}
    >
      <AlertTriangle
        className="w-3.5 h-3.5 text-warning mt-0.5 shrink-0"
      />
      <span>
        {itemId && (
          <span className="font-mono text-text-secondary">
            {itemId}:
          </span>
        )}{" "}
        <span className="text-text-secondary">{reason}</span>
      </span>
    </div>
  );
}
