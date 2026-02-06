"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { getSubject, type SubjectDetail } from "@/lib/api";
import { GeneratePipelineModal } from "@/components/pipelines";
import { useToast } from "@/components/ui";
import { KnowledgeGraphModal } from "@/components/knowledge-graph";
import { CourseProgressDashboard } from "@/components/dashboard";
import { RegenerateDialog } from "./components";

type GenerateModalType = "standards" | "atoms" | null;
type RegenerateModalType = "standards" | "atoms" | null;

export default function CoursePage() {
  const params = useParams();
  const courseId = params.id as string;
  const { showToast } = useToast();

  const [data, setData] = useState<SubjectDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [showGraph, setShowGraph] = useState(false);
  const [generateModal, setGenerateModal] = useState<GenerateModalType>(null);
  const [regenerateModal, setRegenerateModal] = useState<RegenerateModalType>(null);

  const fetchData = useCallback(async () => {
    if (!courseId) return;
    setLoading(true);
    try {
      const subjectData = await getSubject(courseId);
      setData(subjectData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load course");
    } finally {
      setLoading(false);
    }
  }, [courseId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleGenerateSuccess = useCallback(() => {
    const type = generateModal;
    setGenerateModal(null);
    showToast(
      "success",
      type === "standards"
        ? "Standards generated successfully!"
        : "Atoms generated successfully!"
    );
    // Refresh data to show new items
    fetchData();
  }, [generateModal, showToast, fetchData]);

  const handleGenerateClose = useCallback(() => {
    setGenerateModal(null);
  }, []);

  const handleRegenerateConfirm = useCallback(() => {
    // After clearing, open the generate modal
    const type = regenerateModal;
    setRegenerateModal(null);
    if (type) {
      setGenerateModal(type);
    }
  }, [regenerateModal]);

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

  return (
    <div className="space-y-8">
      {/* Course Progress Dashboard */}
      <CourseProgressDashboard
        data={data}
        courseId={courseId}
        onViewGraph={() => setShowGraph(true)}
        onGenerateStandards={() => setGenerateModal("standards")}
        onGenerateAtoms={() => setGenerateModal("atoms")}
      />

      {/* Knowledge Graph Modal */}
      <KnowledgeGraphModal
        subjectId={courseId}
        isOpen={showGraph}
        onClose={() => setShowGraph(false)}
      />

      {/* Generate Standards Modal */}
      <GeneratePipelineModal
        isOpen={generateModal === "standards"}
        onClose={handleGenerateClose}
        onSuccess={handleGenerateSuccess}
        pipelineId="standards_gen"
        pipelineName="Generate Standards"
        pipelineDescription="Generate learning standards from the temario"
        params={{
          temario_file: data?.temario_file || "",
        }}
      />

      {/* Generate Atoms Modal */}
      <GeneratePipelineModal
        isOpen={generateModal === "atoms"}
        onClose={handleGenerateClose}
        onSuccess={handleGenerateSuccess}
        pipelineId="atoms_gen"
        pipelineName="Generate Atoms"
        pipelineDescription="Generate learning atoms from standards"
        params={{
          standards_file: "paes_m1_2026.json",
        }}
      />

      {/* Regenerate Standards Dialog */}
      <RegenerateDialog
        isOpen={regenerateModal === "standards"}
        onClose={() => setRegenerateModal(null)}
        onConfirm={handleRegenerateConfirm}
        pipelineId="standards_gen"
        pipelineName="Standards"
        itemCount={data?.standards.length || 0}
        itemLabel="standards"
      />

      {/* Regenerate Atoms Dialog */}
      <RegenerateDialog
        isOpen={regenerateModal === "atoms"}
        onClose={() => setRegenerateModal(null)}
        onConfirm={handleRegenerateConfirm}
        pipelineId="atoms_gen"
        pipelineName="Atoms"
        itemCount={data?.atoms_count || 0}
        itemLabel="learning atoms"
      />
    </div>
  );
}
