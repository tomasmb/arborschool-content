"use client";

import {
  Database,
  CheckCircle2,
  Clock,
  BarChart3,
} from "lucide-react";
import type { AtomBrief } from "@/lib/api";

interface OverviewTabProps {
  atoms: AtomBrief[];
  loading: boolean;
  onNavigateToGeneration: (atomId?: string) => void;
}

export function OverviewTab({
  atoms,
  loading,
  onNavigateToGeneration,
}: OverviewTabProps) {
  if (loading) {
    return (
      <div className="flex items-center justify-center h-40">
        <div className="text-text-secondary">Loading atoms...</div>
      </div>
    );
  }

  const withQs = atoms.filter((a) => a.question_set_count > 0);
  const withoutQs = atoms.filter((a) => a.question_set_count === 0);
  const totalQs = atoms.reduce(
    (sum, a) => sum + a.question_set_count,
    0,
  );
  const pct =
    atoms.length > 0
      ? Math.round((withQs.length / atoms.length) * 100)
      : 0;

  return (
    <div className="space-y-6">
      <SummaryCards
        total={atoms.length}
        withQs={withQs.length}
        withoutQs={withoutQs.length}
        totalQs={totalQs}
      />
      <ProgressBar pct={pct} done={withQs.length} total={atoms.length} />
      <AtomStatusList
        atoms={atoms}
        onNavigate={onNavigateToGeneration}
      />
    </div>
  );
}


// ---------------------------------------------------------------------------
// Summary stat cards
// ---------------------------------------------------------------------------

function SummaryCards({
  total,
  withQs,
  withoutQs,
  totalQs,
}: {
  total: number;
  withQs: number;
  withoutQs: number;
  totalQs: number;
}) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <StatCard
        icon={<Database className="w-5 h-5 text-accent" />}
        value={total}
        label="Total Atoms"
      />
      <StatCard
        icon={<CheckCircle2 className="w-5 h-5 text-success" />}
        value={withQs}
        label="With Questions"
      />
      <StatCard
        icon={<Clock className="w-5 h-5 text-warning" />}
        value={withoutQs}
        label="Pending"
      />
      <StatCard
        icon={<BarChart3 className="w-5 h-5 text-accent" />}
        value={totalQs}
        label="Total Questions"
      />
    </div>
  );
}


// ---------------------------------------------------------------------------
// Progress bar
// ---------------------------------------------------------------------------

function ProgressBar({
  pct,
  done,
  total,
}: {
  pct: number;
  done: number;
  total: number;
}) {
  return (
    <div className="bg-surface border border-border rounded-lg p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium">
          Generation Progress
        </span>
        <span className="text-sm text-text-secondary">{pct}%</span>
      </div>
      <div className="w-full h-2 bg-border rounded-full overflow-hidden">
        <div
          className="h-full bg-accent rounded-full transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
      <p className="text-xs text-text-secondary mt-2">
        {done} of {total} atoms have generated question pools
      </p>
    </div>
  );
}


// ---------------------------------------------------------------------------
// Atom status list
// ---------------------------------------------------------------------------

function AtomStatusList({
  atoms,
  onNavigate,
}: {
  atoms: AtomBrief[];
  onNavigate: (atomId?: string) => void;
}) {
  return (
    <div className="bg-surface border border-border rounded-lg">
      <div className="px-4 py-3 border-b border-border flex items-center justify-between">
        <h3 className="text-sm font-semibold">
          Atom Question Status
        </h3>
        <button
          onClick={() => onNavigate()}
          className="text-xs text-accent hover:underline"
        >
          Go to Generation
        </button>
      </div>
      <div className="divide-y divide-border max-h-96 overflow-y-auto">
        {atoms.map((atom) => (
          <button
            key={atom.id}
            className="w-full px-4 py-3 flex items-center justify-between hover:bg-white/5 transition-colors text-left"
            onClick={() => onNavigate(atom.id)}
          >
            <div className="min-w-0 flex-1">
              <div className="text-sm font-medium truncate">
                {atom.titulo}
              </div>
              <div className="text-xs text-text-secondary mt-0.5">
                {atom.id} &middot; {atom.eje}
              </div>
            </div>
            <div className="ml-4 flex-shrink-0">
              {atom.question_set_count > 0 ? (
                <span className="inline-flex items-center gap-1 px-2 py-1 text-xs rounded bg-success/10 text-success">
                  <CheckCircle2 className="w-3 h-3" />
                  {atom.question_set_count} questions
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 px-2 py-1 text-xs rounded bg-text-secondary/10 text-text-secondary">
                  <Clock className="w-3 h-3" />
                  Pending
                </span>
              )}
            </div>
          </button>
        ))}
        {atoms.length === 0 && (
          <div className="px-4 py-8 text-center text-text-secondary text-sm">
            No atoms found. Generate atoms first.
          </div>
        )}
      </div>
    </div>
  );
}


// ---------------------------------------------------------------------------
// Stat card
// ---------------------------------------------------------------------------

function StatCard({
  icon,
  value,
  label,
}: {
  icon: React.ReactNode;
  value: number;
  label: string;
}) {
  return (
    <div className="bg-surface border border-border rounded-lg p-4 text-center">
      <div className="flex justify-center mb-2">{icon}</div>
      <div className="text-2xl font-bold">{value}</div>
      <div className="text-xs text-text-secondary mt-1">{label}</div>
    </div>
  );
}
