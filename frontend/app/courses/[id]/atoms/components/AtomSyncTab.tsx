"use client";

import { Upload, AlertTriangle, CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { AtomPipelineSummary } from "@/lib/api";

interface AtomSyncTabProps {
  subjectId: string;
  summary: AtomPipelineSummary;
}

export function AtomSyncTab({
  subjectId,
  summary,
}: AtomSyncTabProps) {
  const isBlocked =
    summary.standards_validated === 0 ||
    summary.structural_checks_passed === false;

  return (
    <div className="space-y-6">
      <div className="bg-surface border border-border rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-2">
          Sync Atoms to Database
        </h3>
        <p className="text-sm text-text-secondary mb-6">
          Sync validated atoms to the database. Uses the
          course-level sync which includes atoms alongside
          standards, tests, and questions.
        </p>

        {isBlocked ? (
          <div className="flex items-start gap-3 bg-amber-500/10 border border-amber-500/20 rounded-lg p-4">
            <AlertTriangle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
            <div>
              <div className="font-medium text-sm">
                Sync Blocked
              </div>
              <p className="text-sm text-text-secondary mt-1">
                {summary.standards_validated === 0
                  ? "Run validation on atoms before syncing. Unvalidated atoms must not reach production."
                  : "Structural checks have failures. Fix errors before syncing."}
              </p>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Ready status */}
            <div className="flex items-start gap-3 bg-success/10 border border-success/20 rounded-lg p-4">
              <CheckCircle2 className="w-5 h-5 text-success flex-shrink-0 mt-0.5" />
              <div>
                <div className="font-medium text-sm">
                  Ready to Sync
                </div>
                <p className="text-sm text-text-secondary mt-1">
                  {summary.atom_count} atoms validated and ready.
                  Use the course-level sync page to push atoms
                  to the database.
                </p>
              </div>
            </div>

            {/* Link to course sync */}
            <a
              href={`/courses/${subjectId}`}
              className={cn(
                "inline-flex items-center gap-2 px-5 py-2.5",
                "bg-accent text-white rounded-lg text-sm",
                "font-medium hover:bg-accent/90 transition-colors",
              )}
            >
              <Upload className="w-4 h-4" />
              Go to Course Sync
            </a>
          </div>
        )}
      </div>

      {/* Info */}
      <div className="bg-surface border border-border rounded-lg p-6">
        <h4 className="text-sm font-semibold mb-2">
          How Sync Works
        </h4>
        <ul className="text-sm text-text-secondary space-y-1.5">
          <li>
            Atoms are synced as part of the course-level sync
            pipeline
          </li>
          <li>
            The sync reads from the canonical atoms JSON file
          </li>
          <li>
            Existing atoms in the DB are updated; new atoms are
            created
          </li>
          <li>
            Sync supports local, staging, and production
            environments
          </li>
        </ul>
      </div>
    </div>
  );
}
