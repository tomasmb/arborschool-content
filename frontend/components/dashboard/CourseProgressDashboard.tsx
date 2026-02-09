"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { CheckCircle2, ArrowRight, Play } from "lucide-react";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { StatusIcon } from "@/components/ui/StatusBadge";
import type { SubjectDetail, TestSyncDiff } from "@/lib/api-types";
import { getTestsSyncStatus } from "@/lib/api";
import { computeProgress, type NextActionType } from "./ProgressComputation";
import { KnowledgePipelineCard, TestRow } from "./DashboardCards";

// -----------------------------------------------------------------------------
// Main Component
// -----------------------------------------------------------------------------

export interface CourseProgressDashboardProps {
  data: SubjectDetail;
  courseId: string;
  onViewGraph?: () => void;
  onGenerateStandards?: () => void;
  onGenerateAtoms?: () => void;
}

export function CourseProgressDashboard({
  data,
  courseId,
  onViewGraph,
  onGenerateStandards,
  onGenerateAtoms,
}: CourseProgressDashboardProps) {
  const router = useRouter();
  const progress = computeProgress(data);

  // Fetch sync status for all tests (async, non-blocking)
  const [syncMap, setSyncMap] = useState<Record<string, TestSyncDiff> | undefined>();
  useEffect(() => {
    getTestsSyncStatus(courseId)
      .then((res) => setSyncMap(res.tests))
      .catch(() => setSyncMap({}));
  }, [courseId]);

  const hasTemario = data.temario_exists;
  const hasStandards = data.standards.length > 0;
  const hasAtoms = data.atoms_count > 0;

  /**
   * Handle clicking the "Next" action - navigate to the appropriate page
   * or trigger the appropriate modal.
   */
  const handleNextAction = () => {
    const { nextActionType } = progress;

    switch (nextActionType) {
      case "generate_standards":
        onGenerateStandards?.();
        break;
      case "generate_atoms":
        onGenerateAtoms?.();
        break;
      case "upload_tests":
        router.push(`/courses/${courseId}/tests`);
        break;
      case "run_split":
      case "run_qti_parse":
      case "run_tagging":
      case "run_enrichment":
      case "run_validation":
        router.push(`/courses/${courseId}/tests`);
        break;
      default:
        // For upload_temario and other cases, go to course overview
        router.push(`/courses/${courseId}`);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header with overall progress */}
      <div className="bg-surface border border-border rounded-lg p-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold">{data.full_name}</h2>
          <span className="text-sm text-text-secondary">{data.year}</span>
        </div>

        <ProgressBar
          current={progress.overallPercent}
          total={100}
          showPercent
          size="lg"
          className="mb-3"
        />

        {progress.nextAction && (
          <button
            onClick={handleNextAction}
            className="flex items-center gap-2 text-sm group hover:bg-accent/5 -mx-2 px-2 py-1 rounded transition-colors"
          >
            <Play className="w-4 h-4 text-accent" />
            <span className="text-text-secondary">Next:</span>
            <span className="text-accent font-medium group-hover:underline">
              {progress.nextAction}
            </span>
            <ArrowRight className="w-3 h-3 text-accent opacity-0 group-hover:opacity-100 transition-opacity" />
          </button>
        )}
      </div>

      {/* Knowledge Pipeline */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wide">
            Knowledge Pipeline
          </h3>
          {hasStandards && hasAtoms && (
            <span className="flex items-center gap-1 text-xs text-success">
              <CheckCircle2 className="w-3 h-3" />
              100%
            </span>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <KnowledgePipelineCard
            title="Standards"
            done={hasStandards}
            count={data.standards.length}
            byEje={progress.knowledgePipeline.standards.byEje}
            linkHref={`/courses/${courseId}/standards`}
          />
          <KnowledgePipelineCard
            title="Atoms"
            done={hasAtoms}
            count={data.atoms_count}
            linkHref={`/courses/${courseId}/atoms`}
          />
          <div className="bg-surface border border-border rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <StatusIcon status={hasAtoms ? "complete" : "not_started"} />
              <h4 className="font-medium text-sm">Prerequisites</h4>
            </div>
            {hasAtoms ? (
              <>
                <p className="text-sm text-text-secondary mb-2">
                  View the knowledge graph to see prerequisite links between atoms.
                </p>
                {onViewGraph && (
                  <button onClick={onViewGraph} className="text-accent text-xs hover:underline">
                    View Graph →
                  </button>
                )}
              </>
            ) : (
              <p className="text-sm text-text-secondary">Generate atoms first</p>
            )}
          </div>
        </div>

        {/* Generate actions */}
        {(!hasStandards || !hasAtoms) && (
          <div className="flex gap-2 mt-3">
            {!hasStandards && hasTemario && onGenerateStandards && (
              <button
                onClick={onGenerateStandards}
                className="flex items-center gap-2 px-3 py-1.5 bg-accent text-white rounded text-sm font-medium hover:bg-accent/90"
              >
                Generate Standards
              </button>
            )}
            {hasStandards && !hasAtoms && onGenerateAtoms && (
              <button
                onClick={onGenerateAtoms}
                className="flex items-center gap-2 px-3 py-1.5 bg-accent text-white rounded text-sm font-medium hover:bg-accent/90"
              >
                Generate Atoms
              </button>
            )}
          </div>
        )}
      </section>

      {/* Tests Table */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wide">
            Tests ({data.tests.length})
          </h3>
          <Link href={`/courses/${courseId}/tests`} className="text-accent text-sm hover:underline">
            View all →
          </Link>
        </div>

        <div className="bg-surface border border-border rounded-lg overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border text-left text-xs text-text-secondary uppercase tracking-wide">
                <th className="px-4 py-2 font-medium">Test</th>
                <th className="px-4 py-2 font-medium text-center">Split</th>
                <th className="px-4 py-2 font-medium text-center">QTI</th>
                <th className="px-4 py-2 font-medium text-center">Enriched</th>
                <th className="px-4 py-2 font-medium text-center">Validated</th>
                <th className="px-4 py-2 font-medium text-center">Qs w/Vars</th>
                <th className="px-4 py-2 font-medium text-center">Sync</th>
                <th className="px-4 py-2 font-medium"></th>
              </tr>
            </thead>
            <tbody>
              {data.tests.map((test) => (
                <TestRow
                  key={test.id}
                  test={test}
                  courseId={courseId}
                  syncDiff={syncMap === undefined ? undefined : (syncMap[test.id] ?? null)}
                />
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
