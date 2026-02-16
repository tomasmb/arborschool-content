"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, Loader2 } from "lucide-react";
import { getAtomCheckpoints } from "@/lib/api";
import type { AtomCheckpointData } from "@/lib/api";
import { PipelineProgress } from "./components/PipelineProgress";
import { EnrichmentSection } from "./components/EnrichmentSection";
import { PlanTable } from "./components/PlanTable";
import { QuestionCards } from "./components/QuestionCards";

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

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Scroll to a specific question card when clicking a plan row
  const handleScrollToQuestion = useCallback(
    (slotIndex: number) => {
      const el = document.getElementById(`question-${slotIndex}`);
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "center" });
        el.classList.add("ring-2", "ring-accent/50");
        setTimeout(() => {
          el.classList.remove("ring-2", "ring-accent/50");
        }, 2000);
      }
    },
    [],
  );

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

  const genCount = data.generated_items?.length ?? 0;
  const planCount = data.plan_slots?.length ?? 0;
  const report = data.pipeline_report;

  return (
    <div className="space-y-0">
      {/* Header */}
      <div className="py-6 space-y-4">
        <BackLink courseId={courseId} />
        <div>
          <h1 className="text-2xl font-semibold">{atomId}</h1>
          <p className="text-text-secondary mt-1">
            Pipeline results &middot;{" "}
            <span className="font-medium">{genCount}</span> generated
            {planCount > 0 && (
              <> of <span className="font-medium">{planCount}</span> planned</>
            )}
          </p>
        </div>
      </div>

      {/* Pipeline progress stepper */}
      <PipelineProgress
        availablePhases={data.available_phases}
        report={report}
      />

      {/* Sections (only shown when data exists) */}
      <div className="py-6 space-y-8">
        {data.enrichment && (
          <EnrichmentSection enrichment={data.enrichment} />
        )}

        {data.plan_slots && data.plan_slots.length > 0 && (
          <PlanTable
            slots={data.plan_slots}
            generatedItems={data.generated_items}
            onSlotClick={handleScrollToQuestion}
          />
        )}

        {data.generated_items && data.generated_items.length > 0 && (
          <QuestionCards
            items={data.generated_items}
            planSlots={data.plan_slots}
          />
        )}
      </div>
    </div>
  );
}

function BackLink({ courseId }: { courseId: string }) {
  return (
    <Link
      href={`/courses/${courseId}/question-generation`}
      className="inline-flex items-center gap-2 text-sm text-text-secondary hover:text-text-primary transition-colors"
    >
      <ArrowLeft className="w-4 h-4" />
      Back to Question Generation
    </Link>
  );
}
