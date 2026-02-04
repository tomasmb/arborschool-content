"use client";

import { CheckCircle2, XCircle, MinusCircle, Clock } from "lucide-react";

type CheckStatus = "pass" | "fail" | "not_applicable";

interface ValidationTabProps {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  result: Record<string, any> | null;
}

const STATUS_CONFIG: Record<
  CheckStatus,
  { icon: React.ReactNode; color: string; bgColor: string; label: string }
> = {
  pass: {
    icon: <CheckCircle2 className="w-4 h-4" />,
    color: "text-success",
    bgColor: "bg-success/10",
    label: "Pass",
  },
  fail: {
    icon: <XCircle className="w-4 h-4" />,
    color: "text-error",
    bgColor: "bg-error/10",
    label: "Fail",
  },
  not_applicable: {
    icon: <MinusCircle className="w-4 h-4" />,
    color: "text-text-secondary",
    bgColor: "bg-background",
    label: "N/A",
  },
};

const CHECK_LABELS: Record<string, string> = {
  correct_answer_check: "Correct Answer",
  feedback_check: "Feedback Quality",
  content_quality_check: "Content Quality",
  image_check: "Image Alignment",
  math_validity_check: "Math Validity",
};

/**
 * Tab component for displaying validation check results.
 * Handles both simplified (string status) and detailed (object) validation formats.
 */
export function ValidationTab({ result }: ValidationTabProps) {
  if (!result) {
    return (
      <div className="text-sm text-text-secondary p-4 text-center">
        <p>No validation results available.</p>
        <p className="mt-1 text-xs">
          Run &quot;Validate&quot; to check question quality after enrichment.
        </p>
      </div>
    );
  }

  // Handle simplified format: { status: "pass", checks: { check_name: "pass", ... } }
  if (result.checks && typeof result.checks === "object") {
    const isPassed = result.status === "pass";
    const checks = Object.entries(result.checks) as [string, string][];

    return (
      <div className="space-y-4">
        {/* Overall result banner */}
        <div
          className={`p-4 rounded-lg border ${
            isPassed
              ? "bg-success/5 border-success/20"
              : "bg-error/5 border-error/20"
          }`}
        >
          <div className="flex items-center gap-3">
            {isPassed ? (
              <CheckCircle2 className="w-6 h-6 text-success" />
            ) : (
              <XCircle className="w-6 h-6 text-error" />
            )}
            <div>
              <p className={`font-medium ${isPassed ? "text-success" : "text-error"}`}>
                {isPassed ? "All checks passed" : "Validation failed"}
              </p>
              {!isPassed && (
                <p className="text-sm text-text-secondary mt-0.5">
                  One or more checks did not pass
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Individual checks */}
        <div className="space-y-2">
          {checks.map(([checkName, status]) => {
            const normalizedStatus = (status as string).toLowerCase().replace(" ", "_");
            const config = STATUS_CONFIG[normalizedStatus as CheckStatus] || STATUS_CONFIG.pass;
            const label = CHECK_LABELS[checkName] || checkName.replace(/_/g, " ");

            return (
              <div
                key={checkName}
                className={`p-3 rounded-lg border border-border ${config.bgColor}`}
              >
                <div className="flex items-center gap-3">
                  <span className={config.color}>{config.icon}</span>
                  <div className="flex-1 flex items-center justify-between">
                    <span className="font-medium text-sm capitalize">{label}</span>
                    <span
                      className={`text-xs px-2 py-0.5 rounded ${config.color} ${config.bgColor}`}
                    >
                      {config.label}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Model info if available */}
        {result.model && (
          <div className="text-xs text-text-secondary text-center">
            Validated with {result.model}
          </div>
        )}
      </div>
    );
  }

  // No recognizable validation structure - show pending message
  return (
    <div className="text-sm text-text-secondary p-4 text-center">
      <div className="flex justify-center mb-3">
        <Clock className="w-8 h-8 text-warning" />
      </div>
      <p className="font-medium text-text-primary">Validation not yet run</p>
      <p className="mt-1 text-xs">
        Enrichment completed. Run &quot;Validate&quot; to perform full quality checks.
      </p>
    </div>
  );
}
