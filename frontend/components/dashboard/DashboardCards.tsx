"use client";

/**
 * Dashboard sub-components for CourseProgressDashboard.
 * Extracted to keep files under 500 lines (DRY/SOLID).
 */

import Link from "next/link";
import { ChevronRight } from "lucide-react";
import { cn, formatEje } from "@/lib/utils";
import { StatusIcon } from "@/components/ui/StatusBadge";
import type { TestBrief, TestSyncDiff } from "@/lib/api-types";
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
// Sync Status Cell
// -----------------------------------------------------------------------------

/**
 * Compact sync status indicator for table cells.
 * - null/undefined: still loading (shows "...")
 * - error: shows "N/A" in gray
 * - in sync: green checkmark
 * - needs sync: shows count of new items in warning color
 */
export function SyncStatusCell({ diff }: { diff: TestSyncDiff | null | undefined }) {
  if (diff === undefined) {
    return <span className="text-xs text-text-secondary/50">...</span>;
  }
  if (diff === null || diff.error) {
    return <span className="text-xs text-text-secondary">N/A</span>;
  }
  const newQ = diff.questions.new_count;
  const newV = diff.variants.new_count;
  const totalNew = newQ + newV;

  if (!diff.has_changes) {
    return <span className="text-xs text-success font-medium">In sync</span>;
  }

  const parts: string[] = [];
  if (newQ > 0) parts.push(`${newQ}Q`);
  if (newV > 0) parts.push(`${newV}V`);
  const label = parts.length > 0
    ? `${totalNew} new (${parts.join("+")})`
    : "Changes";

  return <span className="text-xs text-warning font-medium">{label}</span>;
}

// -----------------------------------------------------------------------------
// Test Row
// -----------------------------------------------------------------------------

export function TestRow({
  test, courseId, syncDiff,
}: {
  test: TestBrief;
  courseId: string;
  /** undefined = loading, null = no DB / error */
  syncDiff?: TestSyncDiff | null;
}) {
  const enrichedComplete =
    test.enriched_count === test.finalized_count && test.finalized_count > 0;
  const validatedComplete =
    test.validated_count === test.finalized_count && test.finalized_count > 0;

  // Variant enrichment/validation (show if variants exist)
  const hasVariants = test.variants_count > 0;
  const varEnriched = test.enriched_variants_count ?? 0;
  const varValidated = test.validated_variants_count ?? 0;
  const varEnrichedComplete = hasVariants && varEnriched === test.variants_count;
  const varValidatedComplete = hasVariants && varValidated === test.variants_count;

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
        {hasVariants && (
          <div className={cn(
            "text-xs font-mono",
            varEnrichedComplete ? "text-success/70" : "text-text-secondary/60"
          )}>
            +{varEnriched}/{test.variants_count} var
          </div>
        )}
      </td>
      <td className="px-4 py-2 text-center text-sm">
        <span className={cn(
          "font-mono",
          validatedComplete ? "text-success" : "text-text-secondary"
        )}>
          {test.validated_count}/{test.finalized_count}
        </span>
        {hasVariants && (
          <div className={cn(
            "text-xs font-mono",
            varValidatedComplete ? "text-success/70" : "text-text-secondary/60"
          )}>
            +{varValidated}/{test.variants_count} var
          </div>
        )}
      </td>
      <td className="px-4 py-2 text-center text-sm">
        <span className="font-mono text-text-secondary">{test.variants_count}</span>
      </td>
      <td className="px-4 py-2 text-center">
        <SyncStatusCell diff={syncDiff} />
      </td>
      <td className="px-4 py-2 text-right">
        <Link href={`/courses/${courseId}/tests/${test.id}`} className="text-accent hover:underline">
          <ChevronRight className="w-4 h-4" />
        </Link>
      </td>
    </tr>
  );
}
