"use client";

import { useState } from "react";
import {
  Sparkles,
  Play,
  RefreshCw,
  CheckCircle2,
  Circle,
  ChevronDown,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { AtomBrief } from "@/lib/api";

// Phase groups matching backend PHASE_GROUPS
const PHASES = [
  {
    id: "enrich",
    label: "Enrich",
    phases: "0-1",
    description: "Scope guardrails + difficulty rubric",
  },
  {
    id: "plan",
    label: "Plan",
    phases: "2-3",
    description: "Diverse item specs + plan validation",
  },
  {
    id: "generate",
    label: "Generate QTI",
    phases: "4",
    description: "Base QTI 3.0 XML items",
  },
  {
    id: "validate",
    label: "Validate",
    phases: "5-6",
    description: "Dedup, XSD, solvability, PAES checks",
  },
  {
    id: "feedback",
    label: "Feedback",
    phases: "7-8",
    description: "Per-option feedback + worked solutions",
  },
  {
    id: "finalize",
    label: "Finalize & Sync",
    phases: "9-10",
    description: "Final validation + DB sync",
  },
] as const;

type AtomFilter = "all" | "pending" | "generated";

interface GenerationTabProps {
  atoms: AtomBrief[];
  onRunPhase: (atomId: string, phase: string) => void;
}

export function GenerationTab({
  atoms,
  onRunPhase,
}: GenerationTabProps) {
  const [filter, setFilter] = useState<AtomFilter>("all");
  const [expandedAtom, setExpandedAtom] = useState<string | null>(
    null,
  );

  const generated = atoms.filter((a) => a.question_set_count > 0);
  const pending = atoms.filter((a) => a.question_set_count === 0);
  const totalQs = atoms.reduce(
    (s, a) => s + a.question_set_count,
    0,
  );

  const filtered = (() => {
    switch (filter) {
      case "pending":
        return pending;
      case "generated":
        return generated;
      default:
        return atoms;
    }
  })();

  const filters: { id: AtomFilter; label: string; count: number }[] =
    [
      { id: "all", label: "All", count: atoms.length },
      { id: "pending", label: "Pending", count: pending.length },
      { id: "generated", label: "Generated", count: generated.length },
    ];

  return (
    <div className="space-y-5">
      <HeaderStats
        generated={generated.length}
        total={atoms.length}
        totalQs={totalQs}
      />
      <FilterBar
        filters={filters}
        active={filter}
        onChange={setFilter}
      />
      <AtomTable
        atoms={filtered}
        expandedAtom={expandedAtom}
        onToggle={(id) =>
          setExpandedAtom(expandedAtom === id ? null : id)
        }
        onRunPhase={onRunPhase}
      />
    </div>
  );
}


// ---------------------------------------------------------------------------
// Header stats
// ---------------------------------------------------------------------------

function HeaderStats({
  generated,
  total,
  totalQs,
}: {
  generated: number;
  total: number;
  totalQs: number;
}) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div className="space-y-1">
        <h3 className="font-semibold">Question Generation</h3>
        <div className="flex gap-4 text-sm">
          <div>
            <span className="text-text-secondary">Generated:</span>{" "}
            <span className="font-medium">
              {generated}/{total}
            </span>
          </div>
          <div>
            <span className="text-text-secondary">Total Qs:</span>{" "}
            <span className="font-medium">{totalQs}</span>
          </div>
        </div>
      </div>
    </div>
  );
}


// ---------------------------------------------------------------------------
// Filter bar
// ---------------------------------------------------------------------------

function FilterBar({
  filters,
  active,
  onChange,
}: {
  filters: { id: AtomFilter; label: string; count: number }[];
  active: AtomFilter;
  onChange: (f: AtomFilter) => void;
}) {
  return (
    <div className="flex gap-1 border-b border-border">
      {filters.map((f) => (
        <button
          key={f.id}
          onClick={() => onChange(f.id)}
          className={cn(
            "px-4 py-2 text-sm font-medium border-b-2 -mb-px",
            "transition-colors",
            active === f.id
              ? "border-accent text-accent"
              : "border-transparent text-text-secondary hover:text-text-primary",
          )}
        >
          {f.label}
          <span
            className={cn(
              "ml-2 px-1.5 py-0.5 text-xs rounded",
              active === f.id ? "bg-accent/20" : "bg-surface",
            )}
          >
            {f.count}
          </span>
        </button>
      ))}
    </div>
  );
}


// ---------------------------------------------------------------------------
// Atom table
// ---------------------------------------------------------------------------

function AtomTable({
  atoms,
  expandedAtom,
  onToggle,
  onRunPhase,
}: {
  atoms: AtomBrief[];
  expandedAtom: string | null;
  onToggle: (id: string) => void;
  onRunPhase: (atomId: string, phase: string) => void;
}) {
  return (
    <div className="bg-surface border border-border rounded-lg overflow-hidden">
      <table className="w-full">
        <thead>
          <tr className="border-b border-border text-left text-xs text-text-secondary uppercase tracking-wide">
            <th className="w-8 px-2" />
            <th className="px-4 py-3 font-medium">Atom</th>
            <th className="px-4 py-3 font-medium">Eje</th>
            <th className="px-4 py-3 font-medium text-center">
              Questions
            </th>
            <th className="px-4 py-3 font-medium text-right">
              Actions
            </th>
          </tr>
        </thead>
        <tbody>
          {atoms.map((atom) => (
            <AtomRow
              key={atom.id}
              atom={atom}
              isExpanded={expandedAtom === atom.id}
              onToggle={() => onToggle(atom.id)}
              onRunPhase={onRunPhase}
            />
          ))}
        </tbody>
      </table>
      {atoms.length === 0 && (
        <div className="p-8 text-center text-text-secondary text-sm">
          No atoms match the current filter
        </div>
      )}
    </div>
  );
}


