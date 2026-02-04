"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, ChevronDown, ChevronRight } from "lucide-react";
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
  const [expandedStandards, setExpandedStandards] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (courseId) {
      getStandards(courseId)
        .then(setStandards)
        .catch((err) => setError(err.message))
        .finally(() => setLoading(false));
    }
  }, [courseId]);

  const toggleExpanded = useCallback((id: string) => {
    setExpandedStandards((prev) => {
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

              <div className="bg-surface border border-border rounded-lg overflow-hidden">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-border text-left text-xs text-text-secondary uppercase tracking-wide">
                      <th className="w-8 px-2"></th>
                      <th className="px-4 py-3 font-medium">ID</th>
                      <th className="px-4 py-3 font-medium">Title</th>
                      <th className="px-4 py-3 font-medium text-right">Atoms</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ejeStandards.map((standard) => {
                      const isExpanded = expandedStandards.has(standard.id);
                      return (
                        <StandardRow
                          key={standard.id}
                          standard={standard}
                          isExpanded={isExpanded}
                          onToggle={() => toggleExpanded(standard.id)}
                          courseId={courseId}
                        />
                      );
                    })}
                  </tbody>
                </table>
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

interface StandardRowProps {
  standard: StandardBrief;
  isExpanded: boolean;
  onToggle: () => void;
  courseId: string;
}

function StandardRow({ standard, isExpanded, onToggle, courseId }: StandardRowProps) {
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
        <td className="px-4 py-3">
          <span className="font-mono text-xs text-text-secondary">{standard.id}</span>
        </td>
        <td className="px-4 py-3 text-sm">{standard.title}</td>
        <td className="px-4 py-3 text-right">
          <span className="text-accent font-semibold">{standard.atoms_count}</span>
        </td>
      </tr>

      {/* Expanded content */}
      {isExpanded && (
        <tr className="bg-background/50">
          <td colSpan={4} className="p-0">
            <StandardExpandedContent standard={standard} courseId={courseId} />
          </td>
        </tr>
      )}
    </>
  );
}

function StandardExpandedContent({ standard, courseId }: { standard: StandardBrief; courseId: string }) {
  return (
    <div className="p-4 border-b border-border">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Left column - Standard details */}
        <div className="space-y-4">
          <div>
            <h4 className="text-xs font-medium text-text-secondary uppercase tracking-wide mb-2">
              Standard Info
            </h4>
            <div className="space-y-2 text-sm">
              <div>
                <span className="text-text-secondary">ID:</span>{" "}
                <span className="font-mono">{standard.id}</span>
              </div>
              <div>
                <span className="text-text-secondary">Eje:</span>{" "}
                <span>{formatEje(standard.eje)}</span>
              </div>
              <div>
                <span className="text-text-secondary">Atoms linked:</span>{" "}
                <span className="text-accent">{standard.atoms_count}</span>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <h4 className="text-xs font-medium text-text-secondary uppercase tracking-wide mb-2">
                Description
              </h4>
              <p className="text-sm text-text-secondary">
                {standard.title}
              </p>
            </div>
          </div>
        </div>

        {/* Right column - Linked atoms */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-xs font-medium text-text-secondary uppercase tracking-wide">
              Linked Atoms
            </h4>
            {standard.atoms_count > 0 && (
              <Link
                href={`/courses/${courseId}/atoms?standard=${standard.id}`}
                className="text-xs text-accent hover:underline"
              >
                View all {standard.atoms_count} atoms →
              </Link>
            )}
          </div>
          <div className="bg-surface border border-border rounded-lg p-3">
            {standard.atoms_count > 0 ? (
              <p className="text-sm">
                <span className="text-success font-medium">{standard.atoms_count}</span>{" "}
                <span className="text-text-secondary">atoms are linked to this standard.</span>
              </p>
            ) : (
              <p className="text-sm text-text-secondary">No atoms linked yet</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
