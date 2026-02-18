"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { getAtoms, type AtomBrief } from "@/lib/api";
import { GeneratePipelineModal } from "@/components/pipelines/GeneratePipelineModal";
import {
  QuestionGenTabs,
  type QGenTab,
} from "./components/QuestionGenTabs";
import { OverviewTab } from "./components/OverviewTab";
import {
  GenerationTab,
  type BatchGenOptions,
} from "./components/GenerationTab";
import { ResultsTab } from "./components/ResultsTab";
import { GenQuestionSyncTab } from "./components/GenQuestionSyncTab";
import { BatchEnrichModal } from "./components/BatchEnrichModal";

const PIPELINE_INFO = {
  id: "question_gen",
  name: "Question Generation",
  description:
    "Generate PAES-style question pools per atom (PP100)",
};

export default function QuestionGenerationPage() {
  const params = useParams();
  const courseId = params.id as string;

  const [atoms, setAtoms] = useState<AtomBrief[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<QGenTab>("overview");

  // Modal state
  const [showGeneration, setShowGeneration] = useState(false);
  const [selectedAtomId, setSelectedAtomId] = useState<string>("");
  const [selectedPhase, setSelectedPhase] = useState<string>("all");
  const [showBatchEnrich, setShowBatchEnrich] = useState(false);
  const [batchEnrichMode, setBatchEnrichMode] = useState("unenriched_only");
  const [showBatchGen, setShowBatchGen] = useState(false);
  const [batchGenOptions, setBatchGenOptions] = useState<BatchGenOptions>({
    mode: "pending_only",
    skip_images: "true",
  });

  const fetchData = useCallback(async () => {
    try {
      const data = await getAtoms(courseId);
      setAtoms(data);
      setError(null);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load",
      );
    } finally {
      setLoading(false);
    }
  }, [courseId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handlePipelineSuccess = useCallback(() => {
    setShowGeneration(false);
    fetchData();
  }, [fetchData]);

  /** Launch pipeline modal for a specific atom + phase */
  const handleRunPhase = useCallback(
    (atomId: string, phase: string) => {
      setSelectedAtomId(atomId);
      setSelectedPhase(phase);
      setShowGeneration(true);
    },
    [],
  );

  /** Navigate from Overview to Generation tab */
  const handleNavigateToGeneration = useCallback(
    (_atomId?: string) => { setActiveTab("generation"); }, [],
  );

  /** Open batch enrichment modal with chosen mode */
  const handleBatchEnrich = useCallback((mode: string) => {
    setBatchEnrichMode(mode);
    setShowBatchEnrich(true);
  }, []);

  /** Open batch generation modal with chosen options */
  const handleBatchGenerate = useCallback((opts: BatchGenOptions) => {
    setBatchGenOptions(opts);
    setShowBatchGen(true);
  }, []);

  const handleBatchGenSuccess = useCallback(() => {
    setShowBatchGen(false);
    fetchData();
  }, [fetchData]);

  const atomsWithQuestions = atoms.filter(
    (a) => a.generated_question_count > 0,
  ).length;

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-error">Error: {error}</div>
      </div>
    );
  }

  const selectedAtom = atoms.find((a) => a.id === selectedAtomId);
  const phaseLabel =
    selectedPhase === "all"
      ? PIPELINE_INFO.name
      : `${PIPELINE_INFO.name} — ${selectedPhase}`;
  const modalParamLabels = selectedAtom
    ? { atom_id: `${selectedAtom.id} — ${selectedAtom.titulo}` }
    : undefined;

  return (
    <div className="space-y-0">
      {/* Header */}
      <div className="px-0 py-6 space-y-6">
        <div className="flex items-center gap-4">
          <Link
            href={`/courses/${courseId}`}
            className="p-2 hover:bg-white/5 rounded-lg transition-colors"
          >
            <ArrowLeft className="w-5 h-5 text-text-secondary" />
          </Link>
          <div>
            <h1 className="text-2xl font-semibold">
              Question Generation
            </h1>
            <p className="text-text-secondary mt-1">
              Generate PAES-style question pools per atom &middot;{" "}
              <span className="font-medium">
                {atomsWithQuestions}/{atoms.length}
              </span>{" "}
              atoms generated
            </p>
          </div>
        </div>
      </div>

      {/* Tab navigation */}
      <QuestionGenTabs
        activeTab={activeTab}
        onTabChange={setActiveTab}
        atomCount={atoms.length}
        atomsWithQuestions={atomsWithQuestions}
      />

      {/* Tab content */}
      <div className="py-6">
        {activeTab === "overview" && (
          <OverviewTab
            atoms={atoms}
            loading={loading}
            onNavigateToGeneration={handleNavigateToGeneration}
          />
        )}

        {activeTab === "generation" && (
          <GenerationTab
            atoms={atoms}
            onRunPhase={handleRunPhase}
            onBatchEnrich={handleBatchEnrich}
            onBatchGenerate={handleBatchGenerate}
          />
        )}

        {activeTab === "results" && (
          <ResultsTab
            courseId={courseId}
            atoms={atoms}
            onRegenerate={(atomId) =>
              handleRunPhase(atomId, "all")
            }
          />
        )}

        {activeTab === "sync" && (
          <GenQuestionSyncTab
            subjectId={courseId}
            atoms={atoms}
          />
        )}
      </div>

      {/* Generation Modal */}
      {showGeneration && (
        <GeneratePipelineModal
          isOpen={showGeneration}
          onClose={() => setShowGeneration(false)}
          onSuccess={handlePipelineSuccess}
          pipelineId={PIPELINE_INFO.id}
          pipelineName={phaseLabel}
          pipelineDescription={PIPELINE_INFO.description}
          params={{
            atom_id: selectedAtomId,
            phase: selectedPhase,
          }}
          paramLabels={modalParamLabels}
        />
      )}

      {/* Batch Generation Modal */}
      {showBatchGen && (
        <GeneratePipelineModal
          isOpen={showBatchGen}
          onClose={() => setShowBatchGen(false)}
          onSuccess={handleBatchGenSuccess}
          pipelineId="batch_question_gen"
          pipelineName="Batch Question Generation"
          pipelineDescription={
            `Generate questions for all covered atoms`
            + ` (${batchGenOptions.mode.replace("_", " ")},`
            + ` images ${batchGenOptions.skip_images === "true" ? "off" : "on"})`
          }
          params={batchGenOptions}
          paramLabels={{
            mode: batchGenOptions.mode === "pending_only"
              ? "Pending only" : "All atoms (re-run)",
            skip_images: batchGenOptions.skip_images === "true"
              ? "Yes — skip images" : "No — generate images",
          }}
        />
      )}

      {/* Batch Enrichment Modal */}
      <BatchEnrichModal
        open={showBatchEnrich}
        onOpenChange={setShowBatchEnrich}
        subjectId={courseId}
        mode={batchEnrichMode}
        onSuccess={fetchData}
      />
    </div>
  );
}
