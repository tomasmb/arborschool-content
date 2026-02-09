"use client";

import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  ChevronDown,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type {
  StructuralChecksResult,
  SavedValidationSummary,
} from "@/lib/api";

// -----------------------------------------------------------------------------
// Structural Checks Display
// -----------------------------------------------------------------------------

export function StructuralChecksDisplay({
  result,
}: {
  result: StructuralChecksResult;
}) {
  const checks = [
    {
      label: "Schema Validation",
      errors: result.schema_errors,
    },
    {
      label: "ID-Eje Match",
      errors: result.id_eje_errors,
    },
    {
      label: "Circular Dependencies",
      errors: result.circular_dependencies,
    },
    {
      label: "Prerequisite References",
      errors: result.missing_prerequisites,
    },
    {
      label: "Standard References",
      errors: result.missing_standard_refs,
    },
    {
      label: "Granularity",
      errors: 0,
      warnings: result.granularity_warnings,
    },
  ];

  return (
    <div className="space-y-3">
      {/* Overall status */}
      <div
        className={cn(
          "flex items-center gap-2 text-sm font-medium",
          result.passed ? "text-success" : "text-error",
        )}
      >
        {result.passed ? (
          <>
            <CheckCircle2 className="w-4 h-4" />
            All structural checks passed ({result.total_atoms}{" "}
            atoms)
          </>
        ) : (
          <>
            <XCircle className="w-4 h-4" />
            Structural issues found ({result.total_atoms} atoms)
          </>
        )}
      </div>

      {/* Check grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
        {checks.map((c) => (
          <div
            key={c.label}
            className="flex items-center gap-2 text-sm bg-background rounded-lg px-3 py-2"
          >
            {c.errors > 0 ? (
              <XCircle className="w-3.5 h-3.5 text-error flex-shrink-0" />
            ) : c.warnings && c.warnings > 0 ? (
              <AlertTriangle className="w-3.5 h-3.5 text-amber-500 flex-shrink-0" />
            ) : (
              <CheckCircle2 className="w-3.5 h-3.5 text-success flex-shrink-0" />
            )}
            <span className="text-text-secondary">{c.label}</span>
            {c.errors > 0 && (
              <span className="text-error font-medium ml-auto">
                {c.errors}
              </span>
            )}
            {c.warnings && c.warnings > 0 && (
              <span className="text-amber-500 font-medium ml-auto">
                {c.warnings}
              </span>
            )}
          </div>
        ))}
      </div>

      {/* Graph stats */}
      {result.graph_stats && (
        <div className="text-xs text-text-secondary mt-2">
          Graph:{" "}
          {result.graph_stats.atoms_with_prerequisites ?? 0} with
          prereqs,{" "}
          {result.graph_stats.atoms_without_prerequisites ?? 0}{" "}
          roots,{" "}
          {result.graph_stats.total_prerequisite_edges ?? 0} edges
        </div>
      )}
    </div>
  );
}

// -----------------------------------------------------------------------------
// Validation Result Row
// -----------------------------------------------------------------------------

export function ValidationRow({
  result,
  expanded,
  onToggle,
}: {
  result: SavedValidationSummary;
  expanded: boolean;
  onToggle: () => void;
}) {
  const qualityColor =
    result.overall_quality === "excellent"
      ? "text-success"
      : result.overall_quality === "good"
        ? "text-success"
        : result.overall_quality === "needs_improvement"
          ? "text-amber-500"
          : "text-text-secondary";

  const coverageColor =
    result.coverage_assessment === "complete"
      ? "text-success"
      : result.coverage_assessment === "incomplete"
        ? "text-amber-500"
        : "text-text-secondary";

  return (
    <>
      <tr
        className={cn(
          "border-b border-border hover:bg-white/5",
          "transition-colors cursor-pointer",
          expanded && "bg-white/5",
        )}
        onClick={onToggle}
      >
        <td className="w-8 px-2">
          {expanded ? (
            <ChevronDown className="w-4 h-4 text-text-secondary" />
          ) : (
            <ChevronRight className="w-4 h-4 text-text-secondary" />
          )}
        </td>
        <td className="px-4 py-3 font-mono text-xs">
          {result.standard_id}
        </td>
        <td
          className={cn(
            "px-4 py-3 text-center text-sm capitalize",
            qualityColor,
          )}
        >
          {result.overall_quality?.replace("_", " ") ?? "—"}
        </td>
        <td
          className={cn(
            "px-4 py-3 text-center text-sm capitalize",
            coverageColor,
          )}
        >
          {result.coverage_assessment ?? "—"}
        </td>
        <td className="px-4 py-3 text-center text-sm">
          {result.total_atoms}
        </td>
        <td className="px-4 py-3 text-center text-sm">
          {result.atoms_with_issues > 0 ? (
            <span className="text-amber-500">
              {result.atoms_with_issues}
            </span>
          ) : (
            <span className="text-success">0</span>
          )}
        </td>
      </tr>
      {expanded && (
        <tr className="bg-background/50">
          <td colSpan={6} className="px-6 py-4">
            <div className="text-sm space-y-2">
              <div className="grid grid-cols-3 gap-4 text-xs">
                <div>
                  <span className="text-text-secondary">
                    Granularity:{" "}
                  </span>
                  <span className="capitalize">
                    {result.granularity_assessment?.replace(
                      "_",
                      " ",
                    ) ?? "—"}
                  </span>
                </div>
                <div>
                  <span className="text-text-secondary">
                    Passing:{" "}
                  </span>
                  <span className="text-success">
                    {result.atoms_passing}/{result.total_atoms}
                  </span>
                </div>
                <div>
                  <span className="text-text-secondary">
                    With Issues:{" "}
                  </span>
                  <span className="text-amber-500">
                    {result.atoms_with_issues}
                  </span>
                </div>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
