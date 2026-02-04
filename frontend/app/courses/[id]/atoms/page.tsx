"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { ArrowLeft, Filter, Network, ChevronDown, ChevronRight } from "lucide-react";
import { getAtoms, type AtomBrief } from "@/lib/api";
import { cn, formatEje, getEjeColor, getEjeBgColor } from "@/lib/utils";
import { KnowledgeGraphModal } from "@/components/knowledge-graph";

const EJES = [
  { id: "all", label: "All" },
  { id: "numeros", label: "Números" },
  { id: "algebra_y_funciones", label: "Álgebra" },
  { id: "geometria", label: "Geometría" },
  { id: "probabilidad_y_estadistica", label: "Probabilidad" },
];

const ATOM_TYPES: Record<string, string> = {
  concepto: "C",
  procedimiento: "P",
  representacion: "R",
  concepto_procedimental: "CP",
  modelizacion: "M",
  argumentacion: "A",
};

export default function AtomsPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const courseId = params.id as string;
  const standardFilter = searchParams.get("standard");

  const [atoms, setAtoms] = useState<AtomBrief[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedEje, setSelectedEje] = useState("all");
  const [showGraph, setShowGraph] = useState(false);
  const [expandedAtoms, setExpandedAtoms] = useState<Set<string>>(new Set());
  const [activeTab, setActiveTab] = useState<"list" | "graph">("list");

  useEffect(() => {
    if (courseId) {
      const filters: { eje?: string; standard_id?: string } = {};
      if (selectedEje !== "all") filters.eje = selectedEje;
      if (standardFilter) filters.standard_id = standardFilter;

      setLoading(true);
      getAtoms(courseId, filters)
        .then(setAtoms)
        .catch((err) => setError(err.message))
        .finally(() => setLoading(false));
    }
  }, [courseId, selectedEje, standardFilter]);

  const toggleExpanded = useCallback((id: string) => {
    setExpandedAtoms((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

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
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            href={`/courses/${courseId}`}
            className="p-2 hover:bg-white/5 rounded-lg transition-colors"
          >
            <ArrowLeft className="w-5 h-5 text-text-secondary" />
          </Link>
          <div>
            <h1 className="text-2xl font-semibold">Atoms ({atoms.length})</h1>
            <p className="text-text-secondary mt-1">
              Learning atoms for this course
              {standardFilter && (
                <span className="ml-2 text-accent">
                  (filtered by standard: {standardFilter})
                </span>
              )}
            </p>
          </div>
        </div>
      </div>

      {/* Tabs: List vs Graph */}
      <div className="flex items-center justify-between border-b border-border">
        <div className="flex gap-1 -mb-px">
          <button
            onClick={() => setActiveTab("list")}
            className={cn(
              "px-4 py-3 text-sm font-medium border-b-2 transition-colors",
              activeTab === "list"
                ? "border-accent text-accent"
                : "border-transparent text-text-secondary hover:text-text-primary"
            )}
          >
            Atoms List
          </button>
          <button
            onClick={() => setActiveTab("graph")}
            className={cn(
              "px-4 py-3 text-sm font-medium border-b-2 transition-colors flex items-center gap-2",
              activeTab === "graph"
                ? "border-accent text-accent"
                : "border-transparent text-text-secondary hover:text-text-primary"
            )}
          >
            <Network className="w-4 h-4" />
            Prerequisites Graph
          </button>
        </div>

        {activeTab === "list" && (
          <div className="flex items-center gap-2 pb-2">
            <Filter className="w-4 h-4 text-text-secondary" />
            <div className="flex gap-1">
              {EJES.map((eje) => (
                <button
                  key={eje.id}
                  onClick={() => setSelectedEje(eje.id)}
                  className={cn(
                    "px-3 py-1.5 text-sm rounded-lg transition-colors",
                    selectedEje === eje.id
                      ? "bg-accent text-white"
                      : "bg-surface text-text-secondary hover:text-text-primary"
                  )}
                >
                  {eje.label}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Tab content */}
      {activeTab === "list" ? (
        <div className="bg-surface border border-border rounded-lg overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border text-left text-xs text-text-secondary uppercase tracking-wide">
                <th className="w-8 px-2"></th>
                <th className="px-4 py-3 font-medium">ID</th>
                <th className="px-4 py-3 font-medium">Title</th>
                <th className="px-4 py-3 font-medium text-center">Type</th>
                <th className="px-4 py-3 font-medium text-center">Questions</th>
                <th className="px-4 py-3 font-medium text-center">Lesson</th>
              </tr>
            </thead>
            <tbody>
              {atoms.map((atom) => {
                const isExpanded = expandedAtoms.has(atom.id);
                return (
                  <AtomRow
                    key={atom.id}
                    atom={atom}
                    isExpanded={isExpanded}
                    onToggle={() => toggleExpanded(atom.id)}
                    courseId={courseId}
                  />
                );
              })}
            </tbody>
          </table>

          {atoms.length === 0 && (
            <div className="p-8 text-center text-text-secondary">
              No atoms found for this filter.
            </div>
          )}
        </div>
      ) : (
        <div className="bg-surface border border-border rounded-lg p-4">
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm text-text-secondary">
              View the knowledge graph to see prerequisite relationships between atoms.
            </p>
            <button
              onClick={() => setShowGraph(true)}
              className="flex items-center gap-2 px-4 py-2 bg-accent text-white rounded-lg text-sm font-medium hover:bg-accent/90"
            >
              <Network className="w-4 h-4" />
              Open Full Graph
            </button>
          </div>
          <div className="h-96 bg-background rounded-lg flex items-center justify-center text-text-secondary">
            Click "Open Full Graph" for interactive visualization
          </div>
        </div>
      )}

      {/* Knowledge Graph Modal */}
      <KnowledgeGraphModal
        subjectId={courseId}
        isOpen={showGraph}
        onClose={() => setShowGraph(false)}
      />
    </div>
  );
}

interface AtomRowProps {
  atom: AtomBrief;
  isExpanded: boolean;
  onToggle: () => void;
  courseId: string;
}

function AtomRow({ atom, isExpanded, onToggle, courseId }: AtomRowProps) {
  return (
    <>
      <tr
        className={cn(
          "border-b border-border hover:bg-white/5 transition-colors cursor-pointer",
          isExpanded && "bg-white/5"
        )}
        onClick={onToggle}
      >
        <td className="w-8 px-2">
          <span className="inline-flex items-center justify-center w-5 h-5 rounded hover:bg-white/10">
            {isExpanded ? (
              <ChevronDown className="w-4 h-4 text-text-secondary" />
            ) : (
              <ChevronRight className="w-4 h-4 text-text-secondary" />
            )}
          </span>
        </td>
        <td className="px-4 py-3 font-mono text-xs text-text-secondary">
          {atom.id}
        </td>
        <td className="px-4 py-3">
          <div>
            <span className="font-medium">{atom.titulo}</span>
            <span
              className={cn(
                "ml-2 text-xs px-1.5 py-0.5 rounded",
                getEjeBgColor(atom.eje),
                getEjeColor(atom.eje)
              )}
            >
              {formatEje(atom.eje).substring(0, 3)}
            </span>
          </div>
        </td>
        <td className="px-4 py-3 text-center">
          <span className="inline-flex items-center justify-center w-6 h-6 rounded bg-accent/10 text-accent text-xs font-medium">
            {ATOM_TYPES[atom.tipo_atomico] || atom.tipo_atomico.charAt(0).toUpperCase()}
          </span>
        </td>
        <td className="px-4 py-3 text-center text-sm">
          {atom.question_set_count > 0 ? (
            <span className="text-accent">{atom.question_set_count}</span>
          ) : (
            <span className="text-text-secondary">-</span>
          )}
        </td>
        <td className="px-4 py-3 text-center text-sm">
          {atom.has_lesson ? (
            <span className="text-success">✓</span>
          ) : (
            <span className="text-text-secondary">-</span>
          )}
        </td>
      </tr>

      {/* Expanded content */}
      {isExpanded && (
        <tr className="bg-background/50">
          <td colSpan={6} className="p-0">
            <AtomExpandedContent atom={atom} courseId={courseId} />
          </td>
        </tr>
      )}
    </>
  );
}

function AtomExpandedContent({
  atom,
  courseId,
}: {
  atom: AtomBrief;
  courseId: string;
}) {
  return (
    <div className="p-4 border-b border-border">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Left column - Atom details */}
        <div className="space-y-3">
          <h4 className="text-xs font-medium text-text-secondary uppercase tracking-wide">
            Details
          </h4>
          <div className="space-y-2 text-sm">
            <div>
              <span className="text-text-secondary">Type:</span>{" "}
              <span className="capitalize">{atom.tipo_atomico.replace("_", " ")}</span>
            </div>
            <div>
              <span className="text-text-secondary">Eje:</span>{" "}
              <span className={getEjeColor(atom.eje)}>{formatEje(atom.eje)}</span>
            </div>
            <div>
              <span className="text-text-secondary">Standards:</span>{" "}
              <span>{atom.standard_ids.join(", ") || "None"}</span>
            </div>
            <div>
              <span className="text-text-secondary">Question Sets:</span>{" "}
              {atom.question_set_count > 0 ? (
                <span className="text-success">{atom.question_set_count} questions</span>
              ) : (
                <span>None</span>
              )}
            </div>
            <div>
              <span className="text-text-secondary">Lesson:</span>{" "}
              {atom.has_lesson ? (
                <span className="text-success">Yes</span>
              ) : (
                <span>No</span>
              )}
            </div>
          </div>
        </div>

        {/* Right column - Prerequisites info */}
        <div className="space-y-3">
          <h4 className="text-xs font-medium text-text-secondary uppercase tracking-wide flex items-center gap-1">
            <Network className="w-3 h-3" />
            Prerequisites & Dependents
          </h4>
          <p className="text-sm text-text-secondary">
            View this atom in the Prerequisites Graph to see its connections to other atoms.
          </p>
          <p className="text-xs text-text-secondary">
            The graph view shows which atoms this one builds on (prerequisites) and which atoms
            build on this one (dependents).
          </p>
        </div>
      </div>
    </div>
  );
}
