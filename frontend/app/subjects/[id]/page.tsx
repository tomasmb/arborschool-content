"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  CheckCircle2,
  Circle,
  Network,
  ChevronRight,
} from "lucide-react";
import { getSubject, type SubjectDetail } from "@/lib/api";
import { cn, formatEje, getEjeColor, getEjeBgColor } from "@/lib/utils";
import { KnowledgeGraphModal } from "@/components/knowledge-graph";

export default function SubjectPage() {
  const params = useParams();
  const subjectId = params.id as string;

  const [data, setData] = useState<SubjectDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [showGraph, setShowGraph] = useState(false);

  useEffect(() => {
    if (subjectId) {
      getSubject(subjectId)
        .then(setData)
        .catch((err) => setError(err.message))
        .finally(() => setLoading(false));
    }
  }, [subjectId]);

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

  if (!data) return null;

  const StatusIcon = ({ done }: { done: boolean }) =>
    done ? (
      <CheckCircle2 className="w-5 h-5 text-success" />
    ) : (
      <Circle className="w-5 h-5 text-text-secondary" />
    );

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold">{data.full_name}</h1>
          <p className="text-text-secondary mt-1">{data.year}</p>
        </div>
        <button
          onClick={() => setShowGraph(true)}
          className="flex items-center gap-2 px-4 py-2 bg-accent/10 text-accent rounded-lg text-sm font-medium hover:bg-accent/20 transition-colors"
        >
          <Network className="w-4 h-4" />
          Knowledge Graph
        </button>
      </div>

      {/* Knowledge Graph Pipeline */}
      <section>
        <h2 className="text-lg font-semibold mb-4 text-text-secondary uppercase tracking-wide text-xs">
          Knowledge Graph Pipeline
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Temario */}
          <div className="bg-surface border border-border rounded-lg p-4">
            <div className="flex items-center gap-3 mb-3">
              <StatusIcon done={data.temario_exists} />
              <h3 className="font-medium">1. Temario</h3>
            </div>
            <p className="text-text-secondary text-sm mb-3">
              {data.temario_exists ? "Parsed from DEMRE PDF" : "Not yet parsed"}
            </p>
            {data.temario_file && (
              <p className="text-xs text-text-secondary font-mono truncate">
                {data.temario_file}
              </p>
            )}
          </div>

          {/* Standards */}
          <div className="bg-surface border border-border rounded-lg p-4">
            <div className="flex items-center gap-3 mb-3">
              <StatusIcon done={data.standards.length > 0} />
              <h3 className="font-medium">2. Standards</h3>
            </div>
            <p className="text-text-secondary text-sm mb-3">
              {data.standards.length > 0
                ? `${data.standards.length} standards defined`
                : "Not yet generated"}
            </p>
            {data.standards.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {["numeros", "algebra_y_funciones", "geometria", "probabilidad_y_estadistica"].map(
                  (eje) => {
                    const count = data.standards.filter((s) => s.eje === eje).length;
                    if (count === 0) return null;
                    return (
                      <span
                        key={eje}
                        className={cn(
                          "text-xs px-2 py-0.5 rounded",
                          getEjeBgColor(eje),
                          getEjeColor(eje)
                        )}
                      >
                        {count}
                      </span>
                    );
                  }
                )}
              </div>
            )}
          </div>

          {/* Atoms */}
          <div className="bg-surface border border-border rounded-lg p-4">
            <div className="flex items-center gap-3 mb-3">
              <StatusIcon done={data.atoms_count > 0} />
              <h3 className="font-medium">3. Atoms</h3>
            </div>
            <p className="text-text-secondary text-sm mb-3">
              {data.atoms_count > 0
                ? `${data.atoms_count} learning atoms`
                : "Not yet generated"}
            </p>
            <Link
              href={`/subjects/${subjectId}/atoms`}
              className="text-accent text-sm hover:underline"
            >
              View atoms →
            </Link>
          </div>
        </div>
      </section>

      {/* Tests & Questions */}
      <section>
        <h2 className="text-lg font-semibold mb-4 text-text-secondary uppercase tracking-wide text-xs">
          Tests & Questions
        </h2>

        <div className="bg-surface border border-border rounded-lg overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border text-left text-xs text-text-secondary uppercase tracking-wide">
                <th className="px-4 py-3 font-medium">Test</th>
                <th className="px-4 py-3 font-medium text-center">Raw</th>
                <th className="px-4 py-3 font-medium text-center">Split</th>
                <th className="px-4 py-3 font-medium text-center">QTI</th>
                <th className="px-4 py-3 font-medium text-center">Tagged</th>
                <th className="px-4 py-3 font-medium text-center">Variants</th>
                <th className="px-4 py-3 font-medium"></th>
              </tr>
            </thead>
            <tbody>
              {data.tests.map((test) => (
                <tr
                  key={test.id}
                  className="border-b border-border last:border-b-0 hover:bg-white/5 transition-colors"
                >
                  <td className="px-4 py-3">
                    <div className="font-medium">{test.name}</div>
                    {test.application_type && (
                      <div className="text-xs text-text-secondary capitalize">
                        {test.application_type} {test.admission_year}
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3 text-center">
                    {test.raw_pdf_exists ? (
                      <CheckCircle2 className="w-4 h-4 text-success mx-auto" />
                    ) : (
                      <Circle className="w-4 h-4 text-text-secondary mx-auto" />
                    )}
                  </td>
                  <td className="px-4 py-3 text-center text-sm">
                    {test.split_count}
                  </td>
                  <td className="px-4 py-3 text-center text-sm">
                    {test.qti_count}
                  </td>
                  <td className="px-4 py-3 text-center text-sm">
                    <span
                      className={cn(
                        test.tagged_count === test.finalized_count &&
                          test.tagged_count > 0
                          ? "text-success"
                          : "text-text-secondary"
                      )}
                    >
                      {test.tagged_count}/{test.finalized_count}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center text-sm">
                    {test.variants_count}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Link
                      href={`/subjects/${subjectId}/tests/${test.id}`}
                      className="text-accent hover:text-accent/80"
                    >
                      <ChevronRight className="w-4 h-4" />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Knowledge Graph Modal */}
      <KnowledgeGraphModal
        subjectId={subjectId}
        isOpen={showGraph}
        onClose={() => setShowGraph(false)}
      />
    </div>
  );
}
