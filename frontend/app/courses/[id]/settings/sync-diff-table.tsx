"use client";

import { CheckCircle2, RefreshCw, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { SyncDiffResponse, SyncEnvironment } from "@/lib/api";

interface SyncDiffTableProps {
  syncDiff: SyncDiffResponse | null;
  diffLoading: boolean;
  environment: SyncEnvironment;
  environmentLabel: string;
  entities: string[];
  onRefresh: () => void;
}

export function SyncDiffTable({
  syncDiff,
  diffLoading,
  environment,
  environmentLabel,
  entities,
  onRefresh,
}: SyncDiffTableProps) {
  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <p className="text-sm font-medium">Sync status for {environmentLabel}:</p>
        <button
          onClick={onRefresh}
          disabled={diffLoading}
          className="text-xs text-accent hover:text-accent/80 flex items-center gap-1"
        >
          <RefreshCw className={cn("w-3 h-3", diffLoading && "animate-spin")} />
          Refresh
        </button>
      </div>

      {diffLoading ? (
        <div className="flex items-center justify-center py-4">
          <Loader2 className="w-4 h-4 animate-spin text-accent" />
          <span className="ml-2 text-sm text-text-secondary">Loading...</span>
        </div>
      ) : syncDiff?.error ? (
        <div className="text-sm text-error bg-error/10 p-3 rounded-lg">{syncDiff.error}</div>
      ) : syncDiff ? (
        <div className="bg-background rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left p-2 font-medium">Entity</th>
                <th className="text-right p-2 font-medium">Local</th>
                <th className="text-right p-2 font-medium">DB</th>
                <th className="text-right p-2 font-medium">Changes</th>
                <th className="text-right p-2 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {entities.map((entity) => {
                const diff = syncDiff.entities[entity];
                if (!diff) return null;
                const hasChanges = diff.has_changes;
                return (
                  <tr key={entity} className="border-b border-border/50 last:border-0">
                    <td className="p-2 capitalize">{entity}</td>
                    <td className="p-2 text-right text-text-secondary">{diff.local_count}</td>
                    <td className="p-2 text-right text-text-secondary">{diff.db_count}</td>
                    <td className="p-2 text-right">
                      {diff.new_count > 0 && (
                        <span className="text-success">+{diff.new_count} </span>
                      )}
                      {diff.modified_count > 0 && (
                        <span className="text-warning">{diff.modified_count} mod </span>
                      )}
                      {diff.deleted_count > 0 && (
                        <span className="text-error">-{diff.deleted_count}</span>
                      )}
                      {!hasChanges && <span className="text-text-secondary">0</span>}
                    </td>
                    <td className="p-2 text-right">
                      {hasChanges ? (
                        <span className="text-warning">Needs sync</span>
                      ) : (
                        <span className="text-success">In sync</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : null}

      {syncDiff && !syncDiff.has_changes && !syncDiff.error && (
        <p className="text-xs text-success mt-2 flex items-center gap-1">
          <CheckCircle2 className="w-3 h-3" />
          All data is already synced to {environmentLabel}
        </p>
      )}
    </div>
  );
}
