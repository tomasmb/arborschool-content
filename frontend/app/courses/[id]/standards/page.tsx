"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { getStandards, type StandardBrief } from "@/lib/api";
import { cn, formatEje, getEjeColor, getEjeBgColor } from "@/lib/utils";

const EJES = [
  { id: "all", label: "All" },
  { id: "numeros", label: "Números" },
  { id: "algebra_y_funciones", label: "Álgebra" },
  { id: "geometria", label: "Geometría" },
  { id: "probabilidad_y_estadistica", label: "Probabilidad" },
];

export default function StandardsPage() {
  const params = useParams();
  const courseId = params.id as string;

  const [standards, setStandards] = useState<StandardBrief[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedEje, setSelectedEje] = useState("all");

  useEffect(() => {
    if (courseId) {
      getStandards(courseId)
        .then(setStandards)
        .catch((err) => setError(err.message))
        .finally(() => setLoading(false));
    }
  }, [courseId]);

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

  const filteredStandards = selectedEje === "all"
    ? standards
    : standards.filter((s) => s.eje === selectedEje);

  // Group standards by eje
  const groupedByEje = filteredStandards.reduce((acc, standard) => {
    if (!acc[standard.eje]) {
      acc[standard.eje] = [];
    }
    acc[standard.eje].push(standard);
    return acc;
  }, {} as Record<string, StandardBrief[]>);

  const ejeOrder = ["numeros", "algebra_y_funciones", "geometria", "probabilidad_y_estadistica"];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link
          href={`/courses/${courseId}`}
          className="p-2 hover:bg-white/5 rounded-lg transition-colors"
        >
          <ArrowLeft className="w-5 h-5 text-text-secondary" />
        </Link>
        <div>
          <h1 className="text-2xl font-semibold">Standards ({standards.length})</h1>
          <p className="text-text-secondary mt-1">
            Learning standards for this course
          </p>
        </div>
      </div>

      {/* Filters */}
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

      {/* Standards grouped by eje */}
      <div className="space-y-8">
        {ejeOrder.map((eje) => {
          const ejeStandards = groupedByEje[eje];
          if (!ejeStandards || ejeStandards.length === 0) return null;

          return (
            <section key={eje}>
              <h2 className={cn(
                "text-sm font-semibold mb-4 uppercase tracking-wide",
                getEjeColor(eje)
              )}>
                {formatEje(eje)} ({ejeStandards.length})
              </h2>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {ejeStandards.map((standard) => (
                  <div
                    key={standard.id}
                    className="bg-surface border border-border rounded-lg p-4"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="font-mono text-xs text-text-secondary">
                            {standard.id}
                          </span>
                          <span
                            className={cn(
                              "text-xs px-2 py-0.5 rounded",
                              getEjeBgColor(standard.eje),
                              getEjeColor(standard.eje)
                            )}
                          >
                            {formatEje(standard.eje)}
                          </span>
                        </div>
                        <p className="text-sm">{standard.title}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-lg font-semibold">{standard.atoms_count}</p>
                        <p className="text-xs text-text-secondary">atoms</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          );
        })}
      </div>

      {filteredStandards.length === 0 && (
        <div className="text-center py-12 text-text-secondary">
          No standards found for this filter.
        </div>
      )}
    </div>
  );
}
