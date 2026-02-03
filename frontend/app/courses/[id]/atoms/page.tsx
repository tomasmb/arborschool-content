"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, Filter, Network } from "lucide-react";
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

export default function AtomsPage() {
  const params = useParams();
  const courseId = params.id as string;

  const [atoms, setAtoms] = useState<AtomBrief[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedEje, setSelectedEje] = useState("all");
  const [showGraph, setShowGraph] = useState(false);

  useEffect(() => {
    if (courseId) {
      const filters = selectedEje === "all" ? {} : { eje: selectedEje };
      getAtoms(courseId, filters)
        .then(setAtoms)
        .catch((err) => setError(err.message))
        .finally(() => setLoading(false));
    }
  }, [courseId, selectedEje]);

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
            </p>
          </div>
        </div>
        <button
          onClick={() => setShowGraph(true)}
          className="flex items-center gap-2 px-4 py-2 bg-accent/10 text-accent rounded-lg text-sm font-medium hover:bg-accent/20 transition-colors"
        >
          <Network className="w-4 h-4" />
          Knowledge Graph
        </button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-2">
        <Filter className="w-4 h-4 text-text-secondary" />
        <div className="flex gap-1">
          {EJES.map((eje) => (
            <button
              key={eje.id}
              onClick={() => {
                setLoading(true);
                setSelectedEje(eje.id);
              }}
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

      {/* Atoms Table */}
      <div className="bg-surface border border-border rounded-lg overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-border text-left text-xs text-text-secondary uppercase tracking-wide">
              <th className="px-4 py-3 font-medium">ID</th>
              <th className="px-4 py-3 font-medium">Title</th>
              <th className="px-4 py-3 font-medium">Eje</th>
              <th className="px-4 py-3 font-medium">Type</th>
              <th className="px-4 py-3 font-medium text-center">Q Set</th>
              <th className="px-4 py-3 font-medium text-center">Lesson</th>
            </tr>
          </thead>
          <tbody>
            {atoms.map((atom) => (
              <tr
                key={atom.id}
                className="border-b border-border last:border-b-0 hover:bg-white/5 transition-colors cursor-pointer"
              >
                <td className="px-4 py-3 font-mono text-xs text-text-secondary">
                  {atom.id}
                </td>
                <td className="px-4 py-3">
                  <span className="font-medium">{atom.titulo}</span>
                </td>
                <td className="px-4 py-3">
                  <span
                    className={cn(
                      "text-xs px-2 py-0.5 rounded",
                      getEjeBgColor(atom.eje),
                      getEjeColor(atom.eje)
                    )}
                  >
                    {formatEje(atom.eje)}
                  </span>
                </td>
                <td className="px-4 py-3 text-sm text-text-secondary capitalize">
                  {atom.tipo_atomico.replace("_", " ")}
                </td>
                <td className="px-4 py-3 text-center text-sm">
                  {atom.question_set_count > 0 ? (
                    <span className="text-success">{atom.question_set_count}</span>
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
            ))}
          </tbody>
        </table>
      </div>

      {/* Knowledge Graph Modal */}
      <KnowledgeGraphModal
        subjectId={courseId}
        isOpen={showGraph}
        onClose={() => setShowGraph(false)}
      />
    </div>
  );
}
