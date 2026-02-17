"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, Loader2, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";
import { getAtomCheckpoints } from "@/lib/api";
import type { AtomCheckpointData } from "@/lib/api";
import type { GeneratedItem } from "@/lib/api-types-question-gen";
import { PipelineProgress } from "./components/PipelineProgress";
import { EnrichmentSection } from "./components/EnrichmentSection";
import { PlanTable } from "./components/PlanTable";
import { QuestionCards } from "./components/QuestionCards";
import { ValidationSummary } from "./components/ValidationSummary";

export default function AtomDetailPage() {
  const params = useParams();
  const courseId = params.id as string;
  const atomId = params.atomId as string;

  const [data, setData] = useState<AtomCheckpointData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const result = await getAtomCheckpoints(atomId);
      setData(result);
      setError(null);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load",
      );
    } finally {
      setLoading(false);
    }
  }, [atomId]);

  /** Re-fetch data without showing the full-page loading spinner. */
  const silentRefresh = useCallback(async () => {
    try {
      const result = await getAtomCheckpoints(atomId);
      setData(result);
    } catch {
      // Silent — don't overwrite existing data on background error
    }
  }, [atomId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-accent" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-4">
        <BackLink courseId={courseId} />
        <div className="flex items-center justify-center h-64">
          <div className="text-error">Error: {error}</div>
        </div>
      </div>
    );
  }

  if (!data) return null;

  return (
    <AtomDetailContent
      data={data}
      courseId={courseId}
      atomId={atomId}
      onRefresh={fetchData}
      onSilentRefresh={silentRefresh}
    />
  );
}

// ---------------------------------------------------------------------------
// Main content (extracted to avoid hooks after early returns)
// ---------------------------------------------------------------------------

function AtomDetailContent({
  data,
  courseId,
  atomId,
  onRefresh,
  onSilentRefresh,
}: {
  data: AtomCheckpointData;
  courseId: string;
  atomId: string;
  onRefresh: () => void;
  onSilentRefresh: () => void;
}) {
  const hasValidation =
    !!data.validation_results &&
    data.validation_results.length > 0;
  const hasFinalValidation = data.final_items !== null;

  // Merge all item phases into one list (latest phase wins)
  const { mergedItems, passedIds, finalPassedIds } = useMemo(() => {
    const map = new Map<string, GeneratedItem>();
    for (const item of data.generated_items ?? []) {
      map.set(item.item_id, item);
    }
    for (const item of data.validation_results ?? []) {
      map.set(item.item_id, item);
    }
    for (const item of data.feedback_items ?? []) {
      map.set(item.item_id, item);
    }
    for (const item of data.final_items ?? []) {
      map.set(item.item_id, item);
    }
    const merged = Array.from(map.values()).sort(
      (a, b) => a.slot_index - b.slot_index,
    );
    const passed = new Set(
      data.validation_results?.map((i) => i.item_id) ?? [],
    );
    const finalPassed = new Set(
      data.final_items?.map((i) => i.item_id) ?? [],
    );
    return {
      mergedItems: merged, passedIds: passed, finalPassedIds: finalPassed,
    };
  }, [data]);

  const genCount = data.generated_items?.length ?? 0;
  const planCount = data.plan_slots?.length ?? 0;

  // Build an "active" report that strips stale errors for items
  // that have since passed validation (e.g. via single-item reval).
  const report = useMemo(() => {
    const raw = data.pipeline_report;
    if (!raw || passedIds.size === 0) return raw;
    return {
      ...raw,
      total_passed_base_validation: Math.max(
        raw.total_passed_base_validation,
        passedIds.size,
      ),
      phases: raw.phases.map((phase) => ({
        ...phase,
        errors: phase.errors.filter((err) => {
          const colonIdx = err.indexOf(":");
          if (colonIdx <= 0) return true;
          const itemId = err.slice(0, colonIdx).trim();
          return !passedIds.has(itemId);
        }),
      })),
    };
  }, [data.pipeline_report, passedIds]);

  // Trigger to programmatically set "fail" filter in QuestionCards
  const [failTrigger, setFailTrigger] = useState(0);

  // Scroll to questions section
  const handleScrollToQuestion = useCallback(
    (slotIndex: number) => {
      const el = document.getElementById(`question-${slotIndex}`);
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "center" });
        el.classList.add("ring-2", "ring-accent/50");
        setTimeout(
          () => el.classList.remove("ring-2", "ring-accent/50"),
          2000,
        );
      }
    },
    [],
  );

  const handleFilterFailed = useCallback(() => {
    setFailTrigger((n) => n + 1);
    // Small delay so the filter applies before scrolling
    setTimeout(() => {
      document
        .getElementById("questions-section")
        ?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 50);
  }, []);

  return (
    <div className="space-y-6 pb-4">
      {/* Header */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <BackLink courseId={courseId} />
          <button
            onClick={onRefresh}
            className={cn(
              "inline-flex items-center gap-1.5",
              "px-2.5 py-1 rounded-md border border-border text-xs",
              "text-text-secondary hover:text-text-primary",
              "hover:bg-white/[0.06] transition-colors",
            )}
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Refresh
          </button>
        </div>
        <div>
          <h1 className="text-xl font-semibold tracking-tight">
            {atomId}
          </h1>
          <p className="text-sm text-text-secondary mt-1">
            {genCount > 0 ? (
              <>
                <span className="font-medium text-text-primary">
                  {genCount}
                </span>{" "}
                generated
                {planCount > 0 && (
                  <>
                    {" "}of{" "}
                    <span className="font-medium text-text-primary">
                      {planCount}
                    </span>{" "}
                    planned
                  </>
                )}
              </>
            ) : (
              "No questions generated yet"
            )}
          </p>
        </div>
      </div>

      {/* Pipeline progress (hero section) */}
      <PipelineProgress
        availablePhases={data.available_phases}
        report={report}
      />

      {/* Enrichment (collapsed by default) */}
      {data.enrichment && (
        <EnrichmentSection enrichment={data.enrichment} />
      )}

      {/* Plan table (collapsed by default) */}
      {data.plan_slots && data.plan_slots.length > 0 && (
        <PlanTable
          slots={data.plan_slots}
          generatedItems={data.generated_items}
          onSlotClick={handleScrollToQuestion}
        />
      )}

      {/* Validation summary */}
      {hasValidation && (
        <ValidationSummary
          validatedItems={data.validation_results!}
          generatedItems={data.generated_items}
          report={report}
          onFilterFailed={handleFilterFailed}
          finalItems={data.final_items}
          feedbackItems={data.feedback_items}
        />
      )}

      {/* Questions section */}
      {mergedItems.length > 0 && (
        <div id="questions-section">
          <QuestionCards
            items={mergedItems}
            planSlots={data.plan_slots}
            sectionTitle={
              hasValidation || hasFinalValidation
                ? "All Questions"
                : "Generated Questions"
            }
            hasValidation={hasValidation}
            passedIds={passedIds}
            finalPassedIds={finalPassedIds}
            hasFinalValidation={hasFinalValidation}
            filterFailedTrigger={failTrigger}
            atomId={atomId}
            onItemRevalidated={onSilentRefresh}
          />
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Back link
// ---------------------------------------------------------------------------

function BackLink({ courseId }: { courseId: string }) {
  return (
    <Link
      href={`/courses/${courseId}/question-generation`}
      className={cn(
        "inline-flex items-center gap-2 text-sm",
        "text-text-secondary hover:text-text-primary",
        "transition-colors",
      )}
    >
      <ArrowLeft className="w-4 h-4" />
      Back to Question Generation
    </Link>
  );
}
