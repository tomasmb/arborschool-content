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
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ValidationSummary({
  validatedItems,
  generatedItems,
  report,
  onFilterFailed,
}: ValidationSummaryProps) {
  const passCount = validatedItems.length;
  const totalCount = generatedItems?.length ?? passCount;
  const failCount = totalCount - passCount;
  const validationErrors = extractValidationErrors(report);

  return (
    <CollapsibleSection
      icon={ShieldCheck}
      title="Validation Results"
      subtitle={
        `${passCount} passed, ${failCount} failed of ${totalCount}`
      }
      defaultExpanded={failCount > 0}
    >
      <div className="px-4 pb-4 space-y-4">
        {/* Stats row */}
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
              Show failed questions
            </button>
          )}
        </div>

        {/* Pass/fail progress bar */}
        <PassRateBar pass={passCount} total={totalCount} />

        {/* Validation errors list */}
        {validationErrors.length > 0 && (
          <div className="space-y-2">
            <h3
              className={cn(
                "text-[11px] font-semibold uppercase tracking-wide",
                "text-text-secondary",
              )}
            >
              Errors ({validationErrors.length})
            </h3>
            <div className="space-y-1 max-h-[200px] overflow-y-auto">
              {validationErrors.map((err, idx) => (
                <ErrorRow key={idx} message={err} />
              ))}
            </div>
          </div>
        )}

        {/* All-pass message */}
        {failCount === 0 && (
          <p className="text-xs text-success flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5" />
            All items passed validation
          </p>
        )}
      </div>
    </CollapsibleSection>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function extractValidationErrors(
  report: PipelineReport | null,
): string[] {
  if (!report) return [];
  const phase = report.phases.find(
    (p) => p.name === "base_validation",
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
