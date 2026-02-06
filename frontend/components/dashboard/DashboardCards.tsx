"use client";

/**
 * Dashboard sub-components for CourseProgressDashboard.
 * Extracted to keep files under 500 lines (DRY/SOLID).
 */

import Link from "next/link";
import { ChevronRight } from "lucide-react";
import { cn, formatEje } from "@/lib/utils";
import { StatusIcon } from "@/components/ui/StatusBadge";
import type { TestBrief } from "@/lib/api-types";
// -----------------------------------------------------------------------------
// Knowledge Pipeline Card
// -----------------------------------------------------------------------------

export function KnowledgePipelineCard({
  title,
  done,
  count,
  byEje,
  linkHref,
}: {
  title: string;
  done: boolean;
  count: number;
  byEje?: Record<string, number>;
  linkHref?: string;
}) {
  return (
    <div className="bg-surface border border-border rounded-lg p-4">
      <div className="flex items-center gap-2 mb-2">
        <StatusIcon status={done ? "complete" : "not_started"} />
        <h4 className="font-medium text-sm">{title}</h4>
      </div>
      <p className={cn("text-2xl font-semibold", done ? "text-success" : "text-text-primary")}>
        {count}
      </p>
      <p className="text-xs text-text-secondary">{done ? "Complete" : "Not generated"}</p>

      {byEje && Object.keys(byEje).length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {Object.entries(byEje).map(([eje, c]) => (
            <span
              key={eje}
              className="text-xs px-1.5 py-0.5 rounded bg-accent/10 text-accent"
              title={formatEje(eje)}
            >
              {c}
            </span>
          ))}
        </div>
      )}

      {linkHref && (
        <Link href={linkHref} className="text-accent text-xs hover:underline mt-2 inline-block">
          View all →
        </Link>
      )}
    </div>
  );
}

// -----------------------------------------------------------------------------
// Test Row
// -----------------------------------------------------------------------------

export function TestRow({ test, courseId }: { test: TestBrief; courseId: string }) {
  const enrichedComplete = test.enriched_count === test.finalized_count && test.finalized_count > 0;
  const validatedComplete =
    test.validated_count === test.finalized_count && test.finalized_count > 0;

  return (
    <tr className="border-b border-border last:border-b-0 hover:bg-white/5 transition-colors">
      <td className="px-4 py-2">
        <div className="font-medium text-sm">{test.name}</div>
        {test.application_type && (
          <div className="text-xs text-text-secondary capitalize">
            {test.application_type} {test.admission_year}
          </div>
        )}
      </td>
      <td className="px-4 py-2 text-center text-sm font-mono">{test.split_count}</td>
      <td className="px-4 py-2 text-center text-sm font-mono">{test.qti_count}</td>
      <td className="px-4 py-2 text-center text-sm">
        <span className={cn("font-mono", enrichedComplete ? "text-success" : "text-text-secondary")}>
          {test.enriched_count}/{test.finalized_count}
        </span>
      </td>
      <td className="px-4 py-2 text-center text-sm">
        <span
          className={cn("font-mono", validatedComplete ? "text-success" : "text-text-secondary")}
        >
          {test.validated_count}/{test.finalized_count}
        </span>
      </td>
      <td className="px-4 py-2 text-center text-sm">
        <span className="font-mono text-text-secondary">{test.variants_count}</span>
      </td>
      <td className="px-4 py-2 text-right">
        <Link href={`/courses/${courseId}/tests/${test.id}`} className="text-accent hover:underline">
          <ChevronRight className="w-4 h-4" />
        </Link>
      </td>
    </tr>
  );
}
