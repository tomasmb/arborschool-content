"use client";

import { useState, useEffect, useCallback } from "react";
import { AlertTriangle, Upload, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { ActionButton } from "@/components/ui";
import type {
  AtomPipelineSummary,
  CourseSyncPreview,
  CourseSyncResult,
  CourseSyncDiff,
  CourseSyncEntityDiff,
} from "@/lib/api";
import {
  getCourseSyncPreview,
  executeCourseSyncAPI,
  getCourseSyncDiff,
} from "@/lib/api";
import {
  BlockedSection,
  DbStateSection,
  LocalStateSection,
  PreviewSection,
  SyncResultSection,
} from "./AtomSyncSubComponents";

export type SyncEnvironment = "local" | "staging" | "prod";

// Atom sync: push atoms, standards, and question-atom links (tagging).
// Question content (QTI, difficulty, feedback) is synced separately
// from the test pipeline.
const SYNC_ENTITIES = ["standards", "atoms", "question_atoms"];

export const envLabel = (env: SyncEnvironment): string =>
  env === "prod"
    ? "Production"
    : env.charAt(0).toUpperCase() + env.slice(1);

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

/** Fetches diff + preview whenever subjectId or env changes. */
function useAtomSyncData(
  subjectId: string,
  selectedEnv: SyncEnvironment,
  isBlocked: boolean,
) {
  const [syncDiff, setSyncDiff] =
    useState<CourseSyncDiff | null>(null);
  const [diffLoading, setDiffLoading] = useState(false);
  const [syncPreview, setSyncPreview] =
    useState<CourseSyncPreview | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] =
    useState<string | null>(null);

  const fetchDiff = useCallback(async () => {
    setDiffLoading(true);
    try {
      setSyncDiff(
        await getCourseSyncDiff(subjectId, selectedEnv),
      );
    } catch {
      setSyncDiff(null);
    } finally {
      setDiffLoading(false);
    }
  }, [subjectId, selectedEnv]);

  const fetchPreview = useCallback(async () => {
    setPreviewLoading(true);
    setPreviewError(null);
    try {
      setSyncPreview(
        await getCourseSyncPreview(subjectId, {
          entities: SYNC_ENTITIES,
          environment: selectedEnv,
        }),
      );
    } catch (err) {
      setPreviewError(
        err instanceof Error
          ? err.message
          : "Failed to load preview",
      );
    } finally {
      setPreviewLoading(false);
    }
  }, [subjectId, selectedEnv]);

  useEffect(() => {
    if (!isBlocked) fetchDiff();
  }, [fetchDiff, isBlocked]);

  useEffect(() => {
    if (!isBlocked) fetchPreview();
  }, [fetchPreview, isBlocked]);

  const atomsTable =
    syncPreview?.tables.find((t) => t.table === "atoms") ??
    null;
  const questionAtomsTable =
    syncPreview?.tables.find(
      (t) => t.table === "question_atoms",
    ) ?? null;
  const atomsDiff: CourseSyncEntityDiff | null =
    syncDiff?.entities?.atoms ?? null;
  const questionAtomsDiff: CourseSyncEntityDiff | null =
    syncDiff?.entities?.question_atoms ?? null;

  return {
    syncDiff, diffLoading, fetchDiff,
    syncPreview, previewLoading, previewError, fetchPreview,
    atomsTable, questionAtomsTable, atomsDiff, questionAtomsDiff,
  };
}

/** Handles sync execution and result state. */
function useAtomSyncExec(
  subjectId: string,
  selectedEnv: SyncEnvironment,
  onSuccess?: () => void,
) {
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] =
    useState<CourseSyncResult | null>(null);

  // Reset result when env changes
  useEffect(() => {
    setSyncResult(null);
  }, [selectedEnv]);

  const handleSync = useCallback(
    async (refreshCbs: (() => void)[]) => {
      setSyncing(true);
      setSyncResult(null);
      try {
        const result = await executeCourseSyncAPI(
          subjectId,
          {
            entities: SYNC_ENTITIES,
            environment: selectedEnv,
            confirm: true,
          },
        );
        setSyncResult(result);
        if (result.success) {
          onSuccess?.();
          refreshCbs.forEach((cb) => cb());
        }
      } catch (err) {
        const msg =
          err instanceof Error
            ? err.message
            : "Sync failed";
        setSyncResult({
          success: false,
          results: {},
          message: msg,
          errors: [msg],
          environment: selectedEnv,
        });
      } finally {
        setSyncing(false);
      }
    },
    [subjectId, selectedEnv, onSuccess],
  );

  return { syncing, syncResult, handleSync };
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

interface AtomSyncTabProps {
  subjectId: string;
  summary: AtomPipelineSummary;
  onSyncComplete?: () => void;
}

