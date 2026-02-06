"use client";

import {
  AlertTriangle,
  RefreshCw,
  ChevronDown,
  ChevronRight,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type {
  QuestionBrief,
  TestSyncPreview,
  TestSyncDiff,
} from "@/lib/api";

// ---------------------------------------------------------------------------
// DB State Section
// ---------------------------------------------------------------------------

export function DbStateSection({
  envLabel,
  syncDiff,
  loading,
  onRefresh,
}: {
  envLabel: string;
  syncDiff: TestSyncDiff | null;
  loading: boolean;
  onRefresh: () => void;
}) {
  const qCount = syncDiff?.questions.db_count;
  const vCount = syncDiff?.variants.db_count;

  return (
    <section className="bg-surface border border-border rounded-lg">
      <div className="px-4 py-3 border-b border-border flex items-center justify-between">
        <h3 className="font-medium">Current Database State</h3>
        <button
          onClick={onRefresh}
          disabled={loading}
          className="text-xs text-accent hover:underline flex items-center gap-1"
        >
          <RefreshCw className={cn("w-3 h-3", loading && "animate-spin")} />
          Refresh
        </button>
      </div>
      <div className="p-4">
        <p className="text-sm text-text-secondary mb-4">
          What&apos;s currently in your{" "}
          <span className="font-medium text-text-primary">{envLabel}</span>{" "}
          database for this test:
        </p>

        {syncDiff?.error ? (
          <div className="text-sm text-error bg-error/10 p-3 rounded-lg">
            {syncDiff.error}
          </div>
        ) : loading ? (
          <div className="flex items-center justify-center py-4">
            <Loader2 className="w-4 h-4 animate-spin text-accent mr-2" />
            <span className="text-sm text-text-secondary">Loading...</span>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-4">
            <div className="text-center p-3 bg-background rounded-lg">
              <p className="text-2xl font-semibold">
                {qCount !== undefined ? qCount : "—"}
              </p>
              <p className="text-xs text-text-secondary">Questions</p>
            </div>
            <div className="text-center p-3 bg-background rounded-lg">
              <p className="text-2xl font-semibold">
                {vCount !== undefined ? vCount : "—"}
              </p>
              <p className="text-xs text-text-secondary">Variants</p>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Local State Section
// ---------------------------------------------------------------------------

export function LocalStateSection({
  validatedQuestions,
  blockedQuestions,
  notEnrichedCount,
  failedValidationCount,
  showBlockedDetails,
  onToggleBlocked,
  syncDiff,
}: {
  validatedQuestions: QuestionBrief[];
  blockedQuestions: QuestionBrief[];
  notEnrichedCount: number;
  failedValidationCount: number;
  showBlockedDetails: boolean;
  onToggleBlocked: () => void;
  syncDiff: TestSyncDiff | null;
}) {
  const vLocal = syncDiff?.variants.local_count;

  return (
    <section className="bg-surface border border-border rounded-lg">
      <div className="px-4 py-3 border-b border-border">
        <h3 className="font-medium">Local State (Ready to Sync)</h3>
      </div>
      <div className="p-4">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-text-secondary uppercase">
              <th className="pb-2">Entity</th>
              <th className="pb-2 text-right">Syncable</th>
              <th className="pb-2 text-right">Blocked</th>
              <th className="pb-2">Reason</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            <tr>
              <td className="py-2">Questions</td>
              <td className="py-2 text-right font-mono text-success">
                {validatedQuestions.length}
              </td>
              <td className="py-2 text-right font-mono text-warning">
                {blockedQuestions.length}
              </td>
              <td className="py-2 text-text-secondary text-xs">
                {notEnrichedCount > 0 && `${notEnrichedCount} not enriched`}
                {notEnrichedCount > 0 && failedValidationCount > 0 && ", "}
                {failedValidationCount > 0 &&
                  `${failedValidationCount} failed validation`}
              </td>
            </tr>
            <tr>
              <td className="py-2">Variants</td>
              <td className="py-2 text-right font-mono text-success">
                {vLocal !== undefined ? vLocal : "—"}
              </td>
              <td className="py-2 text-right font-mono text-warning">—</td>
              <td className="py-2 text-text-secondary text-xs">
                Only validated variants are counted
              </td>
            </tr>
          </tbody>
        </table>

        {blockedQuestions.length > 0 && (
          <button
            onClick={onToggleBlocked}
            className="mt-3 text-xs text-accent hover:underline flex items-center gap-1"
          >
            {showBlockedDetails ? (
              <ChevronDown className="w-3 h-3" />
            ) : (
              <ChevronRight className="w-3 h-3" />
            )}
            View blocked items
          </button>
        )}

        {showBlockedDetails && (
          <div className="mt-3 bg-background rounded-lg p-3 max-h-40 overflow-y-auto">
            <p className="text-xs text-text-secondary mb-2">
              Questions that can&apos;t sync:
            </p>
            <ul className="text-xs space-y-1">
              {blockedQuestions.map((q) => (
                <li key={q.id} className="flex items-center gap-2">
                  <span className="font-mono">Q{q.question_number}</span>
                  <span className="text-text-secondary">
                    {!q.is_enriched ? "Not enriched" : "Validation failed"}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Sync Preview Section
// ---------------------------------------------------------------------------

export function SyncPreviewSection({
  syncPreview,
  loadingPreview,
  previewError,
  onRefresh,
  onViewDiff,
}: {
  syncPreview: TestSyncPreview | null;
  loadingPreview: boolean;
  previewError: string | null;
  onRefresh: () => void;
  onViewDiff?: () => void;
}) {
  const qSum = syncPreview?.question_summary ?? syncPreview?.summary;
  const vSum = syncPreview?.variant_summary;

  return (
    <section className="bg-surface border border-border rounded-lg">
      <div className="px-4 py-3 border-b border-border flex items-center justify-between">
        <h3 className="font-medium">Sync Preview - What Will Happen</h3>
        <button
          onClick={onRefresh}
          disabled={loadingPreview}
          className={cn(
            "text-xs text-accent hover:underline flex items-center gap-1",
            "disabled:opacity-50",
          )}
        >
          <RefreshCw className={cn("w-3 h-3", loadingPreview && "animate-spin")} />
          Refresh
        </button>
      </div>
      <div className="p-4">
        {loadingPreview ? (
          <div className="flex items-center justify-center py-8 text-text-secondary">
            <Loader2 className="w-5 h-5 animate-spin mr-2" />
            Loading sync preview...
          </div>
        ) : previewError ? (
          <PreviewError error={previewError} onRetry={onRefresh} />
        ) : syncPreview && qSum ? (
          <PreviewContent
            qSum={qSum}
            vSum={vSum ?? null}
            syncPreview={syncPreview}
            onViewDiff={onViewDiff}
          />
        ) : (
          <p className="text-sm text-text-secondary">No preview available</p>
        )}
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Small helper components
// ---------------------------------------------------------------------------

function PreviewError({
  error,
  onRetry,
}: {
  error: string;
  onRetry: () => void;
}) {
  return (
    <div className="p-3 bg-error/10 border border-error/20 rounded-lg">
      <p className="text-sm text-error">{error}</p>
      <button
        onClick={onRetry}
        className="mt-2 text-xs text-accent hover:underline"
      >
        Retry
      </button>
    </div>
  );
}

function PreviewContent({
  qSum,
  vSum,
  syncPreview,
  onViewDiff,
}: {
  qSum: { create: number; update: number; unchanged: number; skipped: number };
  vSum: { create: number; update: number; unchanged: number; skipped: number } | null;
  syncPreview: TestSyncPreview;
  onViewDiff?: () => void;
}) {
  return (
    <>
      <div className="space-y-3">
        <PreviewEntityRow label="Questions" summary={qSum} />
        {vSum && <PreviewEntityRow label="Variants" summary={vSum} />}

        {syncPreview.questions.skipped.length > 0 && (
          <SkippedList label="questions" items={syncPreview.questions.skipped} />
        )}

        {syncPreview.variants?.skipped?.length > 0 && (
          <SkippedList label="variants" items={syncPreview.variants.skipped} />
        )}

        <div>
          <p className="text-sm font-medium mb-2">Images:</p>
          <div className="flex gap-4 text-sm text-text-secondary">
            <span>Will upload new images to S3 (upload_images: true)</span>
          </div>
        </div>
      </div>

      <div className="mt-4 p-3 bg-warning/10 border border-warning/20 rounded-lg">
        <p className="text-sm text-warning flex items-center gap-2">
          <AlertTriangle className="w-4 h-4" />
          Updates will OVERWRITE existing data in database
        </p>
      </div>

      {onViewDiff && (
        <button
          onClick={onViewDiff}
          className="mt-3 text-xs text-accent hover:underline"
        >
          View detailed diff &rarr;
        </button>
      )}
    </>
  );
}

/** Single row showing create/update/unchanged/skipped counts. */
function PreviewEntityRow({
  label,
  summary,
}: {
  label: string;
  summary: { create: number; update: number; unchanged: number; skipped: number };
}) {
  return (
    <div>
      <p className="text-sm font-medium mb-2">{label}:</p>
      <div className="flex gap-4 text-sm">
        <span className="text-success">+ INSERT {summary.create} new</span>
        <span className="text-accent">~ UPDATE {summary.update} existing</span>
        <span className="text-text-secondary">
          = UNCHANGED {summary.unchanged}
        </span>
        {summary.skipped > 0 && (
          <span className="text-warning">! SKIPPED {summary.skipped}</span>
        )}
      </div>
    </div>
  );
}

/** Collapsible list of skipped items with reasons. */
function SkippedList({
  label,
  items,
}: {
  label: string;
  items: Array<{ id: string; question_number: number; reason: string }>;
}) {
  return (
    <div className="text-xs bg-warning/10 border border-warning/20 rounded p-2">
      <p className="text-warning font-medium mb-1">
        Skipped {label} (not syncable):
      </p>
      <ul className="space-y-0.5">
        {items.slice(0, 5).map((q) => (
          <li key={q.id} className="text-text-secondary">
            Q{q.question_number}: {q.reason}
          </li>
        ))}
        {items.length > 5 && (
          <li className="text-text-secondary">
            ... and {items.length - 5} more
          </li>
        )}
      </ul>
    </div>
  );
}
