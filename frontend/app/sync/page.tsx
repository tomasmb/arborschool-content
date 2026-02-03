"use client";

import { useState, useEffect } from "react";
import {
  Database,
  AlertTriangle,
  RefreshCw,
  CheckCircle,
  XCircle,
  Loader2,
  AlertCircle,
} from "lucide-react";
import {
  getSyncStatus,
  previewSync,
  executeSync,
  getOverview,
  SyncPreviewResponse,
  SyncExecuteResponse,
  SyncStatus,
} from "@/lib/api";

interface EntityOption {
  id: string;
  label: string;
  count: number | null;
  loading: boolean;
}

export default function SyncPage() {
  // State for sync status and entity counts
  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null);
  const [entities, setEntities] = useState<EntityOption[]>([
    { id: "standards", label: "Standards", count: null, loading: true },
    { id: "atoms", label: "Atoms", count: null, loading: true },
    { id: "tests", label: "Tests", count: null, loading: true },
    { id: "questions", label: "Questions (Official)", count: null, loading: true },
    { id: "variants", label: "Questions (Variants)", count: null, loading: true },
  ]);
  const [selectedEntities, setSelectedEntities] = useState<Set<string>>(
    new Set(["standards", "atoms", "tests", "questions"])
  );
  const [includeVariants, setIncludeVariants] = useState(false);
  const [uploadImages, setUploadImages] = useState(false);

  // Preview state
  const [isPreviewLoading, setIsPreviewLoading] = useState(false);
  const [previewResult, setPreviewResult] = useState<SyncPreviewResponse | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);

  // Execute state
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [isExecuting, setIsExecuting] = useState(false);
  const [executeResult, setExecuteResult] = useState<SyncExecuteResponse | null>(null);
  const [executeError, setExecuteError] = useState<string | null>(null);

  // Load initial data
  useEffect(() => {
    async function loadData() {
      try {
        // Load sync status
        const status = await getSyncStatus();
        setSyncStatus(status);

        // Load entity counts from overview
        const overview = await getOverview();
        if (overview.subjects.length > 0) {
          const stats = overview.subjects[0].stats;
          setEntities([
            { id: "standards", label: "Standards", count: stats.standards_count, loading: false },
            { id: "atoms", label: "Atoms", count: stats.atoms_count, loading: false },
            { id: "tests", label: "Tests", count: stats.tests_count, loading: false },
            {
              id: "questions",
              label: "Questions (Official)",
              count: stats.questions_count,
              loading: false,
            },
            {
              id: "variants",
              label: "Questions (Variants)",
              count: stats.variants_count,
              loading: false,
            },
          ]);
        }
      } catch (err) {
        console.error("Failed to load sync data:", err);
        setEntities((prev) => prev.map((e) => ({ ...e, loading: false })));
      }
    }
    loadData();
  }, []);

  // Toggle entity selection
  const toggleEntity = (entityId: string) => {
    setSelectedEntities((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(entityId)) {
        newSet.delete(entityId);
      } else {
        newSet.add(entityId);
      }
      // Sync variants checkbox with entity selection
      if (entityId === "variants") {
        setIncludeVariants(newSet.has("variants"));
      }
      return newSet;
    });
  };

  // Handle preview
  const handlePreview = async () => {
    setIsPreviewLoading(true);
    setPreviewError(null);
    setPreviewResult(null);
    setExecuteResult(null);

    try {
      const entitiesToSync = Array.from(selectedEntities);
      const result = await previewSync(entitiesToSync, includeVariants, uploadImages);
      setPreviewResult(result);
    } catch (err) {
      setPreviewError(err instanceof Error ? err.message : "Preview failed");
    } finally {
      setIsPreviewLoading(false);
    }
  };

  // Handle execute
  const handleExecute = async () => {
    setIsExecuting(true);
    setExecuteError(null);

    try {
      const entitiesToSync = Array.from(selectedEntities);
      const result = await executeSync(entitiesToSync, includeVariants, uploadImages, true);
      setExecuteResult(result);
      setShowConfirmModal(false);
    } catch (err) {
      setExecuteError(err instanceof Error ? err.message : "Sync failed");
    } finally {
      setIsExecuting(false);
    }
  };

  const canExecute = previewResult && previewResult.tables.length > 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Database Sync</h1>
        <p className="text-text-secondary mt-1">
          Sync content to the student-facing application database
        </p>
      </div>

      {/* Warning */}
      <div className="bg-warning/10 border border-warning/20 rounded-lg p-4 flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 text-warning flex-shrink-0 mt-0.5" />
        <div>
          <p className="font-medium text-warning">Production Database</p>
          <p className="text-sm text-text-secondary mt-1">
            This will modify the production database. Always run a preview first.
          </p>
        </div>
      </div>

      {/* Database configuration status */}
      {syncStatus && !syncStatus.database_configured && (
        <div className="bg-error/10 border border-error/20 rounded-lg p-4 flex items-start gap-3">
          <XCircle className="w-5 h-5 text-error flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-medium text-error">Database Not Configured</p>
            <p className="text-sm text-text-secondary mt-1">
              Set HOST, DB_NAME, DB_USER, DB_PASSWORD environment variables to enable sync.
            </p>
          </div>
        </div>
      )}

      {/* Entity selection */}
      <div className="bg-surface border border-border rounded-lg p-6">
        <h2 className="font-medium mb-4">Entities to Sync</h2>

        <div className="space-y-3">
          {entities.map((entity) => (
            <label
              key={entity.id}
              className="flex items-center gap-3 p-3 border border-border rounded-lg hover:bg-white/5 cursor-pointer"
            >
              <input
                type="checkbox"
                checked={selectedEntities.has(entity.id)}
                onChange={() => toggleEntity(entity.id)}
                className="w-4 h-4 rounded border-border"
              />
              <span className="flex-1">{entity.label}</span>
              <span className="text-text-secondary text-sm">
                {entity.loading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  `(${entity.count ?? "?"})`
                )}
              </span>
            </label>
          ))}
        </div>

        {/* Options */}
        <div className="mt-4 pt-4 border-t border-border">
          <label className="flex items-center gap-3 p-2 hover:bg-white/5 rounded cursor-pointer">
            <input
              type="checkbox"
              checked={uploadImages}
              onChange={(e) => setUploadImages(e.target.checked)}
              className="w-4 h-4 rounded border-border"
            />
            <span>Upload images to S3</span>
            {syncStatus && !syncStatus.s3_configured && (
              <span className="text-warning text-xs">(not configured)</span>
            )}
          </label>
        </div>

        <div className="mt-6 flex gap-3">
          <button
            onClick={handlePreview}
            disabled={isPreviewLoading || selectedEntities.size === 0}
            className={[
              "flex items-center gap-2 px-4 py-2 bg-surface border border-border",
              "rounded-lg text-sm hover:bg-white/5 transition-colors",
              "disabled:opacity-50 disabled:cursor-not-allowed",
            ].join(" ")}
          >
            {isPreviewLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <RefreshCw className="w-4 h-4" />
            )}
            Preview Changes (Dry Run)
          </button>
          <button
            onClick={() => setShowConfirmModal(true)}
            disabled={!canExecute || isExecuting}
            className={[
              "flex items-center gap-2 px-4 py-2 bg-accent text-white rounded-lg",
              "text-sm hover:bg-accent/90 transition-colors",
              "disabled:opacity-50 disabled:cursor-not-allowed",
            ].join(" ")}
          >
            <Database className="w-4 h-4" />
            Execute Sync
          </button>
        </div>
      </div>

      {/* Preview error */}
      {previewError && (
        <div className="bg-error/10 border border-error/20 rounded-lg p-4 flex items-start gap-3">
          <XCircle className="w-5 h-5 text-error flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-medium text-error">Preview Failed</p>
            <p className="text-sm text-text-secondary mt-1">{previewError}</p>
          </div>
        </div>
      )}

      {/* Preview results */}
      <div className="bg-surface border border-border rounded-lg p-6">
        <h2 className="font-medium mb-4">Preview Results</h2>

        {!previewResult && !previewError && (
          <div className="text-center py-8 text-text-secondary">
            <Database className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p>Run a preview to see changes</p>
          </div>
        )}

        {previewResult && (
          <>
            {/* Warnings */}
            {previewResult.warnings.length > 0 && (
              <div className="mb-4 space-y-2">
                {previewResult.warnings.map((warning, idx) => (
                  <div
                    key={idx}
                    className="flex items-start gap-2 text-warning text-sm p-2 bg-warning/10 rounded"
                  >
                    <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                    {warning}
                  </div>
                ))}
              </div>
            )}

            {/* Results table */}
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left py-2 px-3 font-medium">Table</th>
                    <th className="text-right py-2 px-3 font-medium">Rows to Upsert</th>
                    <th className="text-left py-2 px-3 font-medium">Breakdown</th>
                  </tr>
                </thead>
                <tbody>
                  {previewResult.tables.map((table) => (
                    <tr key={table.table} className="border-b border-border/50">
                      <td className="py-2 px-3 font-mono text-xs">{table.table}</td>
                      <td className="py-2 px-3 text-right">{table.total}</td>
                      <td className="py-2 px-3 text-text-secondary text-xs">
                        {Object.entries(table.breakdown || {})
                          .map(([k, v]) => `${k}: ${v}`)
                          .join(", ") || "-"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {previewResult.tables.length === 0 && (
              <p className="text-text-secondary text-center py-4">No data to sync.</p>
            )}
          </>
        )}
      </div>

      {/* Execute result */}
      {executeResult && (
        <div
          className={`border rounded-lg p-4 flex items-start gap-3 ${
            executeResult.success
              ? "bg-success/10 border-success/20"
              : "bg-error/10 border-error/20"
          }`}
        >
          {executeResult.success ? (
            <CheckCircle className="w-5 h-5 text-success flex-shrink-0 mt-0.5" />
          ) : (
            <XCircle className="w-5 h-5 text-error flex-shrink-0 mt-0.5" />
          )}
          <div className="flex-1">
            <p
              className={`font-medium ${executeResult.success ? "text-success" : "text-error"}`}
            >
              {executeResult.success ? "Sync Completed" : "Sync Failed"}
            </p>
            <p className="text-sm text-text-secondary mt-1">{executeResult.message}</p>
            {executeResult.success && Object.keys(executeResult.results).length > 0 && (
              <div className="mt-2 text-sm">
                <p className="text-text-secondary">Rows affected:</p>
                <ul className="mt-1 space-y-1">
                  {Object.entries(executeResult.results).map(([table, count]) => (
                    <li key={table} className="flex justify-between max-w-xs">
                      <span className="font-mono text-xs">{table}</span>
                      <span>{count}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {executeResult.errors.length > 0 && (
              <ul className="mt-2 text-sm text-error space-y-1">
                {executeResult.errors.map((err, idx) => (
                  <li key={idx}>{err}</li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}

      {/* Confirmation Modal */}
      {showConfirmModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="bg-surface border border-border rounded-lg p-6 max-w-md w-full mx-4 shadow-xl">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-6 h-6 text-warning flex-shrink-0" />
              <div>
                <h3 className="font-semibold text-lg">Confirm Sync</h3>
                <p className="text-text-secondary mt-2">
                  You are about to sync data to the <strong>production database</strong>.
                  This action will upsert rows to the following tables:
                </p>
                {previewResult && (
                  <ul className="mt-2 text-sm space-y-1">
                    {previewResult.tables.map((t) => (
                      <li key={t.table} className="flex justify-between">
                        <span className="font-mono text-xs">{t.table}</span>
                        <span className="text-text-secondary">{t.total} rows</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setShowConfirmModal(false)}
                disabled={isExecuting}
                className="px-4 py-2 border border-border rounded-lg text-sm hover:bg-white/5 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleExecute}
                disabled={isExecuting}
                className={[
                  "flex items-center gap-2 px-4 py-2 bg-warning text-black rounded-lg",
                  "text-sm font-medium hover:bg-warning/90 transition-colors disabled:opacity-50",
                ].join(" ")}
              >
                {isExecuting ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Database className="w-4 h-4" />
                )}
                {isExecuting ? "Syncing..." : "Yes, Execute Sync"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
