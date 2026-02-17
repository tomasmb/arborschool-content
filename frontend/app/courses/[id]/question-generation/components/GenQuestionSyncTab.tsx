"use client";

import { useState, useEffect, useCallback } from "react";
import {
  AlertTriangle,
  Upload,
  Loader2,
  CheckCircle2,
  RefreshCw,
  Database,
  FileText,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { ActionButton } from "@/components/ui";
import {
  EnvironmentSelector,
  envLabel,
  type SyncEnvironment,
} from "@/components/sync";
import type {
  AtomBrief,
  CourseSyncPreview,
  CourseSyncResult,
} from "@/lib/api";
import {
  getCourseSyncPreview,
  executeCourseSyncAPI,
} from "@/lib/api";

const SYNC_ENTITIES = ["generated_questions"];

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

/** Fetches preview whenever subjectId or env changes. */
function useGenQPreview(
  subjectId: string,
  selectedEnv: SyncEnvironment,
) {
  const [preview, setPreview] =
    useState<CourseSyncPreview | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setPreview(
        await getCourseSyncPreview(subjectId, {
          entities: SYNC_ENTITIES,
          environment: selectedEnv,
        }),
      );
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to load preview",
      );
    } finally {
      setLoading(false);
    }
  }, [subjectId, selectedEnv]);

  useEffect(() => {
    fetch();
  }, [fetch]);

  const table =
    preview?.tables.find(
      (t) => t.table === "generated_questions",
    ) ?? null;

  return { preview, loading, error, table, refresh: fetch };
}