export function AtomSyncTab({
  subjectId,
  summary,
  onSyncComplete,
}: AtomSyncTabProps) {
  const [selectedEnv, setSelectedEnv] =
    useState<SyncEnvironment>("local");

  const isBlocked =
    summary.atom_count === 0 ||
    summary.standards_validated === 0 ||
    summary.structural_checks_passed === false;

  const data = useAtomSyncData(
    subjectId,
    selectedEnv,
    isBlocked,
  );
  const exec = useAtomSyncExec(
    subjectId,
    selectedEnv,
    onSyncComplete,
  );

  return (
    <div className="p-6 space-y-6">
      <EnvironmentSelector
        selectedEnv={selectedEnv}
        onSelect={setSelectedEnv}
      />

      {isBlocked && <BlockedSection summary={summary} />}

      {!isBlocked && (
        <div className="grid gap-6">
          <DbStateSection
            envLabel={envLabel(selectedEnv)}
            syncDiff={data.syncDiff}
            atomsDiff={data.atomsDiff}
            questionAtomsDiff={data.questionAtomsDiff}
            loading={data.diffLoading}
            onRefresh={data.fetchDiff}
          />
          <LocalStateSection summary={summary} />
          <PreviewSection
            syncPreview={data.syncPreview}
            atomsTable={data.atomsTable}
            atomsDiff={data.atomsDiff}
            questionAtomsDiff={data.questionAtomsDiff}
            loading={data.previewLoading}
            error={data.previewError}
            warnings={data.syncPreview?.warnings ?? []}
            onRefresh={data.fetchPreview}
          />
          {exec.syncResult && (
            <SyncResultSection result={exec.syncResult} />
          )}
        </div>
      )}

      {!isBlocked && (
        <SyncActionBar
          atomsTable={data.atomsTable}
          questionAtomsTable={data.questionAtomsTable}
          atomsDiff={data.atomsDiff}
          questionAtomsDiff={data.questionAtomsDiff}
          selectedEnv={selectedEnv}
          syncing={exec.syncing}
          previewLoading={data.previewLoading}
          onSync={() =>
            exec.handleSync([
              data.fetchDiff,
              data.fetchPreview,
            ])
          }
        />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Small layout sub-components
// ---------------------------------------------------------------------------

function EnvironmentSelector({
  selectedEnv,
  onSelect,
}: {
  selectedEnv: SyncEnvironment;
  onSelect: (env: SyncEnvironment) => void;
}) {
  return (
    <div className="flex items-center gap-4">
      <span className="text-sm text-text-secondary">
        Environment:
      </span>
      <div className="flex gap-1 bg-surface border border-border rounded-lg p-1">
        {(["local", "staging", "prod"] as const).map(
          (env) => (
            <button
              key={env}
              onClick={() => onSelect(env)}
              className={cn(
                "px-4 py-1.5 text-sm rounded-md transition-colors",
                selectedEnv === env
                  ? "bg-accent text-white"
                  : "text-text-secondary hover:text-text-primary",
              )}
            >
              {envLabel(env)}
            </button>
          ),
        )}
      </div>
      {selectedEnv === "prod" && (
        <span className="text-xs text-warning flex items-center gap-1">
          <AlertTriangle className="w-3 h-3" />
          Production database
        </span>
      )}
    </div>
  );
}

function SyncActionBar({
  atomsTable,
  questionAtomsTable,
  atomsDiff,
  questionAtomsDiff,
  selectedEnv,
  syncing,
  previewLoading,
  onSync,
}: {
  atomsTable: { total: number } | null;
  questionAtomsTable: { total: number } | null;
  atomsDiff: CourseSyncEntityDiff | null;
  questionAtomsDiff: CourseSyncEntityDiff | null;
  selectedEnv: SyncEnvironment;
  syncing: boolean;
  previewLoading: boolean;
  onSync: () => void;
}) {
  const qaCount = questionAtomsTable?.total ?? 0;

  // Build a concise summary line
  const parts: string[] = [];
  if (atomsDiff) {
    const aParts: string[] = [];
    if (atomsDiff.new_count > 0) aParts.push(`${atomsDiff.new_count} new`);
    if (atomsDiff.modified_count > 0) aParts.push(`${atomsDiff.modified_count} modified`);
    if (atomsDiff.deleted_count > 0) aParts.push(`${atomsDiff.deleted_count} deleted`);
    if (aParts.length > 0) parts.push(`Atoms: ${aParts.join(", ")}`);
  }
  if (questionAtomsDiff) {
    const qParts: string[] = [];
    if (questionAtomsDiff.new_count > 0) qParts.push(`${questionAtomsDiff.new_count} new`);
    if (questionAtomsDiff.modified_count > 0) qParts.push(`${questionAtomsDiff.modified_count} modified`);
    if (questionAtomsDiff.deleted_count > 0) qParts.push(`${questionAtomsDiff.deleted_count} deleted`);
    if (qParts.length > 0) parts.push(`Links: ${qParts.join(", ")}`);
  }
  const summaryLine = parts.length > 0
    ? parts.join(" · ")
    : `To ${envLabel(selectedEnv)} database`;

  return (
    <div
      className={cn(
        "sticky bottom-0 z-10",
        "bg-surface/95 backdrop-blur-sm",
        "border border-border rounded-lg p-4",
        "shadow-[0_-4px_12px_rgba(0,0,0,0.3)]",
      )}
    >
      <div className="flex items-center justify-between">
        <div>
          <p className="font-medium">
            Ready to sync {atomsTable?.total ?? 0} atoms
            {qaCount > 0 && ` + ${qaCount} question links`}
          </p>
          <p className="text-sm text-text-secondary">
            {summaryLine}
          </p>
        </div>
        <ActionButton
          variant={
            selectedEnv === "prod" ? "danger" : "primary"
          }
          size="lg"
          icon={
            syncing ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Upload className="w-4 h-4" />
            )
          }
          onClick={onSync}
          disabled={
            syncing ||
            previewLoading ||
            (atomsTable?.total ?? 0) === 0
          }
        >
          {syncing
            ? "Syncing..."
            : `Sync to ${envLabel(selectedEnv)}`}
        </ActionButton>
      </div>
    </div>
  );
}
