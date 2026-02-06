"use client";

import { useState, useEffect, useCallback } from "react";
import { AlertTriangle, Upload } from "lucide-react";
import { cn } from "@/lib/utils";
import { ActionButton } from "@/components/ui";
import type {
  QuestionBrief,
  TestDetail,
  TestSyncPreview,
  TestSyncDiff,
} from "@/lib/api";
import { getTestSyncDiff, getTestSyncPreview } from "@/lib/api";
import {
  DbStateSection,
  LocalStateSection,
  SyncPreviewSection,
} from "./SyncSubComponents";

export interface SyncTabProps {
  subjectId: string;
  testId: string;
  questions: QuestionBrief[];
  data: TestDetail;
  onSync: () => void;
  onViewDiff?: () => void;
}

type SyncEnvironment = "local" | "staging" | "prod";

export function SyncTab({
  subjectId,
  testId,
  questions,
  data,
  onSync,
  onViewDiff,
}: SyncTabProps) {
  const [selectedEnv, setSelectedEnv] = useState<SyncEnvironment>("local");
  const [showBlockedDetails, setShowBlockedDetails] = useState(false);

  // DB diff state
  const [syncDiff, setSyncDiff] = useState<TestSyncDiff | null>(null);
  const [diffLoading, setDiffLoading] = useState(false);

  // Sync preview state
  const [syncPreview, setSyncPreview] = useState<TestSyncPreview | null>(null);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);

  // Calculate sync eligibility from local question list
  const validatedQuestions = questions.filter((q) => q.is_validated);
  const blockedQuestions = questions.filter(
    (q) => !q.is_validated && q.is_tagged,
  );
  const notEnrichedCount = blockedQuestions.filter(
    (q) => !q.is_enriched,
  ).length;
  const failedValidationCount = blockedQuestions.filter(
    (q) => q.is_enriched && !q.is_validated,
  ).length;

  // --- Fetch DB diff ---
  const fetchDiff = useCallback(async () => {
    setDiffLoading(true);
    try {
      const diff = await getTestSyncDiff(subjectId, testId, selectedEnv);
      setSyncDiff(diff);
    } catch {
      setSyncDiff(null);
    } finally {
      setDiffLoading(false);
    }
  }, [subjectId, testId, selectedEnv]);

  useEffect(() => {
    fetchDiff();
  }, [fetchDiff]);

  // --- Fetch sync preview ---
  const fetchSyncPreview = useCallback(async () => {
    setLoadingPreview(true);
    setPreviewError(null);
    try {
      const preview = await getTestSyncPreview(subjectId, testId, {
        environment: selectedEnv,
        include_variants: true,
        upload_images: true,
      });
      setSyncPreview(preview);
    } catch (err) {
      setPreviewError(
        err instanceof Error ? err.message : "Failed to load preview",
      );
    } finally {
      setLoadingPreview(false);
    }
  }, [subjectId, testId, selectedEnv]);

  useEffect(() => {
    fetchSyncPreview();
  }, [fetchSyncPreview]);

  // Computed totals
  const totalChanges = syncPreview
    ? syncPreview.summary.create + syncPreview.summary.update
    : 0;

  const envLabel = (env: SyncEnvironment) =>
    env === "prod"
      ? "Production"
      : env.charAt(0).toUpperCase() + env.slice(1);

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
                  : "text-text-secondary hover:text-text-primary",
              )}
            >
              {envLabel(env)}
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
        <DbStateSection
          envLabel={envLabel(selectedEnv)}
          syncDiff={syncDiff}
          loading={diffLoading}
          onRefresh={fetchDiff}
        />

        <LocalStateSection
          validatedQuestions={validatedQuestions}
          blockedQuestions={blockedQuestions}
          notEnrichedCount={notEnrichedCount}
          failedValidationCount={failedValidationCount}
          showBlockedDetails={showBlockedDetails}
          onToggleBlocked={() => setShowBlockedDetails(!showBlockedDetails)}
          syncDiff={syncDiff}
        />

        <SyncPreviewSection
          syncPreview={syncPreview}
          loadingPreview={loadingPreview}
          previewError={previewError}
          onRefresh={fetchSyncPreview}
          onViewDiff={onViewDiff}
        />
      </div>

      {/* Sticky sync action bar */}
      <div
        className={cn(
          "sticky bottom-0 z-10",
          "bg-surface/95 backdrop-blur-sm border border-border rounded-lg p-4",
          "shadow-[0_-4px_12px_rgba(0,0,0,0.3)]",
        )}
      >
        <div className="flex items-center justify-between">
          <div>
            <p className="font-medium">
              Ready to sync {syncPreview?.summary.create ?? 0} new +{" "}
              {syncPreview?.summary.update ?? 0} updates
            </p>
            <p className="text-sm text-text-secondary">
              {totalChanges} total changes to {envLabel(selectedEnv)} database
            </p>
          </div>
          <ActionButton
            variant={selectedEnv === "prod" ? "danger" : "primary"}
            size="lg"
            icon={<Upload className="w-4 h-4" />}
            onClick={onSync}
            disabled={validatedQuestions.length === 0 || loadingPreview}
          >
            Sync to {envLabel(selectedEnv)}
          </ActionButton>
        </div>
      </div>
    </div>
  );
}
