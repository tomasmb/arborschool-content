"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  AlertTriangle,
  CheckCircle2,
  Database,
  ArrowRight,
  Play,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { StatusIcon } from "@/components/ui/StatusBadge";
import type { SubjectDetail, SyncStatus } from "@/lib/api-types";
import { computeProgress, type NextActionType } from "./ProgressComputation";
import {
  KnowledgePipelineCard,
  PipelineStageRow,
  SyncStatusItem,
  TestRow,
} from "./DashboardCards";

// -----------------------------------------------------------------------------
// Main Component
// -----------------------------------------------------------------------------

export interface CourseProgressDashboardProps {
  data: SubjectDetail;
  syncStatus: SyncStatus | null;
  courseId: string;
  onViewGraph?: () => void;
  onGenerateStandards?: () => void;
  onGenerateAtoms?: () => void;
}

export function CourseProgressDashboard({
  data,
  syncStatus,
  courseId,
  onViewGraph,
  onGenerateStandards,
  onGenerateAtoms,
}: CourseProgressDashboardProps) {
  const router = useRouter();
  const progress = computeProgress(data);

  const hasTemario = data.temario_exists;
  const hasStandards = data.standards.length > 0;
  const hasAtoms = data.atoms_count > 0;

  // Calculate totals for sync display
  let totalQuestions = 0;
  let totalVariants = 0;
  for (const test of data.tests) {
    totalQuestions += test.finalized_count;
    totalVariants += test.variants_count;
  }

  /**
   * Handle clicking the "Next" action - navigate to the appropriate page
   * or trigger the appropriate modal.
   */
  const handleNextAction = () => {
    const { nextActionType, nextActionTestId } = progress;

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
        // Navigate to the specific test that needs work
        if (nextActionTestId) {
          router.push(`/courses/${courseId}/tests/${nextActionTestId}`);
        } else {
          router.push(`/courses/${courseId}/tests`);
        }
        break;
      default:
        // For upload_temario and other cases, go to settings
        router.push(`/courses/${courseId}/settings`);
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

      {/* Questions Pipeline */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wide">
            Questions Pipeline
          </h3>
          {progress.overallPercent > 0 && (
            <span className="text-xs text-text-secondary">
              Aggregated across {data.tests.length} tests
            </span>
          )}
        </div>

        <div className="bg-surface border border-border rounded-lg overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border text-left text-xs text-text-secondary uppercase tracking-wide">
                <th className="px-4 py-2 font-medium">Stage</th>
                <th className="px-4 py-2 font-medium text-right">Done</th>
                <th className="px-4 py-2 font-medium text-right">Total</th>
                <th className="px-4 py-2 font-medium pl-4">Progress</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {progress.questionsPipeline.map((stage) => (
                <PipelineStageRow key={stage.label} stage={stage} />
              ))}
            </tbody>
          </table>

          {/* Variants section */}
          <div className="border-t border-border px-4 py-3 bg-background/50">
            <h4 className="text-xs font-semibold text-text-secondary uppercase tracking-wide mb-2">
              Variants
            </h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <p className="text-text-secondary text-xs">Questions w/ Variants</p>
                <p className="font-mono">
                  {progress.variants.questionsWithVariants || "—"}/
                  {progress.variants.totalQuestions}
                </p>
              </div>
              <div>
                <p className="text-text-secondary text-xs">Qs w/ Validated Vars</p>
                <p className="font-mono">
                  {progress.variants.questionsWithValidatedVariants || "—"}/
                  {progress.variants.totalQuestions}
                </p>
              </div>
              <div>
                <p className="text-text-secondary text-xs">Total Variants</p>
                <p className="font-mono">{totalVariants}</p>
              </div>
              <div>
                <p className="text-text-secondary text-xs">Avg per Question</p>
                <p className="font-mono">
                  {totalQuestions > 0 ? (totalVariants / totalQuestions).toFixed(1) : "—"}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Action items */}
        {progress.actionItems.length > 0 && (
          <div className="mt-3 space-y-1">
            {progress.actionItems.map((item, i) => (
              <div
                key={i}
                className={cn(
                  "flex items-center gap-2 text-sm",
                  item.type === "warning" ? "text-warning" : "text-text-secondary"
                )}
              >
                <AlertTriangle className="w-4 h-4" />
                <span>
                  {item.count} {item.message}
                </span>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Sync Status */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wide">
            Database Sync Status
          </h3>
        </div>

        <div className="bg-surface border border-border rounded-lg p-4">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-4">
            <SyncStatusItem
              label="Standards"
              count={data.standards.length}
              synced={data.standards.length > 0}
            />
            <SyncStatusItem label="Atoms" count={data.atoms_count} synced={data.atoms_count > 0} />
            <SyncStatusItem label="Questions" count={totalQuestions} synced={totalQuestions > 0} />
            <SyncStatusItem label="Variants" count={totalVariants} synced={totalVariants > 0} />
            <SyncStatusItem
              label="Images"
              count={0}
              synced={false}
              warning={!syncStatus?.s3_configured ? "S3 not configured" : undefined}
            />
          </div>

          <div className="flex items-center justify-between pt-3 border-t border-border">
            <div className="text-sm text-text-secondary">
              {syncStatus?.s3_configured ? (
                <span className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-success" />
                  S3 configured
                </span>
              ) : (
                <span className="flex items-center gap-2 text-warning">
                  <AlertTriangle className="w-4 h-4" />
                  S3 not configured
                </span>
              )}
            </div>
            <Link
              href={`/courses/${courseId}/settings`}
              className="flex items-center gap-2 px-3 py-1.5 bg-accent/10 text-accent rounded text-sm font-medium hover:bg-accent/20"
            >
              <Database className="w-4 h-4" />
              Sync Settings
            </Link>
          </div>
        </div>
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
                <th className="px-4 py-2 font-medium"></th>
              </tr>
            </thead>
            <tbody>
              {data.tests.map((test) => (
                <TestRow key={test.id} test={test} courseId={courseId} />
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
