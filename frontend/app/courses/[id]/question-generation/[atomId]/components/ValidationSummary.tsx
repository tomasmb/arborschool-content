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
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ValidationSummary({
  validatedItems,
  generatedItems,
  report,
}: ValidationSummaryProps) {
  const passCount = validatedItems.length;
  const totalCount = generatedItems?.length ?? passCount;
  const failCount = totalCount - passCount;

  // Extract validation-phase errors from the pipeline report
  const validationErrors = extractValidationErrors(report);

  return (
    <CollapsibleSection
      icon={ShieldCheck}
      title="Validation Results"
      subtitle={`${passCount} passed, ${failCount} failed of ${totalCount}`}
      defaultExpanded={failCount > 0}
    >
      <div className="px-4 pb-4 space-y-3">
        {/* Pass / fail counters */}
        <div className="flex gap-4">
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
        </div>

        {/* Validation errors list */}
        {validationErrors.length > 0 && (
          <div className="space-y-1.5">
            <h3 className="text-[11px] font-semibold uppercase tracking-wide text-text-secondary">
              Failed Items
            </h3>
            <div className="space-y-1">
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
  // Error format: "A-M1-ALG-01-01_Q33: Some error reason"
  const colonIdx = message.indexOf(":");
  const itemId = colonIdx > 0
    ? message.slice(0, colonIdx).trim()
    : null;
  const reason = colonIdx > 0
    ? message.slice(colonIdx + 1).trim()
    : message;

  return (
    <div className="flex items-start gap-2 text-xs">
      <AlertTriangle className="w-3.5 h-3.5 text-warning mt-0.5 shrink-0" />
      <span>
        {itemId && (
          <span className="font-mono text-text-secondary">
            {itemId}:
          </span>
        )}{" "}
        {reason}
      </span>
    </div>
  );
}
