"use client";

import {
  AlertTriangle,
  RefreshCw,
  Loader2,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type {
  AtomPipelineSummary,
  CourseSyncPreview,
  CourseSyncResult,
  CourseSyncDiff,
  CourseSyncEntityDiff,
} from "@/lib/api";

// ---------------------------------------------------------------------------
// Blocked Section
// ---------------------------------------------------------------------------

/** Shown when sync is blocked due to missing validation/checks. */
export function BlockedSection({
  summary,
}: {
  summary: AtomPipelineSummary;
}) {
  let reason = "Complete prerequisites before syncing.";
  if (summary.atom_count === 0) {
    reason = "Generate atoms first before syncing.";
  } else if (summary.standards_validated === 0) {
    reason =
      "Run validation on atoms before syncing. " +
      "Unvalidated atoms must not reach production.";
  } else if (summary.structural_checks_passed === false) {
    reason =
      "Structural checks have failures. " +
      "Fix errors before syncing.";
  }

  return (
    <div className="bg-surface border border-border rounded-lg p-6">
      <div className="flex items-start gap-3 bg-amber-500/10 border border-amber-500/20 rounded-lg p-4">
        <AlertTriangle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
        <div>
          <div className="font-medium text-sm">
            Sync Blocked
          </div>
          <p className="text-sm text-text-secondary mt-1">
            {reason}
          </p>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// DB State Section
// ---------------------------------------------------------------------------

/** Current database state for atoms. */
export function DbStateSection({
  envLabel,
  syncDiff,
  atomsDiff,
  loading,
  onRefresh,
}: {
  envLabel: string;
  syncDiff: CourseSyncDiff | null;
  atomsDiff: CourseSyncEntityDiff | null;
  loading: boolean;
  onRefresh: () => void;
}) {
  return (
    <section className="bg-surface border border-border rounded-lg">
      <div className="px-4 py-3 border-b border-border flex items-center justify-between">
        <h3 className="font-medium">
          Current Database State
        </h3>
        <button
          onClick={onRefresh}
          disabled={loading}
          className="text-xs text-accent hover:underline flex items-center gap-1"
        >
          <RefreshCw
            className={cn(
              "w-3 h-3",
              loading && "animate-spin",
            )}
          />
          Refresh
        </button>
      </div>
      <div className="p-4">
        <p className="text-sm text-text-secondary mb-4">
          What&apos;s currently in your{" "}
          <span className="font-medium text-text-primary">
            {envLabel}
          </span>{" "}
          database:
        </p>

        {syncDiff?.error ? (
          <div className="text-sm text-error bg-error/10 p-3 rounded-lg">
            {syncDiff.error}
          </div>
        ) : loading ? (
          <div className="flex items-center justify-center py-4">
            <Loader2 className="w-4 h-4 animate-spin text-accent mr-2" />
            <span className="text-sm text-text-secondary">
              Loading...
            </span>
          </div>
        ) : atomsDiff ? (
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center p-3 bg-background rounded-lg">
              <p className="text-2xl font-semibold">
                {atomsDiff.db_count}
              </p>
              <p className="text-xs text-text-secondary">
                Atoms in DB
              </p>
            </div>
            <div className="text-center p-3 bg-background rounded-lg">
              <p className="text-2xl font-semibold text-success">
                {atomsDiff.new_count}
              </p>
              <p className="text-xs text-text-secondary">
                New (not in DB)
              </p>
            </div>
            <div className="text-center p-3 bg-background rounded-lg">
              <p className="text-2xl font-semibold text-accent">
                {atomsDiff.modified_count}
              </p>
              <p className="text-xs text-text-secondary">
                Modified
              </p>
            </div>
          </div>
        ) : (
          <p className="text-sm text-text-secondary">
            No diff data available. The database may not be
            configured for this environment.
          </p>
        )}
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Local State Section
// ---------------------------------------------------------------------------

/** Local state: atoms ready to sync. */
export function LocalStateSection({
  summary,
}: {
  summary: AtomPipelineSummary;
}) {
  const validatedPct =
    summary.standards_count > 0
      ? Math.round(
          (summary.standards_validated /
            summary.standards_count) *
            100,
        )
      : 0;

  return (
    <section className="bg-surface border border-border rounded-lg">
      <div className="px-4 py-3 border-b border-border">
        <h3 className="font-medium">
          Local State (Ready to Sync)
        </h3>
      </div>
      <div className="p-4">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-text-secondary uppercase">
              <th className="pb-2">Metric</th>
              <th className="pb-2 text-right">Value</th>
              <th className="pb-2">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            <tr>
              <td className="py-2">Total Atoms</td>
              <td className="py-2 text-right font-mono">
                {summary.atom_count}
              </td>
              <td className="py-2 text-text-secondary text-xs">
                From canonical atoms file
              </td>
            </tr>
            <tr>
              <td className="py-2">Standards Validated</td>
              <td className="py-2 text-right font-mono">
                <span
                  className={
                    validatedPct === 100
                      ? "text-success"
                      : "text-amber-500"
                  }
                >
                  {summary.standards_validated}/
                  {summary.standards_count}
                </span>
              </td>
              <td className="py-2 text-text-secondary text-xs">
                {validatedPct}% validated
              </td>
            </tr>
            <tr>
              <td className="py-2">Structural Checks</td>
              <td className="py-2 text-right font-mono">
                {summary.structural_checks_passed === true ? (
                  <span className="text-success">Passed</span>
                ) : summary.structural_checks_passed ===
                  false ? (
                  <span className="text-error">Failed</span>
                ) : (
                  <span className="text-text-secondary">
                    Not run
                  </span>
                )}
              </td>
              <td className="py-2 text-text-secondary text-xs">
                {summary.standards_with_issues > 0
                  ? `${summary.standards_with_issues} standards with issues`
                  : "All checks passing"}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Sync Preview Section
// ---------------------------------------------------------------------------

/** Sync preview: what will happen when syncing. */
export function PreviewSection({
  syncPreview,
  atomsTable,
  atomsDiff,
  loading,
  error,
  warnings,
  onRefresh,
}: {
  syncPreview: CourseSyncPreview | null;
  atomsTable: { table: string; total: number } | null;
  atomsDiff: CourseSyncEntityDiff | null;
  loading: boolean;
  error: string | null;
  warnings: string[];
  onRefresh: () => void;
}) {
  return (
    <section className="bg-surface border border-border rounded-lg">
      <div className="px-4 py-3 border-b border-border flex items-center justify-between">
        <h3 className="font-medium">
          Sync Preview - What Will Happen
        </h3>
        <button
          onClick={onRefresh}
          disabled={loading}
          className={cn(
            "text-xs text-accent hover:underline",
            "flex items-center gap-1 disabled:opacity-50",
          )}
        >
          <RefreshCw
            className={cn(
              "w-3 h-3",
              loading && "animate-spin",
            )}
          />
          Refresh
        </button>
      </div>
      <div className="p-4">
        {loading ? (
          <div className="flex items-center justify-center py-8 text-text-secondary">
            <Loader2 className="w-5 h-5 animate-spin mr-2" />
            Loading sync preview...
          </div>
        ) : error ? (
          <div className="p-3 bg-error/10 border border-error/20 rounded-lg">
            <p className="text-sm text-error">{error}</p>
            <button
              onClick={onRefresh}
              className="mt-2 text-xs text-accent hover:underline"
            >
              Retry
            </button>
          </div>
        ) : syncPreview && atomsTable ? (
          <PreviewContent
            atomsTable={atomsTable}
            atomsDiff={atomsDiff}
            warnings={warnings}
          />
        ) : (
          <p className="text-sm text-text-secondary">
            No preview available
          </p>
        )}
      </div>
    </section>
  );
}

/** Preview content when data is available. */
function PreviewContent({
  atomsTable,
  atomsDiff,
  warnings,
}: {
  atomsTable: { table: string; total: number };
  atomsDiff: CourseSyncEntityDiff | null;
  warnings: string[];
}) {
  return (
    <div className="space-y-3">
      <p className="text-sm font-medium mb-2">Atoms:</p>
      {atomsDiff ? (
        <div className="flex gap-4 text-sm">
          <span className="text-success">
            + INSERT {atomsDiff.new_count} new
          </span>
          <span className="text-accent">
            ~ UPDATE {atomsDiff.modified_count} existing
          </span>
          <span className="text-text-secondary">
            = UNCHANGED {atomsDiff.unchanged}
          </span>
        </div>
      ) : (
        <div className="flex gap-4 text-sm">
          <span className="text-accent">
            UPSERT {atomsTable.total} atoms
          </span>
        </div>
      )}

      {warnings.length > 0 && (
        <div className="mt-3 p-3 bg-warning/10 border border-warning/20 rounded-lg space-y-1">
          {warnings.map((w, i) => (
            <p
              key={i}
              className="text-sm text-warning flex items-center gap-2"
            >
              <AlertTriangle className="w-4 h-4 flex-shrink-0" />
              {w}
            </p>
          ))}
        </div>
      )}

      <div className="mt-4 p-3 bg-warning/10 border border-warning/20 rounded-lg">
        <p className="text-sm text-warning flex items-center gap-2">
          <AlertTriangle className="w-4 h-4" />
          Sync will UPSERT atoms — existing data is overwritten
        </p>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sync Result Section
// ---------------------------------------------------------------------------

/** Shows result after sync execution. */
export function SyncResultSection({
  result,
}: {
  result: CourseSyncResult;
}) {
  return (
    <section className="bg-surface border border-border rounded-lg">
      <div className="px-4 py-3 border-b border-border">
        <h3 className="font-medium">Sync Result</h3>
      </div>
      <div className="p-4">
        <div className="flex items-center gap-3 mb-4">
          {result.success ? (
            <CheckCircle2 className="w-6 h-6 text-success" />
          ) : (
            <XCircle className="w-6 h-6 text-error" />
          )}
          <p
            className={cn(
              "font-medium",
              result.success ? "text-success" : "text-error",
            )}
          >
            {result.success
              ? "Sync Complete!"
              : "Sync Failed"}
          </p>
        </div>

        <p className="text-sm text-text-secondary mb-3">
          {result.message}
        </p>

        {/* Rows affected breakdown */}
        {Object.keys(result.results).length > 0 && (
          <div className="grid grid-cols-2 gap-2 text-sm">
            {Object.entries(result.results).map(
              ([table, count]) => (
                <div
                  key={table}
                  className="p-3 bg-background rounded-lg"
                >
                  <p className="font-semibold">{count}</p>
                  <p className="text-text-secondary text-xs capitalize">
                    {table} rows
                  </p>
                </div>
              ),
            )}
          </div>
        )}

        {/* Errors list */}
        {result.errors.length > 0 && (
          <div className="mt-3 max-h-32 overflow-y-auto border border-error/20 rounded-lg p-3">
            {result.errors.map((e, i) => (
              <p key={i} className="text-sm text-error">
                {e}
              </p>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
