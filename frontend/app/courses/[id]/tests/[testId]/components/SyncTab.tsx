"use client";

import { useState, useEffect, useCallback } from "react";
import {
  AlertTriangle,
  Upload,
  RefreshCw,
  ChevronDown,
  ChevronRight,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { QuestionBrief, TestDetail, TestSyncPreview } from "@/lib/api";
import { getTestSyncPreview } from "@/lib/api";

export interface SyncTabProps {
  subjectId: string;
  testId: string;
  questions: QuestionBrief[];
  data: TestDetail;
  onSync: () => void;
  onViewDiff?: () => void;
}

export function SyncTab({
  subjectId,
  testId,
  questions,
  data,
  onSync,
  onViewDiff,
}: SyncTabProps) {
  const [selectedEnv, setSelectedEnv] = useState<"local" | "staging" | "prod">("local");
  const [showBlockedDetails, setShowBlockedDetails] = useState(false);
  const [syncPreview, setSyncPreview] = useState<TestSyncPreview | null>(null);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);

  // Calculate sync eligibility
  const validatedQuestions = questions.filter((q) => q.is_validated);
  const blockedQuestions = questions.filter((q) => !q.is_validated && q.is_tagged);
  const notEnrichedCount = blockedQuestions.filter((q) => !q.is_enriched).length;
  const failedValidationCount = blockedQuestions.filter(
    (q) => q.is_enriched && !q.is_validated
  ).length;

  // Fetch sync preview from API
  const fetchSyncPreview = useCallback(async () => {
    setLoadingPreview(true);
    setPreviewError(null);
    try {
      const preview = await getTestSyncPreview(subjectId, testId, {
        include_variants: true,
        upload_images: true,
      });
      setSyncPreview(preview);
    } catch (err) {
      setPreviewError(err instanceof Error ? err.message : "Failed to load preview");
    } finally {
      setLoadingPreview(false);
    }
  }, [subjectId, testId]);

  useEffect(() => {
    fetchSyncPreview();
  }, [fetchSyncPreview]);

  const totalChanges = syncPreview
    ? syncPreview.summary.create + syncPreview.summary.update
    : 0;

  return (
    <div className="p-6 space-y-6">
      {/* Environment selector */}
      <div className="flex items-center gap-4">
        <span className="text-sm text-text-secondary">Environment:</span>
        <div className="flex gap-1 bg-surface border border-border rounded-lg p-1">
          {(["local", "staging", "prod"] as const).map((env) => (
            <button
              key={env}
              onClick={() => setSelectedEnv(env)}
              className={cn(
                "px-4 py-1.5 text-sm rounded-md transition-colors",
                selectedEnv === env
                  ? "bg-accent text-white"
                  : "text-text-secondary hover:text-text-primary"
              )}
            >
              {env === "prod" ? "Production" : env.charAt(0).toUpperCase() + env.slice(1)}
            </button>
          ))}
        </div>
        {selectedEnv === "prod" && (
          <span className="text-xs text-warning flex items-center gap-1">
            <AlertTriangle className="w-3 h-3" />
            Production database
          </span>
        )}
      </div>

      {/* Main content - three sections */}
      <div className="grid gap-6">
        {/* Current DB State */}
        <section className="bg-surface border border-border rounded-lg">
          <div className="px-4 py-3 border-b border-border flex items-center justify-between">
            <h3 className="font-medium">Current Database State</h3>
            <button className="text-xs text-accent hover:underline flex items-center gap-1">
              <RefreshCw className="w-3 h-3" />
              Refresh
            </button>
          </div>
          <div className="p-4">
            <p className="text-sm text-text-secondary mb-4">
              What's currently in your{" "}
              <span className="font-medium text-text-primary">
                {selectedEnv === "prod" ? "Production" : selectedEnv}
              </span>{" "}
              database for this test:
            </p>
            <div className="grid grid-cols-3 gap-4">
              <div className="text-center p-3 bg-background rounded-lg">
                <p className="text-2xl font-semibold">—</p>
                <p className="text-xs text-text-secondary">Questions</p>
              </div>
              <div className="text-center p-3 bg-background rounded-lg">
                <p className="text-2xl font-semibold">—</p>
                <p className="text-xs text-text-secondary">Variants</p>
              </div>
              <div className="text-center p-3 bg-background rounded-lg">
                <p className="text-2xl font-semibold">—</p>
                <p className="text-xs text-text-secondary">Images</p>
              </div>
            </div>
            <button className="mt-3 text-xs text-accent hover:underline">
              View current DB questions →
            </button>
          </div>
        </section>

        {/* Local State */}
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
                  <td className="py-2 text-right font-mono text-success">{validatedQuestions.length}</td>
                  <td className="py-2 text-right font-mono text-warning">{blockedQuestions.length}</td>
                  <td className="py-2 text-text-secondary text-xs">
                    {notEnrichedCount > 0 && `${notEnrichedCount} not enriched`}
                    {notEnrichedCount > 0 && failedValidationCount > 0 && ", "}
                    {failedValidationCount > 0 && `${failedValidationCount} failed validation`}
                  </td>
                </tr>
                <tr>
                  <td className="py-2">Variants</td>
                  <td className="py-2 text-right font-mono text-success">—</td>
                  <td className="py-2 text-right font-mono text-warning">—</td>
                  <td className="py-2 text-text-secondary text-xs">Requires variant validation data</td>
                </tr>
                <tr>
                  <td className="py-2">Images</td>
                  <td className="py-2 text-right font-mono text-success">—</td>
                  <td className="py-2 text-right font-mono">0</td>
                  <td className="py-2 text-text-secondary text-xs">—</td>
                </tr>
              </tbody>
            </table>

            {blockedQuestions.length > 0 && (
              <button
                onClick={() => setShowBlockedDetails(!showBlockedDetails)}
                className="mt-3 text-xs text-accent hover:underline flex items-center gap-1"
              >
                {showBlockedDetails ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                View blocked items
              </button>
            )}

            {showBlockedDetails && (
              <div className="mt-3 bg-background rounded-lg p-3 max-h-40 overflow-y-auto">
                <p className="text-xs text-text-secondary mb-2">Questions that can't sync:</p>
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

        {/* Sync Preview */}
        <section className="bg-surface border border-border rounded-lg">
          <div className="px-4 py-3 border-b border-border flex items-center justify-between">
            <h3 className="font-medium">Sync Preview - What Will Happen</h3>
            <button
              onClick={fetchSyncPreview}
              disabled={loadingPreview}
              className="text-xs text-accent hover:underline flex items-center gap-1 disabled:opacity-50"
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
              <div className="p-3 bg-error/10 border border-error/20 rounded-lg">
                <p className="text-sm text-error">{previewError}</p>
                <button
                  onClick={fetchSyncPreview}
                  className="mt-2 text-xs text-accent hover:underline"
                >
                  Retry
                </button>
              </div>
            ) : syncPreview ? (
              <>
                <div className="space-y-3">
                  <div>
                    <p className="text-sm font-medium mb-2">Questions:</p>
                    <div className="flex gap-4 text-sm">
                      <span className="text-success">✚ INSERT {syncPreview.summary.create} new</span>
                      <span className="text-accent">✎ UPDATE {syncPreview.summary.update} existing</span>
                      <span className="text-text-secondary">
                        ○ UNCHANGED {syncPreview.summary.unchanged}
                      </span>
                      {syncPreview.summary.skipped > 0 && (
                        <span className="text-warning">
                          ⚠ SKIPPED {syncPreview.summary.skipped}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Show skipped questions with reasons */}
                  {syncPreview.questions.skipped.length > 0 && (
                    <div className="text-xs bg-warning/10 border border-warning/20 rounded p-2">
                      <p className="text-warning font-medium mb-1">
                        Skipped questions (not syncable):
                      </p>
                      <ul className="space-y-0.5">
                        {syncPreview.questions.skipped.slice(0, 5).map((q) => (
                          <li key={q.id} className="text-text-secondary">
                            Q{q.question_number}: {q.reason}
                          </li>
                        ))}
                        {syncPreview.questions.skipped.length > 5 && (
                          <li className="text-text-secondary">
                            ... and {syncPreview.questions.skipped.length - 5} more
                          </li>
                        )}
                      </ul>
                    </div>
                  )}

                  <div>
                    <p className="text-sm font-medium mb-2">Variants:</p>
                    <div className="flex gap-4 text-sm text-text-secondary">
                      <span>Included with question sync (include_variants: true)</span>
                    </div>
                  </div>

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
                    View detailed diff →
                  </button>
                )}
              </>
            ) : (
              <p className="text-sm text-text-secondary">No preview available</p>
            )}
          </div>
        </section>
      </div>

      {/* Sync action */}
      <div className="bg-surface border border-border rounded-lg p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="font-medium">
              Ready to sync {syncPreview?.summary.create ?? 0} new +{" "}
              {syncPreview?.summary.update ?? 0} updates
            </p>
            <p className="text-sm text-text-secondary">
              {totalChanges} total changes to{" "}
              {selectedEnv === "prod" ? "Production" : selectedEnv} database
            </p>
          </div>
          <button
            onClick={onSync}
            disabled={validatedQuestions.length === 0 || loadingPreview}
            className={cn(
              "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium",
              selectedEnv === "prod"
                ? "bg-error text-white hover:bg-error/90"
                : "bg-accent text-white hover:bg-accent/90",
              "disabled:opacity-50"
            )}
          >
            <Upload className="w-4 h-4" />
            Sync to{" "}
            {selectedEnv === "prod"
              ? "Production"
              : selectedEnv.charAt(0).toUpperCase() + selectedEnv.slice(1)}
          </button>
        </div>
      </div>
    </div>
  );
}
