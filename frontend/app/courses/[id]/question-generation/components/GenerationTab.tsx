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
  Lock,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { AtomBrief } from "@/lib/api";
import { ImageStatusBadge, CoverageBadge } from "./StatusBadges";
import { BatchGenMenu } from "./BatchGenMenu";
import { PhaseControls } from "./PhaseControls";

type AtomFilter =
  | "all" | "pending" | "generated"
  | "covered" | "no_coverage" | "needs_enrichment";

export interface BatchGenOptions {
  mode: string;
  skip_images: string;
}

interface GenerationTabProps {
  atoms: AtomBrief[];
  onRunPhase: (atomId: string, phase: string) => void;
  onBatchEnrich?: (mode: string) => void;
  onBatchGenerate?: (options: BatchGenOptions) => void;
}

export function GenerationTab({
  atoms, onRunPhase, onBatchEnrich, onBatchGenerate,
}: GenerationTabProps) {
  const [filter, setFilter] = useState<AtomFilter>("all");
  const [expandedAtom, setExpandedAtom] = useState<string | null>(null);

  const generated = atoms.filter((a) => a.generated_question_count > 0);
  const pending = atoms.filter((a) => a.generated_question_count === 0);
  const covered = atoms.filter((a) => a.question_coverage !== "none");
  const noCoverage = atoms.filter((a) => a.question_coverage === "none");
  const needsEnrichment = atoms.filter(
    (a) => a.image_status === "not_enriched" && a.question_coverage !== "none",
  );
  const totalQs = atoms.reduce((s, a) => s + a.generated_question_count, 0);

  const filtered = (() => {
    switch (filter) {
      case "pending": return pending;
      case "generated": return generated;
      case "covered": return covered;
      case "no_coverage": return noCoverage;
      case "needs_enrichment": return needsEnrichment;
      default: return atoms;
    }
  })();

  const filters: { id: AtomFilter; label: string; count: number }[] = [
    { id: "all", label: "All", count: atoms.length },
    { id: "covered", label: "Has Coverage", count: covered.length },
    { id: "no_coverage", label: "No Coverage", count: noCoverage.length },
    { id: "needs_enrichment", label: "Needs Enrichment", count: needsEnrichment.length },
    { id: "pending", label: "Pending", count: pending.length },
    { id: "generated", label: "Generated", count: generated.length },
  ];

  return (
    <div className="space-y-5">
      <HeaderStats
        generated={generated.length}
        total={atoms.length}
        totalQs={totalQs}
        onBatchEnrich={onBatchEnrich}
        onBatchGenerate={onBatchGenerate}
      />
      <FilterBar filters={filters} active={filter} onChange={setFilter} />
      <AtomTable
        atoms={filtered}
        expandedAtom={expandedAtom}
        onToggle={(id) => setExpandedAtom(expandedAtom === id ? null : id)}
        onRunPhase={onRunPhase}
      />
    </div>
  );
}


// ---------------------------------------------------------------------------
// Header stats
// ---------------------------------------------------------------------------

