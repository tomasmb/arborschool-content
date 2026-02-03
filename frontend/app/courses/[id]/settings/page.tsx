"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  ArrowLeft,
  CheckCircle2,
  Circle,
  RefreshCw,
  AlertTriangle,
  Loader2,
} from "lucide-react";
import {
  getSyncStatus,
  previewCourseSync,
  executeCourseSync,
  type SyncStatus,
  type SyncPreviewResponse,
  type SyncExecuteResponse,
} from "@/lib/api";
import { cn } from "@/lib/utils";
import { useToast } from "@/components/ui";

type SyncStep = "idle" | "preview" | "confirm" | "syncing" | "done" | "error";

export default function SettingsPage() {
  const params = useParams();
  const courseId = params.id as string;
  const { showToast } = useToast();

  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Sync flow state
  const [syncStep, setSyncStep] = useState<SyncStep>("idle");
  const [preview, setPreview] = useState<SyncPreviewResponse | null>(null);
  const [syncResult, setSyncResult] = useState<SyncExecuteResponse | null>(null);

  // Sync options
  const [entities, setEntities] = useState<string[]>([
    "standards",
    "atoms",
    "tests",
    "questions",
  ]);
  const [includeVariants, setIncludeVariants] = useState(true);
  const [uploadImages, setUploadImages] = useState(false);

  useEffect(() => {
    if (courseId) {
      getSyncStatus()
        .then(setSyncStatus)
        .catch((err) => setError(err.message))
        .finally(() => setLoading(false));
    }
  }, [courseId]);

  const handlePreview = useCallback(async () => {
    setSyncStep("preview");
    setPreview(null);
    setSyncResult(null);

    try {
      const result = await previewCourseSync(
        courseId,
        entities,
        includeVariants,
        uploadImages
      );
      setPreview(result);
      setSyncStep("confirm");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Preview failed");
      setSyncStep("error");
    }
  }, [courseId, entities, includeVariants, uploadImages]);

  const handleSync = useCallback(async () => {
    setSyncStep("syncing");

    try {
      const result = await executeCourseSync(
        courseId,
        entities,
        includeVariants,
        uploadImages,
        true // confirm
      );
      setSyncResult(result);

      if (result.success) {
        setSyncStep("done");
        showToast("success", result.message);
      } else {
        setSyncStep("error");
        showToast("error", result.errors?.[0] || "Sync failed");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sync failed");
      setSyncStep("error");
      showToast("error", "Sync failed");
    }
  }, [courseId, entities, includeVariants, uploadImages, showToast]);

  const resetSync = useCallback(() => {
    setSyncStep("idle");
    setPreview(null);
    setSyncResult(null);
  }, []);

  const toggleEntity = (entity: string) => {
    setEntities((prev) =>
      prev.includes(entity) ? prev.filter((e) => e !== entity) : [...prev, entity]
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-text-secondary">Loading...</div>
      </div>
    );
  }

  if (error && syncStep === "idle") {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-error">Error: {error}</div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link
          href={`/courses/${courseId}`}
          className="p-2 hover:bg-white/5 rounded-lg transition-colors"
        >
          <ArrowLeft className="w-5 h-5 text-text-secondary" />
        </Link>
        <div>
          <h1 className="text-2xl font-semibold">Settings</h1>
          <p className="text-text-secondary mt-1">Course configuration and sync</p>
        </div>
      </div>

      {/* Configuration Status */}
      <section>
        <h2 className="text-lg font-semibold mb-4 text-text-secondary uppercase tracking-wide text-xs">
          Configuration
        </h2>

        <div className="bg-surface border border-border rounded-lg p-6">
          <div className="grid grid-cols-2 gap-4">
            <div className="flex items-center gap-3">
              {syncStatus?.database_configured ? (
                <CheckCircle2 className="w-5 h-5 text-success flex-shrink-0" />
              ) : (
                <Circle className="w-5 h-5 text-text-secondary flex-shrink-0" />
              )}
              <div>
                <p className="text-sm font-medium">Database</p>
                <p className="text-xs text-text-secondary">
                  {syncStatus?.database_configured ? "Connected" : "Not configured"}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              {syncStatus?.s3_configured ? (
                <CheckCircle2 className="w-5 h-5 text-success flex-shrink-0" />
              ) : (
                <Circle className="w-5 h-5 text-text-secondary flex-shrink-0" />
              )}
              <div>
                <p className="text-sm font-medium">S3 Storage</p>
                <p className="text-xs text-text-secondary">
                  {syncStatus?.s3_configured ? "Connected" : "Not configured"}
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Sync Section */}
      <section>
        <h2 className="text-lg font-semibold mb-4 text-text-secondary uppercase tracking-wide text-xs">
          Sync to Database
        </h2>

        <div className="bg-surface border border-border rounded-lg p-6 space-y-6">
          {/* Entity Selection */}
          {syncStep === "idle" && (
            <>
              <div>
                <p className="text-sm font-medium mb-3">Select data to sync:</p>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {["standards", "atoms", "tests", "questions"].map((entity) => (
                    <label
                      key={entity}
                      className={cn(
                        "flex items-center gap-2 p-3 rounded-lg border cursor-pointer transition-colors",
                        entities.includes(entity)
                          ? "border-accent bg-accent/10"
                          : "border-border hover:border-border/80"
                      )}
                    >
                      <input
                        type="checkbox"
                        checked={entities.includes(entity)}
                        onChange={() => toggleEntity(entity)}
                        className="hidden"
                      />
                      <div
                        className={cn(
                          "w-4 h-4 rounded border flex items-center justify-center",
                          entities.includes(entity)
                            ? "bg-accent border-accent"
                            : "border-text-secondary"
                        )}
                      >
                        {entities.includes(entity) && (
                          <CheckCircle2 className="w-3 h-3 text-white" />
                        )}
                      </div>
                      <span className="text-sm capitalize">{entity}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="flex flex-wrap gap-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={includeVariants}
                    onChange={(e) => setIncludeVariants(e.target.checked)}
                    className="w-4 h-4 rounded border-border"
                  />
                  <span className="text-sm">Include question variants</span>
                </label>

                <label
                  className={cn(
                    "flex items-center gap-2",
                    syncStatus?.s3_configured ? "cursor-pointer" : "opacity-50 cursor-not-allowed"
                  )}
                >
                  <input
                    type="checkbox"
                    checked={uploadImages}
                    onChange={(e) => setUploadImages(e.target.checked)}
                    disabled={!syncStatus?.s3_configured}
                    className="w-4 h-4 rounded border-border"
                  />
                  <span className="text-sm">Upload images to S3</span>
                  {!syncStatus?.s3_configured && (
                    <span className="text-xs text-warning">(S3 not configured)</span>
                  )}
                </label>
              </div>

              <div className="pt-4 border-t border-border">
                <button
                  onClick={handlePreview}
                  disabled={entities.length === 0}
                  className={cn(
                    "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors",
                    entities.length === 0
                      ? "bg-accent/50 text-white cursor-not-allowed"
                      : "bg-accent text-white hover:bg-accent/90"
                  )}
                >
                  <RefreshCw className="w-4 h-4" />
                  Preview Sync
                </button>
              </div>
            </>
          )}

          {/* Preview Loading */}
          {syncStep === "preview" && (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-accent" />
              <span className="ml-2 text-text-secondary">Generating preview...</span>
            </div>
          )}

          {/* Preview Results & Confirm */}
          {syncStep === "confirm" && preview && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-sm font-medium">
                <AlertTriangle className="w-4 h-4 text-warning" />
                <span>Review what will be synced:</span>
              </div>

              <div className="bg-background rounded-lg p-4 space-y-2">
                {preview.tables.map((table) => (
                  <div key={table.table} className="flex justify-between text-sm">
                    <span className="capitalize">{table.table}</span>
                    <span className="text-text-secondary">
                      {table.total} rows
                      {table.breakdown?.official !== undefined && (
                        <span className="text-xs ml-2">
                          ({table.breakdown.official} official, {table.breakdown.variants} variants)
                        </span>
                      )}
                    </span>
                  </div>
                ))}
              </div>

              {preview.warnings.length > 0 && (
                <div className="bg-warning/10 border border-warning/20 rounded-lg p-3">
                  {preview.warnings.map((warning, i) => (
                    <p key={i} className="text-sm text-warning">
                      {warning}
                    </p>
                  ))}
                </div>
              )}

              <div className="flex gap-3 pt-2">
                <button
                  onClick={handleSync}
                  className="flex items-center gap-2 px-4 py-2 bg-success text-white rounded-lg text-sm font-medium hover:bg-success/90 transition-colors"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  Confirm & Sync
                </button>
                <button
                  onClick={resetSync}
                  className="px-4 py-2 bg-surface border border-border rounded-lg text-sm font-medium hover:bg-white/5 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {/* Syncing */}
          {syncStep === "syncing" && (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-accent" />
              <span className="ml-2 text-text-secondary">Syncing to database...</span>
            </div>
          )}

          {/* Done */}
          {syncStep === "done" && syncResult && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-success">
                <CheckCircle2 className="w-5 h-5" />
                <span className="font-medium">{syncResult.message}</span>
              </div>

              <div className="bg-background rounded-lg p-4 space-y-2">
                {Object.entries(syncResult.results).map(([table, count]) => (
                  <div key={table} className="flex justify-between text-sm">
                    <span className="capitalize">{table}</span>
                    <span className="text-text-secondary">{count} rows affected</span>
                  </div>
                ))}
              </div>

              <button
                onClick={resetSync}
                className="px-4 py-2 bg-surface border border-border rounded-lg text-sm font-medium hover:bg-white/5 transition-colors"
              >
                Done
              </button>
            </div>
          )}

          {/* Error */}
          {syncStep === "error" && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-error">
                <AlertTriangle className="w-5 h-5" />
                <span className="font-medium">Sync failed</span>
              </div>

              {syncResult?.errors && syncResult.errors.length > 0 && (
                <div className="bg-error/10 border border-error/20 rounded-lg p-3">
                  {syncResult.errors.map((err, i) => (
                    <p key={i} className="text-sm text-error">
                      {err}
                    </p>
                  ))}
                </div>
              )}

              {error && (
                <div className="bg-error/10 border border-error/20 rounded-lg p-3">
                  <p className="text-sm text-error">{error}</p>
                </div>
              )}

              <button
                onClick={resetSync}
                className="px-4 py-2 bg-surface border border-border rounded-lg text-sm font-medium hover:bg-white/5 transition-colors"
              >
                Try Again
              </button>
            </div>
          )}
        </div>
      </section>

      {/* Course Info Section */}
      <section>
        <h2 className="text-lg font-semibold mb-4 text-text-secondary uppercase tracking-wide text-xs">
          Course Information
        </h2>

        <div className="bg-surface border border-border rounded-lg p-6">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-text-secondary uppercase tracking-wide">Course ID</p>
              <p className="font-mono text-sm mt-1">{courseId}</p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
