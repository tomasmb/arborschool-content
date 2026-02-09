"use client";

import { useCallback, useEffect, useState } from "react";
import { Shield, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  getAtomStructuralChecks,
  getAtomValidationResults,
  type AtomPipelineSummary,
  type StructuralChecksResult,
  type SavedValidationSummary,
} from "@/lib/api";
import {
  StructuralChecksDisplay,
  ValidationRow,
} from "./ValidationSubComponents";

// -----------------------------------------------------------------------------
// Types
// -----------------------------------------------------------------------------

type NextAction = "structural" | "validate" | "done";
type Filter = "all" | "passing" | "issues" | "not_validated";

interface ValidationTabProps {
  subjectId: string;
  summary: AtomPipelineSummary;
  onOpenValidation: () => void;
  onRefresh: () => void;
}

// -----------------------------------------------------------------------------
// Component
// -----------------------------------------------------------------------------

export function ValidationTab({
  subjectId,
  summary,
  onOpenValidation,
  onRefresh,
}: ValidationTabProps) {
  const [structural, setStructural] =
    useState<StructuralChecksResult | null>(null);
  const [structuralLoading, setStructuralLoading] = useState(false);
  const [validationResults, setValidationResults] = useState<
    SavedValidationSummary[]
  >([]);
  const [filter, setFilter] = useState<Filter>("all");
  const [expandedStds, setExpandedStds] = useState<Set<string>>(
    new Set(),
  );

  // Load saved validation results on mount
  useEffect(() => {
    getAtomValidationResults(subjectId)
      .then(setValidationResults)
      .catch(() => {});
  }, [subjectId]);

  const runStructuralChecks = useCallback(async () => {
    setStructuralLoading(true);
    try {
      const result = await getAtomStructuralChecks(subjectId);
      setStructural(result);
      onRefresh();
    } catch (err) {
      console.error("Structural checks failed:", err);
    } finally {
      setStructuralLoading(false);
    }
  }, [subjectId, onRefresh]);

  // Determine next action
  const getNextAction = (): NextAction => {
    if (!structural) return "structural";
    const unvalidated =
      summary.standards_count - summary.standards_validated;
    if (unvalidated > 0) return "validate";
    return "done";
  };

  const nextAction = getNextAction();

  // Filter validation results
  const filtered = validationResults.filter((r) => {
    if (filter === "passing")
      return (
        r.overall_quality === "excellent" ||
        r.overall_quality === "good"
      );
    if (filter === "issues")
      return (
        r.overall_quality === "needs_improvement" ||
        r.atoms_with_issues > 0
      );
    return true;
  });

  const toggleExpanded = (stdId: string) => {
    setExpandedStds((prev) => {
      const next = new Set(prev);
      if (next.has(stdId)) next.delete(stdId);
      else next.add(stdId);
      return next;
    });
  };

  // Filter counts for tabs
  const passingCount = validationResults.filter(
    (r) =>
      r.overall_quality === "excellent" ||
      r.overall_quality === "good",
  ).length;
  const issuesCount = validationResults.filter(
    (r) =>
      r.overall_quality === "needs_improvement" ||
      r.atoms_with_issues > 0,
  ).length;
  const unvalidatedCount =
    summary.standards_count - summary.standards_validated;

  const filters: { id: Filter; label: string; count: number }[] = [
    {
      id: "all",
      label: "All",
      count: validationResults.length,
    },
    { id: "passing", label: "Passing", count: passingCount },
    { id: "issues", label: "Issues", count: issuesCount },
    {
      id: "not_validated",
      label: "Not Validated",
      count: unvalidatedCount,
    },
  ];

  return (
    <div className="space-y-6">
      {/* Structural Checks Section */}
      <div className="bg-surface border border-border rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-accent" />
            <h3 className="font-semibold">Structural Checks</h3>
          </div>
          <button
            onClick={runStructuralChecks}
            disabled={structuralLoading}
            className={cn(
              "px-4 py-2 text-sm rounded-lg font-medium transition-colors",
              structural
                ? "bg-surface border border-border text-text-secondary hover:text-text-primary"
                : "bg-accent text-white hover:bg-accent/90",
            )}
          >
            {structuralLoading
              ? "Running..."
              : structural
                ? "Re-run"
                : "Run Checks"}
          </button>
        </div>

        {structural ? (
          <StructuralChecksDisplay result={structural} />
        ) : (
          <p className="text-sm text-text-secondary">
            Run structural checks to validate schema, circular
            dependencies, ID formats, and granularity heuristics.
            This is instant and free (no AI cost).
          </p>
        )}
      </div>

      {/* LLM Validation Section */}
      <div className="bg-surface border border-border rounded-lg">
        {/* Header */}
        <div className="p-6 border-b border-border">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-accent" />
              <h3 className="font-semibold">
                Quality Validation (LLM)
              </h3>
            </div>
            {nextAction === "validate" && (
              <button
                onClick={onOpenValidation}
                className="flex items-center gap-2 px-4 py-2 bg-accent text-white text-sm rounded-lg font-medium hover:bg-accent/90 transition-colors"
              >
                <Sparkles className="w-4 h-4" />
                Validate {unvalidatedCount} Standard
                {unvalidatedCount !== 1 ? "s" : ""}
              </button>
            )}
            {nextAction === "done" && (
              <button
                onClick={onOpenValidation}
                className={cn(
                  "px-4 py-2 bg-surface border border-border text-sm",
                  "rounded-lg font-medium text-text-secondary",
                  "hover:text-text-primary transition-colors",
                )}
              >
                Re-validate
              </button>
            )}
          </div>

          {/* Progress stats */}
          <div className="flex gap-4 text-sm">
            <span className="text-text-secondary">
              Validated:{" "}
              <span className="text-text-primary font-medium">
                {summary.standards_validated}/
                {summary.standards_count}
              </span>
            </span>
            {passingCount > 0 && (
              <span className="text-success">
                {passingCount} passing
              </span>
            )}
            {issuesCount > 0 && (
              <span className="text-amber-500">
                {issuesCount} with issues
              </span>
            )}
          </div>
        </div>

        {/* Filter tabs */}
        {validationResults.length > 0 && (
          <div className="flex gap-1 px-6 pt-4 pb-2">
            {filters.map((f) => (
              <button
                key={f.id}
                onClick={() => setFilter(f.id)}
                className={cn(
                  "px-3 py-1.5 text-xs rounded-lg transition-colors",
                  filter === f.id
                    ? "bg-accent text-white"
                    : "bg-background text-text-secondary hover:text-text-primary",
                )}
              >
                {f.label} ({f.count})
              </button>
            ))}
          </div>
        )}

        {/* Results table */}
        {validationResults.length > 0 ? (
          <div className="overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border text-left text-xs text-text-secondary uppercase tracking-wide">
                  <th className="w-8 px-2" />
                  <th className="px-4 py-3 font-medium">
                    Standard
                  </th>
                  <th className="px-4 py-3 font-medium text-center">
                    Quality
                  </th>
                  <th className="px-4 py-3 font-medium text-center">
                    Coverage
                  </th>
                  <th className="px-4 py-3 font-medium text-center">
                    Atoms
                  </th>
                  <th className="px-4 py-3 font-medium text-center">
                    Issues
                  </th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((r) => {
                  const expanded = expandedStds.has(
                    r.standard_id,
                  );
                  return (
                    <ValidationRow
                      key={r.standard_id}
                      result={r}
                      expanded={expanded}
                      onToggle={() =>
                        toggleExpanded(r.standard_id)
                      }
                    />
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-6 text-sm text-text-secondary">
            No validation results yet. Run quality validation to
            check atoms against their standards.
          </div>
        )}
      </div>
    </div>
  );
}