function HeaderStats({
  generated, total, totalQs, onBatchEnrich, onBatchGenerate,
}: {
  generated: number;
  total: number;
  totalQs: number;
  onBatchEnrich?: (mode: string) => void;
  onBatchGenerate?: (options: BatchGenOptions) => void;
}) {
  const [showEnrichMenu, setShowEnrichMenu] = useState(false);
  const [showBatchGenMenu, setShowBatchGenMenu] = useState(false);
  return (
    <div className="flex items-start justify-between gap-4">
      <div className="space-y-1">
        <h3 className="font-semibold">Question Generation</h3>
        <div className="flex gap-4 text-sm">
          <div>
            <span className="text-text-secondary">Generated:</span>{" "}
            <span className="font-medium">{generated}/{total}</span>
          </div>
          <div>
            <span className="text-text-secondary">Total Qs:</span>{" "}
            <span className="font-medium">{totalQs}</span>
          </div>
        </div>
      </div>
      <div className="flex items-center gap-2">
        {onBatchGenerate && (
          <div className="relative">
            <button
              onClick={() => setShowBatchGenMenu((v) => !v)}
              className={cn(
                "flex items-center gap-1.5 px-4 py-2",
                "bg-accent text-white rounded-lg text-sm",
                "font-medium hover:bg-accent/90 transition-colors",
              )}
            >
              <Play className="w-4 h-4" />
              Batch Generate
              <ChevronDown className="w-3 h-3" />
            </button>
            {showBatchGenMenu && (
              <BatchGenMenu
                onSelect={(opts) => {
                  onBatchGenerate(opts);
                  setShowBatchGenMenu(false);
                }}
                onClose={() => setShowBatchGenMenu(false)}
              />
            )}
          </div>
        )}
        {onBatchEnrich && (
          <div className="relative">
            <button
              onClick={() => setShowEnrichMenu((v) => !v)}
              className={cn(
                "flex items-center gap-1.5 px-4 py-2",
                "bg-surface border border-border rounded-lg text-sm",
                "font-medium hover:bg-white/5 transition-colors",
              )}
            >
              <Sparkles className="w-4 h-4" />
              Enrich All
              <ChevronDown className="w-3 h-3" />
            </button>
            {showEnrichMenu && (
              <div className="absolute right-0 mt-1 w-52 bg-surface border border-border rounded-lg shadow-lg z-10">
                <button
                  onClick={() => { onBatchEnrich("unenriched_only"); setShowEnrichMenu(false); }}
                  className="w-full px-4 py-2 text-left text-sm hover:bg-white/5 rounded-t-lg"
                >
                  Unenriched only
                </button>
                <button
                  onClick={() => { onBatchEnrich("all"); setShowEnrichMenu(false); }}
                  className="w-full px-4 py-2 text-left text-sm hover:bg-white/5 rounded-b-lg text-warning"
                >
                  Re-enrich all
                </button>
              </div>
            )}
          </div>
        )}
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
    <div className="flex gap-1 border-b border-border overflow-x-auto">
      {filters.map((f) => (
        <button
          key={f.id}
          onClick={() => onChange(f.id)}
          className={cn(
            "px-3 py-2 text-sm font-medium border-b-2 -mb-px",
            "transition-colors whitespace-nowrap flex-shrink-0",
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
    <div className="bg-surface border border-border rounded-lg overflow-x-auto">
      <table className="w-full min-w-[700px]">
        <thead>
          <tr className="border-b border-border text-left text-xs text-text-secondary uppercase tracking-wide">
            <th className="w-8 px-2" />
            <th className="px-3 py-3 font-medium">Atom</th>
            <th className="px-3 py-3 font-medium hidden md:table-cell">Eje</th>
            <th className="px-3 py-3 font-medium text-center">Images</th>
            <th className="px-3 py-3 font-medium text-center">Coverage</th>
            <th className="px-3 py-3 font-medium text-center">Qs</th>
            <th className="px-3 py-3 font-medium text-right">Actions</th>
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
  atom, isExpanded, onToggle, onRunPhase,
}: AtomRowProps) {
  const hasQuestions = atom.generated_question_count > 0;
  const blocked = atom.question_coverage === "none";

  return (
    <>
      <tr
        className={cn(
          "border-b border-border hover:bg-white/5 transition-colors",
          blocked ? "opacity-60 cursor-default" : "cursor-pointer",
          isExpanded && "bg-white/5",
        )}
        onClick={blocked ? undefined : onToggle}
        title={blocked ? "No PAES questions associated" : undefined}
      >
        <td className="w-8 px-2">
          {blocked ? (
            <Lock className="w-4 h-4 text-text-secondary" />
          ) : isExpanded ? (
            <ChevronDown className="w-4 h-4 text-text-secondary" />
          ) : (
            <ChevronRight className="w-4 h-4 text-text-secondary" />
          )}
        </td>
        <td className="px-3 py-3">
          <div className="text-sm font-medium truncate max-w-[180px]">{atom.titulo}</div>
          <div className="text-xs text-text-secondary mt-0.5">{atom.id}</div>
        </td>
        <td className="px-3 py-3 text-xs text-text-secondary hidden md:table-cell">
          {atom.eje}
        </td>
        <td className="px-3 py-3 text-center">
          <ImageStatusBadge status={atom.image_status} />
        </td>
        <td className="px-3 py-3 text-center">
          <CoverageBadge
            coverage={atom.question_coverage}
            directCount={atom.direct_question_count}
          />
        </td>
        <td className="px-3 py-3 text-center">
          <QuestionBadge count={atom.generated_question_count} />
        </td>
        <td className="px-3 py-3 text-right">
          {blocked ? (
            <span className="text-xs text-text-secondary">Blocked</span>
          ) : (
            <ActionBtn
              hasQuestions={hasQuestions}
              onClick={(e) => { e.stopPropagation(); onRunPhase(atom.id, "all"); }}
            />
          )}
        </td>
      </tr>
      {isExpanded && !blocked && (
        <tr className="bg-background/50">
          <td colSpan={7} className="p-0">
            <PhaseControls
              atomId={atom.id}
              lastCompletedPhase={atom.last_completed_phase}
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