// ---------------------------------------------------------------------------
// Atom row with expandable phase controls
// ---------------------------------------------------------------------------

interface AtomRowProps {
  atom: AtomBrief;
  isExpanded: boolean;
  onToggle: () => void;
  onRunPhase: (atomId: string, phase: string) => void;
}

function AtomRow({
  atom,
  isExpanded,
  onToggle,
  onRunPhase,
}: AtomRowProps) {
  const hasQuestions = atom.question_set_count > 0;

  return (
    <>
      <tr
        className={cn(
          "border-b border-border hover:bg-white/5",
          "transition-colors cursor-pointer",
          isExpanded && "bg-white/5",
        )}
        onClick={onToggle}
      >
        <td className="w-8 px-2">
          {isExpanded ? (
            <ChevronDown className="w-4 h-4 text-text-secondary" />
          ) : (
            <ChevronRight className="w-4 h-4 text-text-secondary" />
          )}
        </td>
        <td className="px-4 py-3">
          <div className="text-sm font-medium truncate max-w-xs">
            {atom.titulo}
          </div>
          <div className="text-xs text-text-secondary mt-0.5">
            {atom.id}
          </div>
        </td>
        <td className="px-4 py-3 text-xs text-text-secondary">
          {atom.eje}
        </td>
        <td className="px-4 py-3 text-center">
          <QuestionBadge count={atom.question_set_count} />
        </td>
        <td className="px-4 py-3 text-right">
          <ActionBtn
            hasQuestions={hasQuestions}
            onClick={(e) => {
              e.stopPropagation();
              onRunPhase(atom.id, "all");
            }}
          />
        </td>
      </tr>
      {isExpanded && (
        <tr className="bg-background/50">
          <td colSpan={5} className="p-0">
            <PhaseControls
              atomId={atom.id}
              onRunPhase={onRunPhase}
            />
          </td>
        </tr>
      )}
    </>
  );
}


// ---------------------------------------------------------------------------
// Small presentational helpers
// ---------------------------------------------------------------------------

function QuestionBadge({ count }: { count: number }) {
  if (count > 0) {
    return (
      <span className="inline-flex items-center gap-1 text-sm text-success">
        <CheckCircle2 className="w-3.5 h-3.5" />
        {count}
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-sm text-text-secondary">
      <Circle className="w-3.5 h-3.5" />0
    </span>
  );
}

function ActionBtn({
  hasQuestions,
  onClick,
}: {
  hasQuestions: boolean;
  onClick: (e: React.MouseEvent) => void;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "inline-flex items-center gap-1.5 px-3 py-1.5",
        "rounded-md text-xs font-medium transition-colors",
        hasQuestions
          ? "bg-warning/10 text-warning hover:bg-warning/20"
          : "bg-accent/10 text-accent hover:bg-accent/20",
      )}
    >
      {hasQuestions ? (
        <>
          <RefreshCw className="w-3 h-3" />
          Regenerate
        </>
      ) : (
        <>
          <Sparkles className="w-3 h-3" />
          Generate
        </>
      )}
    </button>
  );
}


// ---------------------------------------------------------------------------
// Phase controls (shown when atom row is expanded)
// ---------------------------------------------------------------------------

function PhaseControls({
  atomId,
  onRunPhase,
}: {
  atomId: string;
  onRunPhase: (atomId: string, phase: string) => void;
}) {
  return (
    <div className="px-6 py-4 border-b border-border">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-semibold text-text-secondary uppercase tracking-wide">
          Run Individual Phases
        </span>
        <button
          onClick={() => onRunPhase(atomId, "all")}
          className={cn(
            "flex items-center gap-1.5 px-3 py-1.5",
            "bg-accent text-white rounded-md text-xs",
            "font-medium hover:bg-accent/90 transition-colors",
          )}
        >
          <Sparkles className="w-3 h-3" />
          Run All
        </button>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
        {PHASES.map((phase, idx) => (
          <button
            key={phase.id}
            onClick={() => onRunPhase(atomId, phase.id)}
            className={cn(
              "flex items-center gap-2 px-3 py-2 text-left group",
              "bg-surface border border-border rounded-md",
              "hover:border-accent/30 transition-colors",
            )}
          >
            <span className="flex items-center justify-center w-5 h-5 rounded-full bg-accent/10 text-accent text-xs font-semibold flex-shrink-0">
              {idx + 1}
            </span>
            <div className="min-w-0 flex-1">
              <div className="text-xs font-medium group-hover:text-accent transition-colors">
                {phase.label}
              </div>
              <div className="text-[10px] text-text-secondary truncate">
                {phase.description}
              </div>
            </div>
            <Play className="w-3 h-3 text-text-secondary group-hover:text-accent transition-colors flex-shrink-0" />
          </button>
        ))}
      </div>
    </div>
  );
}
