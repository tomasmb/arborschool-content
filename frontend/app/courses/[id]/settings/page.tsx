"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  ArrowLeft,
  CheckCircle2,
  Circle,
  RefreshCw,
  AlertTriangle,
} from "lucide-react";
import { getSyncStatus, type SyncStatus } from "@/lib/api";
import { cn } from "@/lib/utils";

export default function SettingsPage() {
  const params = useParams();
  const courseId = params.id as string;

  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);

  useEffect(() => {
    if (courseId) {
      getSyncStatus()
        .then(setSyncStatus)
        .catch((err) => setError(err.message))
        .finally(() => setLoading(false));
    }
  }, [courseId]);

  const handleSync = async () => {
    setSyncing(true);
    // TODO: Implement course-scoped sync
    // For now, show a placeholder
    await new Promise((resolve) => setTimeout(resolve, 1000));
    setSyncing(false);
    alert("Course-scoped sync coming soon!");
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-text-secondary">Loading...</div>
      </div>
    );
  }

  if (error) {
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
          <p className="text-text-secondary mt-1">
            Course configuration and sync
          </p>
        </div>
      </div>

      {/* Sync Status Section */}
      <section>
        <h2 className="text-lg font-semibold mb-4 text-text-secondary uppercase tracking-wide text-xs">
          Sync Status
        </h2>

        <div className="bg-surface border border-border rounded-lg p-6">
          {syncStatus ? (
            <div className="space-y-6">
              {/* Configuration Status */}
              <div className="grid grid-cols-2 gap-4">
                <div className="flex items-center gap-3">
                  {syncStatus.database_configured ? (
                    <CheckCircle2 className="w-5 h-5 text-success flex-shrink-0" />
                  ) : (
                    <Circle className="w-5 h-5 text-text-secondary flex-shrink-0" />
                  )}
                  <div>
                    <p className="text-sm font-medium">Database</p>
                    <p className="text-xs text-text-secondary">
                      {syncStatus.database_configured ? "Connected" : "Not configured"}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {syncStatus.s3_configured ? (
                    <CheckCircle2 className="w-5 h-5 text-success flex-shrink-0" />
                  ) : (
                    <Circle className="w-5 h-5 text-text-secondary flex-shrink-0" />
                  )}
                  <div>
                    <p className="text-sm font-medium">S3 Storage</p>
                    <p className="text-xs text-text-secondary">
                      {syncStatus.s3_configured ? "Connected" : "Not configured"}
                    </p>
                  </div>
                </div>
              </div>

              {/* S3 Configuration */}
              <div className="pt-4 border-t border-border">
                <div className="flex items-center gap-2">
                  {syncStatus.s3_configured ? (
                    <>
                      <CheckCircle2 className="w-4 h-4 text-success" />
                      <span className="text-sm">S3 configured for image uploads</span>
                    </>
                  ) : (
                    <>
                      <AlertTriangle className="w-4 h-4 text-warning" />
                      <span className="text-sm text-warning">
                        S3 not configured - images will remain local
                      </span>
                    </>
                  )}
                </div>
              </div>

              {/* Sync Button */}
              <div className="pt-4 border-t border-border">
                <button
                  onClick={handleSync}
                  disabled={syncing}
                  className={cn(
                    "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors",
                    syncing
                      ? "bg-accent/50 text-white cursor-not-allowed"
                      : "bg-accent text-white hover:bg-accent/90"
                  )}
                >
                  <RefreshCw className={cn("w-4 h-4", syncing && "animate-spin")} />
                  {syncing ? "Syncing..." : "Sync to Database"}
                </button>
                <p className="text-xs text-text-secondary mt-2">
                  This will sync all course data (standards, atoms, questions, variants) to the
                  database.
                </p>
              </div>
            </div>
          ) : (
            <div className="text-text-secondary">No sync status available</div>
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
