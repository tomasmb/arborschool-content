"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, CheckCircle2, Circle, ChevronRight } from "lucide-react";
import { getTests, getTestRawPdfUrl, type TestBrief } from "@/lib/api";
import { cn } from "@/lib/utils";

export default function TestsPage() {
  const params = useParams();
  const courseId = params.id as string;

  const [tests, setTests] = useState<TestBrief[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (courseId) {
      getTests(courseId)
        .then(setTests)
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
          <h1 className="text-2xl font-semibold">Tests ({tests.length})</h1>
          <p className="text-text-secondary mt-1">
            All tests for this course
          </p>
        </div>
      </div>

      {/* Tests Table */}
      <div className="bg-surface border border-border rounded-lg overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-border text-left text-xs text-text-secondary uppercase tracking-wide">
              <th className="px-4 py-3 font-medium">Test</th>
              <th className="px-4 py-3 font-medium text-center">Raw PDF</th>
              <th className="px-4 py-3 font-medium text-center">Split</th>
              <th className="px-4 py-3 font-medium text-center">QTI</th>
              <th className="px-4 py-3 font-medium text-center">Tagged</th>
              <th className="px-4 py-3 font-medium text-center">Enriched</th>
              <th className="px-4 py-3 font-medium text-center">Validated</th>
              <th className="px-4 py-3 font-medium text-center">Variants</th>
              <th className="px-4 py-3 font-medium"></th>
            </tr>
          </thead>
          <tbody>
            {tests.map((test) => {
              const hasVariants = test.variants_count > 0;
              const varEnriched = test.enriched_variants_count ?? 0;
              const varValidated = test.validated_variants_count ?? 0;

              return (
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
                      <a
                        href={getTestRawPdfUrl(courseId, test.id)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center justify-center hover:opacity-80"
                        title="View raw PDF"
                      >
                        <CheckCircle2 className="w-4 h-4 text-success" />
                      </a>
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
                        test.tagged_count === test.finalized_count && test.tagged_count > 0
                          ? "text-success"
                          : "text-text-secondary"
                      )}
                    >
                      {test.tagged_count}/{test.finalized_count}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center text-sm">
                    <span
                      className={cn(
                        "font-mono",
                        test.enriched_count === test.finalized_count && test.finalized_count > 0
                          ? "text-success"
                          : "text-text-secondary"
                      )}
                    >
                      {test.enriched_count}/{test.finalized_count}
                    </span>
                    {hasVariants && (
                      <div className={cn(
                        "text-xs font-mono",
                        varEnriched === test.variants_count
                          ? "text-success/70" : "text-text-secondary/60"
                      )}>
                        +{varEnriched}/{test.variants_count} var
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3 text-center text-sm">
                    <span
                      className={cn(
                        "font-mono",
                        test.validated_count === test.finalized_count && test.finalized_count > 0
                          ? "text-success"
                          : "text-text-secondary"
                      )}
                    >
                      {test.validated_count}/{test.finalized_count}
                    </span>
                    {hasVariants && (
                      <div className={cn(
                        "text-xs font-mono",
                        varValidated === test.variants_count
                          ? "text-success/70" : "text-text-secondary/60"
                      )}>
                        +{varValidated}/{test.variants_count} var
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3 text-center text-sm">
                    {test.variants_count}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Link
                      href={`/courses/${courseId}/tests/${test.id}`}
                      className="text-accent hover:text-accent/80"
                    >
                      <ChevronRight className="w-4 h-4" />
                    </Link>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {tests.length === 0 && (
        <div className="text-center py-12 text-text-secondary">
          No tests found for this course.
        </div>
      )}
    </div>
  );
}
