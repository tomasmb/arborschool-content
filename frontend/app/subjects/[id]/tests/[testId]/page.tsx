"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, CheckCircle2, Circle, XCircle } from "lucide-react";
import { getTestDetail, type TestDetail } from "@/lib/api";
import { cn } from "@/lib/utils";

export default function TestDetailPage() {
  const params = useParams();
  const subjectId = params.id as string;
  const testId = params.testId as string;

  const [data, setData] = useState<TestDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (subjectId && testId) {
      getTestDetail(subjectId, testId)
        .then(setData)
        .catch((err) => setError(err.message))
        .finally(() => setLoading(false));
    }
  }, [subjectId, testId]);

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

  const StatusCell = ({ done }: { done: boolean }) =>
    done ? (
      <CheckCircle2 className="w-4 h-4 text-success mx-auto" />
    ) : (
      <Circle className="w-4 h-4 text-text-secondary mx-auto" />
    );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link
          href={`/subjects/${subjectId}`}
          className="p-2 hover:bg-white/5 rounded-lg transition-colors"
        >
          <ArrowLeft className="w-5 h-5 text-text-secondary" />
        </Link>
        <div>
          <h1 className="text-2xl font-semibold">{data.name}</h1>
          {data.application_type && (
            <p className="text-text-secondary mt-1 capitalize">
              {data.application_type} {data.admission_year}
            </p>
          )}
        </div>
      </div>

      {/* Pipeline Status */}
      <div className="flex gap-4">
        {[
          { label: "Raw PDF", value: data.raw_pdf_exists, type: "boolean" },
          { label: "Split", value: `${data.split_count}`, type: "number" },
          { label: "QTI", value: `${data.qti_count}`, type: "number" },
          { label: "Finalized", value: `${data.finalized_count}`, type: "number" },
          {
            label: "Tagged",
            value: `${data.tagged_count}/${data.finalized_count}`,
            type: "fraction",
          },
          { label: "Variants", value: `${data.variants_count}`, type: "number" },
        ].map((item, idx) => (
          <div
            key={item.label}
            className="flex items-center gap-3 bg-surface border border-border rounded-lg px-4 py-2"
          >
            {idx > 0 && <span className="text-text-secondary">→</span>}
            <div className="text-center">
              <p className="text-xs text-text-secondary">{item.label}</p>
              {item.type === "boolean" ? (
                item.value ? (
                  <CheckCircle2 className="w-5 h-5 text-success mx-auto mt-1" />
                ) : (
                  <XCircle className="w-5 h-5 text-error mx-auto mt-1" />
                )
              ) : (
                <p className="font-semibold">{item.value}</p>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Questions Table */}
      <div className="bg-surface border border-border rounded-lg overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-border text-left text-xs text-text-secondary uppercase tracking-wide">
              <th className="px-4 py-3 font-medium">Q#</th>
              <th className="px-4 py-3 font-medium text-center">Split</th>
              <th className="px-4 py-3 font-medium text-center">QTI</th>
              <th className="px-4 py-3 font-medium text-center">Final</th>
              <th className="px-4 py-3 font-medium text-center">Tagged</th>
              <th className="px-4 py-3 font-medium text-center">Atoms</th>
              <th className="px-4 py-3 font-medium text-center">Variants</th>
            </tr>
          </thead>
          <tbody>
            {data.questions.map((q) => (
              <tr
                key={q.id}
                className="border-b border-border last:border-b-0 hover:bg-white/5 transition-colors cursor-pointer"
              >
                <td className="px-4 py-3 font-mono text-sm">
                  Q{q.question_number}
                </td>
                <td className="px-4 py-3">
                  <StatusCell done={q.has_split_pdf} />
                </td>
                <td className="px-4 py-3">
                  <StatusCell done={q.has_qti} />
                </td>
                <td className="px-4 py-3">
                  <StatusCell done={q.is_finalized} />
                </td>
                <td className="px-4 py-3">
                  <StatusCell done={q.is_tagged} />
                </td>
                <td className="px-4 py-3 text-center text-sm">
                  {q.atoms_count > 0 ? (
                    <span className="text-accent">{q.atoms_count}</span>
                  ) : (
                    <span className="text-text-secondary">-</span>
                  )}
                </td>
                <td className="px-4 py-3 text-center text-sm">
                  {q.variants_count > 0 ? (
                    <span className="text-accent">{q.variants_count}</span>
                  ) : (
                    <span className="text-text-secondary">-</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
