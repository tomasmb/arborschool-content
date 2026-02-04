"use client";

import { CheckCircle2, XCircle, MinusCircle, AlertTriangle } from "lucide-react";
import type { ValidationResultDetail, CheckStatus } from "@/lib/api";

interface ValidationTabProps {
  result: ValidationResultDetail | null;
}

const STATUS_CONFIG: Record<
  CheckStatus,
  { icon: React.ReactNode; color: string; bgColor: string }
> = {
  pass: {
    icon: <CheckCircle2 className="w-4 h-4" />,
    color: "text-success",
    bgColor: "bg-success/10",
  },
  fail: {
    icon: <XCircle className="w-4 h-4" />,
    color: "text-error",
    bgColor: "bg-error/10",
  },
  not_applicable: {
    icon: <MinusCircle className="w-4 h-4" />,
    color: "text-text-secondary",
    bgColor: "bg-background",
  },
};

/**
 * Tab component for displaying validation check results.
 * Shows overall status plus individual check details.
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

  const isPassed = result.validation_result === "pass";

  // Build check items for display
  const checks = [
    {
      name: "Correct Answer",
      result: result.correct_answer_check,
      details: result.correct_answer_check.expected_answer !== result.correct_answer_check.marked_answer
        ? `Expected: ${result.correct_answer_check.expected_answer}, Marked: ${result.correct_answer_check.marked_answer}`
        : null,
    },
    {
      name: "Feedback Quality",
      result: result.feedback_check,
      details: null,
    },
    {
      name: "Content Quality",
      result: {
        status: result.content_quality_check.status,
        issues: [
          ...result.content_quality_check.typos_found.map((t) => `Typo: ${t}`),
          ...result.content_quality_check.character_issues.map((c) => `Character: ${c}`),
          ...result.content_quality_check.clarity_issues.map((c) => `Clarity: ${c}`),
        ],
        reasoning: "",
      },
      details: null,
    },
    {
      name: "Image Alignment",
      result: result.image_check,
      details: null,
    },
    {
      name: "Math Validity",
      result: result.math_validity_check,
      details: null,
    },
  ];

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
        {checks.map((check) => {
          const config = STATUS_CONFIG[check.result.status];
          const hasIssues = check.result.issues && check.result.issues.length > 0;

          return (
            <div
              key={check.name}
              className={`p-3 rounded-lg border border-border ${config.bgColor}`}
            >
              <div className="flex items-start gap-3">
                <span className={config.color}>{config.icon}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium text-sm">{check.name}</span>
                    <span
                      className={`text-xs px-2 py-0.5 rounded capitalize ${config.color} ${config.bgColor}`}
                    >
                      {check.result.status.replace("_", " ")}
                    </span>
                  </div>

                  {/* Show details if provided */}
                  {check.details && (
                    <p className="text-xs text-text-secondary mt-1">{check.details}</p>
                  )}

                  {/* Show issues if any */}
                  {hasIssues && (
                    <ul className="mt-2 space-y-1">
                      {check.result.issues.map((issue, i) => (
                        <li
                          key={i}
                          className="flex items-start gap-2 text-sm text-error"
                        >
                          <AlertTriangle className="w-3 h-3 mt-0.5 flex-shrink-0" />
                          <span>{issue}</span>
                        </li>
                      ))}
                    </ul>
                  )}

                  {/* Show reasoning if available and different from issues */}
                  {"reasoning" in check.result && check.result.reasoning && !hasIssues && (
                    <p className="text-xs text-text-secondary mt-1">
                      {check.result.reasoning}
                    </p>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Overall reasoning */}
      {result.overall_reasoning && (
        <div className="p-3 bg-surface border border-border rounded-lg">
          <p className="text-xs font-medium text-text-secondary mb-1">Summary</p>
          <p className="text-sm">{result.overall_reasoning}</p>
        </div>
      )}
    </div>
  );
}
