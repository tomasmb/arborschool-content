"use client";

import {
  CheckCircle2,
  RefreshCw,
  XCircle,
  BarChart3,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { AtomBrief } from "@/lib/api";

interface ResultsTabProps {
  atoms: AtomBrief[];
  onRegenerate: (atomId: string) => void;
}

export function ResultsTab({ atoms, onRegenerate }: ResultsTabProps) {
  const withQuestions = atoms.filter(
    (a) => a.question_set_count > 0,
  );

  if (withQuestions.length === 0) {
    return <EmptyState />;
  }

  const byEje: Record<string, AtomBrief[]> = {};
  for (const atom of withQuestions) {
    const eje = atom.eje || "unknown";
    if (!byEje[eje]) byEje[eje] = [];
    byEje[eje].push(atom);
  }

  const totalQs = withQuestions.reduce(
    (sum, a) => sum + a.question_set_count,
    0,
  );

  return (
    <div className="space-y-6">
      <ResultsSummary
        atomCount={withQuestions.length}
        totalQs={totalQs}
      />
      {Object.entries(byEje).map(([eje, ejeAtoms]) => (
        <EjeGroup
          key={eje}
          eje={eje}
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
  totalQs,
}: {
  atomCount: number;
  totalQs: number;
}) {
  const avg = atomCount > 0 ? (totalQs / atomCount).toFixed(1) : "0";

  return (
    <div className="grid grid-cols-3 gap-4">
      <div className="bg-surface border border-border rounded-lg p-4 text-center">
        <div className="text-2xl font-bold">{atomCount}</div>
        <div className="text-xs text-text-secondary mt-1">
          Atoms with Questions
        </div>
      </div>
      <div className="bg-surface border border-border rounded-lg p-4 text-center">
        <div className="text-2xl font-bold">{totalQs}</div>
        <div className="text-xs text-text-secondary mt-1">
          Total Questions
        </div>
      </div>
      <div className="bg-surface border border-border rounded-lg p-4 text-center">
        <div className="text-2xl font-bold">{avg}</div>
        <div className="text-xs text-text-secondary mt-1">
          Avg per Atom
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
  atoms,
  onRegenerate,
}: {
  eje: string;
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
          <div
            key={atom.id}
            className="px-4 py-3 flex items-center justify-between group"
          >
            <div className="min-w-0 flex-1">
              <div className="text-sm font-medium truncate">
                {atom.titulo}
              </div>
              <div className="text-xs text-text-secondary mt-0.5">
                {atom.id}
              </div>
            </div>
            <div className="ml-4 flex items-center gap-3">
              <span className="inline-flex items-center gap-1 text-sm">
                <CheckCircle2 className="w-3.5 h-3.5 text-success" />
                <span className="font-medium">
                  {atom.question_set_count}
                </span>
              </span>
              <button
                onClick={() => onRegenerate(atom.id)}
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
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
