"use client";

import { Database, AlertTriangle, RefreshCw } from "lucide-react";

export default function SyncPage() {
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

      {/* Entity selection */}
      <div className="bg-surface border border-border rounded-lg p-6">
        <h2 className="font-medium mb-4">Entities to Sync</h2>

        <div className="space-y-3">
          {[
            { id: "standards", label: "Standards", count: 21 },
            { id: "atoms", label: "Atoms", count: 127 },
            { id: "tests", label: "Tests", count: 4 },
            { id: "questions", label: "Questions (Official)", count: 176 },
            { id: "variants", label: "Questions (Variants)", count: 89 },
          ].map((entity) => (
            <label
              key={entity.id}
              className="flex items-center gap-3 p-3 border border-border rounded-lg hover:bg-white/5 cursor-pointer"
            >
              <input
                type="checkbox"
                defaultChecked
                className="w-4 h-4 rounded border-border"
              />
              <span className="flex-1">{entity.label}</span>
              <span className="text-text-secondary text-sm">({entity.count})</span>
            </label>
          ))}
        </div>

        <div className="mt-6 flex gap-3">
          <button className="flex items-center gap-2 px-4 py-2 bg-surface border border-border rounded-lg text-sm hover:bg-white/5 transition-colors">
            <RefreshCw className="w-4 h-4" />
            Preview Changes (Dry Run)
          </button>
          <button
            className="flex items-center gap-2 px-4 py-2 bg-accent text-white rounded-lg text-sm hover:bg-accent/90 transition-colors"
            disabled
          >
            <Database className="w-4 h-4" />
            Execute Sync
          </button>
        </div>
      </div>

      {/* Preview results placeholder */}
      <div className="bg-surface border border-border rounded-lg p-6">
        <h2 className="font-medium mb-4">Preview Results</h2>

        <div className="text-center py-8 text-text-secondary">
          <Database className="w-8 h-8 mx-auto mb-2 opacity-50" />
          <p>Run a preview to see changes</p>
        </div>
      </div>
    </div>
  );
}
