"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, CheckCircle2, Circle, RefreshCw, AlertTriangle, Loader2 } from "lucide-react";
import {
  getSyncStatus,
  getCourseSyncDiff,
  previewCourseSync,
  executeCourseSync,
  type SyncStatus,
  type SyncPreviewResponse,
  type SyncExecuteResponse,
  type SyncEnvironment,
  type SyncDiffResponse,
} from "@/lib/api";
import { cn } from "@/lib/utils";
import { useToast } from "@/components/ui";
import { SyncDiffTable } from "./sync-diff-table";
import { EnvironmentSelector, ENVIRONMENTS } from "./environment-selector";

type SyncStep = "idle" | "preview" | "confirm" | "syncing" | "done" | "error";

const ENTITIES = ["standards", "atoms", "tests", "questions", "variants"];

export default function SettingsPage() {
  const params = useParams();
  const courseId = params.id as string;
  const { showToast } = useToast();

  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null);
  const [syncDiff, setSyncDiff] = useState<SyncDiffResponse | null>(null);
  const [diffLoading, setDiffLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Sync flow state
  const [syncStep, setSyncStep] = useState<SyncStep>("idle");
  const [preview, setPreview] = useState<SyncPreviewResponse | null>(null);
  const [syncResult, setSyncResult] = useState<SyncExecuteResponse | null>(null);

  // Sync options
  const [environment, setEnvironment] = useState<SyncEnvironment>("local");
  const [entities, setEntities] = useState<string[]>([]);
  const [showProdConfirm, setShowProdConfirm] = useState(false);

  // Auto-select entities that need syncing when diff loads
  useEffect(() => {
    if (syncDiff && !syncDiff.error) {
      const needsSync = ENTITIES.filter((entity) => {
        const diff = syncDiff.entities[entity];
        return diff?.has_changes ?? false;
      });
      setEntities(needsSync);
    }
  }, [syncDiff]);

  useEffect(() => {
    if (courseId) {
      getSyncStatus()
        .then(setSyncStatus)
        .catch((err) => setError(err.message))
        .finally(() => setLoading(false));
    }
  }, [courseId]);

  // Load diff when environment changes
  const loadDiff = useCallback(async () => {
    if (!courseId || !syncStatus?.environments?.[environment]) return;
    setDiffLoading(true);
    try {
      const diff = await getCourseSyncDiff(courseId, environment);
      setSyncDiff(diff);
    } catch (err) {
      console.error("Failed to load diff:", err);
    } finally {
      setDiffLoading(false);
    }
  }, [courseId, environment, syncStatus]);

  useEffect(() => {
    loadDiff();
  }, [loadDiff]);

  const isEnvConfigured = (env: SyncEnvironment) => {
    return syncStatus?.environments?.[env] ?? false;
  };

  const handlePreview = useCallback(async () => {
    setSyncStep("preview");
    setPreview(null);
    setSyncResult(null);
    setError(null);

    try {
      const result = await previewCourseSync(courseId, entities, environment);
      setPreview(result);
      setSyncStep("confirm");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Preview failed");
      setSyncStep("error");
    }
  }, [courseId, entities, environment]);

  const handleSync = useCallback(async () => {
    // Extra confirmation for production
    if (environment === "prod" && !showProdConfirm) {
      setShowProdConfirm(true);
      return;
    }

    setSyncStep("syncing");
    setShowProdConfirm(false);

    try {
      const result = await executeCourseSync(courseId, entities, environment, true);
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
  }, [courseId, entities, environment, showProdConfirm, showToast]);

  const resetSync = useCallback(() => {
    setSyncStep("idle");
    setPreview(null);
    setSyncResult(null);
    setShowProdConfirm(false);
    setError(null);
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
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {ENVIRONMENTS.map((env) => (
              <div key={env.id} className="flex items-center gap-3">
                {isEnvConfigured(env.id) ? (
                  <CheckCircle2 className="w-5 h-5 text-success flex-shrink-0" />
                ) : (
                  <Circle className="w-5 h-5 text-text-secondary flex-shrink-0" />
                )}
                <div>
                  <p className="text-sm font-medium">{env.label} DB</p>
                  <p className="text-xs text-text-secondary">
                    {isEnvConfigured(env.id) ? "Configured" : "Not configured"}
                  </p>
                </div>
              </div>
            ))}
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
          {/* Environment & Entity Selection */}
          {syncStep === "idle" && (
            <>
              {/* Environment Selector */}
              <EnvironmentSelector
                environment={environment}
                setEnvironment={setEnvironment}
                isEnvConfigured={isEnvConfigured}
              />

              {/* Sync Status Table */}
              {isEnvConfigured(environment) && (
                <SyncDiffTable
                  syncDiff={syncDiff}
                  diffLoading={diffLoading}
                  environment={environment}
                  environmentLabel={ENVIRONMENTS.find((e) => e.id === environment)?.label || ""}
                  entities={ENTITIES}
                  onRefresh={loadDiff}
                />
              )}

              {/* Entity Selection */}
              <div>
                <p className="text-sm font-medium mb-3">Select data to sync:</p>
                <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                  {ENTITIES.map((entity) => {
                    const diff = syncDiff?.entities[entity];
                    const hasChanges = diff?.has_changes ?? false;
                    const isSelected = entities.includes(entity);
                    const isDisabled = !hasChanges;

                    return (
                      <button
                        key={entity}
                        type="button"
                        onClick={() => !isDisabled && toggleEntity(entity)}
                        disabled={isDisabled}
                        className={cn(
                          "flex items-center gap-2 p-3 rounded-lg border transition-colors",
                          isSelected && !isDisabled
                            ? "border-accent bg-accent/10 text-accent"
                            : isDisabled
                              ? "border-border/50 opacity-50 cursor-not-allowed"
                              : "border-border hover:border-border/80"
                        )}
                      >
                        <div
                          className={cn(
                            "w-4 h-4 rounded border flex items-center justify-center flex-shrink-0",
                            isSelected && !isDisabled
                              ? "bg-accent border-accent"
                              : isDisabled
                                ? "border-text-secondary/50 bg-success/20"
                                : "border-text-secondary"
                          )}
                        >
                          {isSelected && !isDisabled && (
                            <CheckCircle2 className="w-3 h-3 text-white" />
                          )}
                          {isDisabled && (
                            <CheckCircle2 className="w-3 h-3 text-success" />
                          )}
                        </div>
                        <span className="text-sm capitalize">{entity}</span>
                        {isDisabled && (
                          <span className="text-xs text-success ml-auto">synced</span>
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* S3 Auto-Upload Note */}
              {syncStatus?.s3_configured && entities.includes("questions") && (
                <div className="flex items-center gap-2 text-xs text-text-secondary">
                  <CheckCircle2 className="w-4 h-4 text-success" />
                  <span>Images will be automatically uploaded to S3</span>
                </div>
              )}

              <div className="pt-4 border-t border-border">
                <button
                  onClick={handlePreview}
                  disabled={entities.length === 0 || !isEnvConfigured(environment)}
                  className={cn(
                    "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors",
                    entities.length === 0 || !isEnvConfigured(environment)
                      ? "bg-accent/50 text-white cursor-not-allowed"
                      : "bg-accent text-white hover:bg-accent/90"
                  )}
                >
                  <RefreshCw className="w-4 h-4" />
                  Preview Sync to {ENVIRONMENTS.find((e) => e.id === environment)?.label}
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
                <AlertTriangle className={cn(
                  "w-4 h-4",
                  environment === "prod" ? "text-error" : "text-warning"
                )} />
                <span>
                  Review what will be synced to{" "}
                  <span className={environment === "prod" ? "text-error font-bold" : ""}>
                    {ENVIRONMENTS.find((e) => e.id === environment)?.label}
                  </span>
                  :
                </span>
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

              {/* Production Confirmation */}
              {environment === "prod" && showProdConfirm && (
                <div className="bg-error/10 border border-error/20 rounded-lg p-4">
                  <p className="text-sm text-error font-medium mb-2">
                    Are you sure you want to sync to PRODUCTION?
                  </p>
                  <p className="text-xs text-error/80">
                    This will modify live data. This action cannot be undone.
                  </p>
                </div>
              )}

              <div className="flex gap-3 pt-2">
                <button
                  onClick={handleSync}
                  className={cn(
                    "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors",
                    environment === "prod"
                      ? "bg-error text-white hover:bg-error/90"
                      : "bg-success text-white hover:bg-success/90"
                  )}
                >
                  <CheckCircle2 className="w-4 h-4" />
                  {showProdConfirm ? "Yes, Sync to Production" : "Confirm & Sync"}
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
              <span className="ml-2 text-text-secondary">
                Syncing to {ENVIRONMENTS.find((e) => e.id === environment)?.label}...
              </span>
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

        <div className="bg-surface border border-border rounded-lg p-6 grid grid-cols-2 gap-4">
          <div>
            <p className="text-xs text-text-secondary uppercase tracking-wide">Course ID</p>
            <p className="font-mono text-sm mt-1">{courseId}</p>
          </div>
        </div>
      </section>
    </div>
  );
}