/** Handles sync execution and result state. */
function useGenQExec(
  subjectId: string,
  selectedEnv: SyncEnvironment,
) {
  const [syncing, setSyncing] = useState(false);
  const [result, setResult] =
    useState<CourseSyncResult | null>(null);

  // Reset result when env changes
  useEffect(() => {
    setResult(null);
  }, [selectedEnv]);

  const handleSync = useCallback(
    async (onSuccess?: () => void) => {
      setSyncing(true);
      setResult(null);
      try {
        const res = await executeCourseSyncAPI(subjectId, {
          entities: SYNC_ENTITIES,
          environment: selectedEnv,
          confirm: true,
        });
        setResult(res);
        if (res.success) onSuccess?.();
      } catch (err) {
        const msg =
          err instanceof Error
            ? err.message
            : "Sync failed";
        setResult({
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
    [subjectId, selectedEnv],
  );

  return { syncing, result, handleSync };
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

interface GenQuestionSyncTabProps {
  subjectId: string;
  atoms: AtomBrief[];
}

export function GenQuestionSyncTab({
  subjectId,
  atoms,
}: GenQuestionSyncTabProps) {
  const [selectedEnv, setSelectedEnv] =
    useState<SyncEnvironment>("local");
  const [prodAck, setProdAck] = useState(false);

  // Reset prod ack when switching envs
  useEffect(() => {
    setProdAck(false);
  }, [selectedEnv]);

  const data = useGenQPreview(subjectId, selectedEnv);
  const exec = useGenQExec(subjectId, selectedEnv);

  const readyAtoms = atoms.filter(
    (a) => a.last_completed_phase !== null && a.last_completed_phase >= 9,
  );
  const totalGenerated = atoms.reduce(
    (sum, a) => sum + a.generated_question_count, 0,
  );

  const isProd = selectedEnv === "prod";
  const canSync =
    !exec.syncing &&
    !data.loading &&
    (data.table?.total ?? 0) > 0 &&
    (!isProd || prodAck);

  return (
    <div className="p-6 space-y-6">
      <EnvironmentSelector
        selected={selectedEnv}
        onChange={setSelectedEnv}
      />

      <div className="grid gap-6">
        <LocalStateCard
          readyCount={readyAtoms.length}
          totalCount={atoms.length}
          totalGenerated={totalGenerated}
        />
        <PreviewCard
          preview={data.preview}
          table={data.table}
          loading={data.loading}
          error={data.error}
          envName={envLabel(selectedEnv)}
          onRefresh={data.refresh}
        />
        {exec.result && <ResultCard result={exec.result} />}
      </div>

      {/* Sticky sync action bar */}
      <SyncActionBar
        table={data.table}
        selectedEnv={selectedEnv}
        isProd={isProd}
        prodAck={prodAck}
        onProdAckChange={setProdAck}
        syncing={exec.syncing}
        canSync={canSync}
        onSync={() => exec.handleSync(data.refresh)}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function LocalStateCard({
  readyCount,
  totalCount,
  totalGenerated,
}: {
  readyCount: number;
  totalCount: number;
  totalGenerated: number;
}) {
  return (
    <div className="bg-surface border border-border rounded-lg p-4">
      <div className="flex items-center gap-2 mb-3">
        <FileText className="w-4 h-4 text-accent" />
        <h3 className="text-sm font-medium">Local State</h3>
      </div>
      <div className="grid grid-cols-3 gap-4 text-sm">
        <div>
          <p className="text-text-secondary">Atoms ready</p>
          <p className="text-lg font-semibold">
            {readyCount}
            <span className="text-sm font-normal text-text-secondary">
              {" "}/ {totalCount}
            </span>
          </p>
        </div>
        <div>
          <p className="text-text-secondary">
            Questions generated
          </p>
          <p className="text-lg font-semibold">
            {totalGenerated}
          </p>
        </div>
        <div>
          <p className="text-text-secondary">
            Pipeline phase required
          </p>
          <p className="text-lg font-semibold">≥ 9</p>
        </div>
      </div>
    </div>
  );
}

function PreviewCard({
  preview,
  table,
  loading,
  error,
  envName,
  onRefresh,
}: {
  preview: CourseSyncPreview | null;
  table: { total: number; breakdown: Record<string, number> } | null;
  loading: boolean;
  error: string | null;
  envName: string;
  onRefresh: () => void;
}) {
  return (
    <div className="bg-surface border border-border rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Database className="w-4 h-4 text-accent" />
          <h3 className="text-sm font-medium">
            Sync Preview — {envName}
          </h3>
        </div>
        <button
          onClick={onRefresh}
          disabled={loading}
          className="text-text-secondary hover:text-text-primary transition-colors"
        >
          <RefreshCw
            className={cn(
              "w-4 h-4",
              loading && "animate-spin",
            )}
          />
        </button>
      </div>

      {loading && (
        <div className="flex items-center gap-2 text-sm text-text-secondary py-4">
          <Loader2 className="w-4 h-4 animate-spin" />
          Loading preview…
        </div>
      )}

      {error && (
        <div className="text-sm text-error bg-error/10 border border-error/20 rounded-lg p-3">
          {error}
        </div>
      )}

      {!loading && !error && table && (
        <div className="space-y-3">
          <div className="bg-background rounded-lg p-3">
            <p className="text-sm font-medium mb-2">
              generated_questions
            </p>
            <p className="text-2xl font-semibold">
              {table.total}
              <span className="text-sm font-normal text-text-secondary ml-2">
                rows to upsert
              </span>
            </p>
            {Object.keys(table.breakdown).length > 0 && (
              <div className="mt-2 flex flex-wrap gap-2 text-xs text-text-secondary">
                {Object.entries(table.breakdown).map(
                  ([key, count]) => (
                    <span
                      key={key}
                      className="px-2 py-0.5 bg-surface rounded"
                    >
                      {key}: {count}
                    </span>
                  ),
                )}
              </div>
            )}
          </div>
          {(preview?.warnings?.length ?? 0) > 0 && (
            <div className="space-y-1">
              {preview!.warnings.map((w, i) => (
                <div
                  key={i}
                  className="flex items-start gap-2 text-xs text-warning"
                >
                  <AlertTriangle className="w-3 h-3 mt-0.5 shrink-0" />
                  {w}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {!loading && !error && !table && (
        <p className="text-sm text-text-secondary py-2">
          No generated questions found on disk.
        </p>
      )}
    </div>
  );
}

function ResultCard({ result }: { result: CourseSyncResult }) {
  return (
    <div
      className={cn(
        "border rounded-lg p-4",
        result.success
          ? "bg-success/5 border-success/20"
          : "bg-error/5 border-error/20",
      )}
    >
      <div className="flex items-center gap-2 mb-2">
        {result.success ? (
          <CheckCircle2 className="w-4 h-4 text-success" />
        ) : (
          <AlertTriangle className="w-4 h-4 text-error" />
        )}
        <h3
          className={cn(
            "text-sm font-medium",
            result.success ? "text-success" : "text-error",
          )}
        >
          {result.success ? "Sync Successful" : "Sync Failed"}
        </h3>
      </div>
      <p className="text-sm text-text-secondary">
        {result.message}
      </p>
      {result.errors.length > 0 && (
        <ul className="mt-2 space-y-1 text-xs text-error">
          {result.errors.map((e, i) => (
            <li key={i}>• {e}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function SyncActionBar({
  table,
  selectedEnv,
  isProd,
  prodAck,
  onProdAckChange,
  syncing,
  canSync,
  onSync,
}: {
  table: { total: number } | null;
  selectedEnv: SyncEnvironment;
  isProd: boolean;
  prodAck: boolean;
  onProdAckChange: (v: boolean) => void;
  syncing: boolean;
  canSync: boolean;
  onSync: () => void;
}) {
  const count = table?.total ?? 0;

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
            {count > 0
              ? `Ready to sync ${count} generated questions`
              : "No generated questions to sync"}
          </p>
          <p className="text-sm text-text-secondary">
            To {envLabel(selectedEnv)} database
          </p>
          {isProd && (
            <label className="flex items-center gap-2 mt-2 cursor-pointer">
              <input
                type="checkbox"
                checked={prodAck}
                onChange={(e) =>
                  onProdAckChange(e.target.checked)
                }
                disabled={syncing}
                className="w-4 h-4 rounded border-border"
              />
              <span className="text-xs text-warning">
                I understand this will write to production
              </span>
            </label>
          )}
        </div>
        <ActionButton
          variant={isProd ? "danger" : "primary"}
          size="lg"
          icon={
            syncing ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Upload className="w-4 h-4" />
            )
          }
          onClick={onSync}
          disabled={!canSync}
        >
          {syncing
            ? "Syncing…"
            : `Sync to ${envLabel(selectedEnv)}`}
        </ActionButton>
      </div>
    </div>
  );
}
