"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import {
  getAtomPipelineSummary,
  type AtomPipelineSummary,
} from "@/lib/api";
import { GeneratePipelineModal } from "@/components/pipelines/GeneratePipelineModal";
import { AtomValidationModal } from "@/components/pipelines/AtomValidationModal";
import {
  AtomTabs,
  type AtomTab,
} from "./components/AtomTabs";
import { GenerationTab } from "./components/GenerationTab";
import { ValidationTab } from "./components/ValidationTab";
import { CoverageTab } from "./components/CoverageTab";
import { GraphTab } from "./components/GraphTab";
import { AtomSyncTab } from "./components/AtomSyncTab";

// Pipeline info for GeneratePipelineModal reuse
const ATOMS_PIPELINE_INFO = {
  id: "atoms_gen",
  name: "Atom Generation",
  description:
    "Generate learning atoms from standards using Gemini",
};

export default function AtomsPage() {
  const params = useParams();
  const courseId = params.id as string;

  // State
  const [summary, setSummary] =
    useState<AtomPipelineSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] =
    useState<AtomTab>("generation");

  // Modal state (owned by orchestrator)
  const [showGeneration, setShowGeneration] = useState(false);
  const [showValidation, setShowValidation] = useState(false);

  // Fetch pipeline summary
  const fetchData = useCallback(async () => {
    try {
      const data = await getAtomPipelineSummary(courseId);
      setSummary(data);
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
    fetchData();
  }, [fetchData]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-text-secondary">Loading...</div>
      </div>
    );
  }

  if (error || !summary) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-error">
          Error: {error || "No data"}
        </div>
      </div>
    );
  }

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
              Atoms Pipeline
            </h1>
            <p className="text-text-secondary mt-1">
              Generate, validate, and analyze learning atoms
            </p>
          </div>
        </div>
      </div>

      {/* Tab navigation */}
      <AtomTabs
        activeTab={activeTab}
        onTabChange={setActiveTab}
        summary={summary}
      />

      {/* Tab content */}
      <div className="py-6">
        {activeTab === "generation" && (
          <GenerationTab
            subjectId={courseId}
            summary={summary}
            onRunGeneration={() => setShowGeneration(true)}
          />
        )}

        {activeTab === "validation" && (
          <ValidationTab
            subjectId={courseId}
            summary={summary}
            onOpenValidation={() => setShowValidation(true)}
            onRefresh={fetchData}
          />
        )}

        {activeTab === "coverage" && (
          <CoverageTab subjectId={courseId} />
        )}

        {activeTab === "graph" && (
          <GraphTab subjectId={courseId} />
        )}

        {activeTab === "sync" && (
          <AtomSyncTab
            subjectId={courseId}
            summary={summary}
          />
        )}
      </div>

      {/* Generation Modal (reuses existing GeneratePipelineModal) */}
      {showGeneration && (
        <GeneratePipelineModal
          isOpen={showGeneration}
          onClose={() => setShowGeneration(false)}
          onSuccess={handlePipelineSuccess}
          pipelineId={ATOMS_PIPELINE_INFO.id}
          pipelineName={ATOMS_PIPELINE_INFO.name}
          pipelineDescription={ATOMS_PIPELINE_INFO.description}
          params={{ standards_file: "paes_m1_2026.json" }}
        />
      )}

      {/* Validation Modal */}
      <AtomValidationModal
        open={showValidation}
        onOpenChange={setShowValidation}
        subjectId={courseId}
        stats={{
          standards_count: summary.standards_count,
          standards_validated: summary.standards_validated,
        }}
        onSuccess={handlePipelineSuccess}
      />
    </div>
  );
}
