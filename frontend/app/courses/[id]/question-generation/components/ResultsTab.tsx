"use client";

import Link from "next/link";
import {
  CheckCircle2,
  ChevronRight,
  RefreshCw,
  XCircle,
  BarChart3,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { AtomBrief } from "@/lib/api";

/** Phase group label for the last completed pipeline phase. */
const PHASE_LABELS: Record<number, string> = {
  1: "Enriched",
  3: "Planned",
  4: "Generated",
  6: "Validated",
  8: "Feedback",
  10: "Finalized",
};

function PhaseBadge({ phase }: { phase: number | null }) {
  if (phase === null) return null;
  // Find the highest matching label
  const keys = Object.keys(PHASE_LABELS)
    .map(Number)
    .filter((k) => k <= phase)
    .sort((a, b) => b - a);
  const label = keys.length > 0 ? PHASE_LABELS[keys[0]] : `Phase ${phase}`;
  return (
    <span
      className={cn(
        "inline-flex items-center px-1.5 py-0.5 rounded",
        "text-[10px] font-medium",
        phase >= 10
          ? "bg-success/10 text-success"
          : phase >= 4
            ? "bg-accent/10 text-accent"
            : "bg-white/10 text-text-secondary",
      )}
    >
      {label}
    </span>
  );
}

interface ResultsTabProps {
  courseId: string;
  atoms: AtomBrief[];
  onRegenerate: (atomId: string) => void;
}

/** An atom has results if it has synced questions OR generated checkpoints. */
function hasResults(a: AtomBrief): boolean {
  return a.question_set_count > 0
    || (a.last_completed_phase !== null && a.last_completed_phase >= 4);
}

export function ResultsTab({ courseId, atoms, onRegenerate }: ResultsTabProps) {
  const withResults = atoms.filter(hasResults);

  if (withResults.length === 0) {
    return <EmptyState />;
  }

  const byEje: Record<string, AtomBrief[]> = {};
  for (const atom of withResults) {
    const eje = atom.eje || "unknown";
    if (!byEje[eje]) byEje[eje] = [];
    byEje[eje].push(atom);
  }

  const syncedCount = withResults.filter((a) => a.question_set_count > 0).length;
  const totalQs = withResults.reduce(
    (sum, a) => sum + a.question_set_count,
    0,
  );

  return (
    <div className="space-y-6">
      <ResultsSummary
        atomCount={withResults.length}
        syncedCount={syncedCount}
        totalQs={totalQs}
      />
      {Object.entries(byEje).map(([eje, ejeAtoms]) => (
        <EjeGroup
          key={eje}
          eje={eje}
          courseId={courseId}
          atoms={ejeAtoms}
          onRegenerate={onRegenerate}
        />
      ))}
    </div>
  );
}


// ---------------------------------------------------------------------------
// Empty state
// ---------------------------------------------------------------------------

function EmptyState() {
  return (
    <div className="bg-surface border border-border rounded-lg p-8 text-center">
      <XCircle className="w-8 h-8 text-text-secondary mx-auto mb-3" />
      <h3 className="text-sm font-semibold mb-1">No results yet</h3>
      <p className="text-sm text-text-secondary">
        Generate question pools from the Generation tab to see
        results here.
      </p>
    </div>
  );
}


// ---------------------------------------------------------------------------
// Summary stats row
// ---------------------------------------------------------------------------

function ResultsSummary({
  atomCount,
  syncedCount,
  totalQs,
}: {
  atomCount: number;
  syncedCount: number;
  totalQs: number;
}) {
  return (
    <div className="grid grid-cols-3 gap-4">
      <div className="bg-surface border border-border rounded-lg p-4 text-center">
        <div className="text-2xl font-bold">{atomCount}</div>
        <div className="text-xs text-text-secondary mt-1">
          Atoms with Results
        </div>
      </div>
      <div className="bg-surface border border-border rounded-lg p-4 text-center">
        <div className="text-2xl font-bold">{syncedCount}</div>
        <div className="text-xs text-text-secondary mt-1">
          Synced to DB
        </div>
      </div>
      <div className="bg-surface border border-border rounded-lg p-4 text-center">
        <div className="text-2xl font-bold">{totalQs}</div>
        <div className="text-xs text-text-secondary mt-1">
          Synced Questions
        </div>
      </div>
    </div>
  );
}


// ---------------------------------------------------------------------------
// Eje group with atom rows
// ---------------------------------------------------------------------------

function EjeGroup({
  eje,
  courseId,
  atoms,
  onRegenerate,
}: {
  eje: string;
  courseId: string;
  atoms: AtomBrief[];
  onRegenerate: (atomId: string) => void;
}) {
  const qCount = atoms.reduce(
    (s, a) => s + a.question_set_count,
    0,
  );

  return (
    <div className="bg-surface border border-border rounded-lg">
      <div className="px-4 py-3 border-b border-border flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold capitalize">
            {eje.replace(/_/g, " ")}
          </h3>
          <span className="text-xs text-text-secondary">
            {atoms.length} atoms &middot; {qCount} questions
          </span>
        </div>
        <BarChart3 className="w-4 h-4 text-text-secondary" />
      </div>
      <div className="divide-y divide-border">
        {atoms.map((atom) => (
          <Link
            key={atom.id}
            href={`/courses/${courseId}/question-generation/${atom.id}`}
            className={cn(
              "px-4 py-3 flex items-center justify-between group",
              "hover:bg-white/5 transition-colors cursor-pointer block",
            )}
          >
            <div className="min-w-0 flex-1">
              <div className="text-sm font-medium truncate">
                {atom.titulo}
              </div>
              <div className="flex items-center gap-2 mt-0.5">
                <span className="text-xs text-text-secondary">
                  {atom.id}
                </span>
                <PhaseBadge phase={atom.last_completed_phase} />
              </div>
            </div>
            <div className="ml-4 flex items-center gap-3">
              {atom.question_set_count > 0 ? (
                <span className="inline-flex items-center gap-1 text-sm">
                  <CheckCircle2 className="w-3.5 h-3.5 text-success" />
                  <span className="font-medium">
                    {atom.question_set_count}
                  </span>
                </span>
              ) : (
                <span className="text-xs text-text-secondary">
                  not synced
                </span>
              )}
              <button
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  onRegenerate(atom.id);
                }}
                className={cn(
                  "flex items-center gap-1 px-2 py-1",
                  "rounded text-xs font-medium",
                  "text-warning bg-warning/10",
                  "hover:bg-warning/20 transition-colors",
                  "opacity-0 group-hover:opacity-100",
                )}
              >
                <RefreshCw className="w-3 h-3" />
                Regenerate
              </button>
              <ChevronRight className="w-4 h-4 text-text-secondary opacity-0 group-hover:opacity-100 transition-opacity" />
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
