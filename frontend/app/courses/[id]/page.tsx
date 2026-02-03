"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  CheckCircle2,
  Circle,
  Network,
  ChevronRight,
  RefreshCw,
  AlertTriangle,
} from "lucide-react";
import {
  getSubject,
  getSyncStatus,
  getTemarioPdfUrl,
  getTestRawPdfUrl,
  type SubjectDetail,
  type SyncStatus,
} from "@/lib/api";
import { GeneratePipelineModal } from "@/components/pipelines";
import { useToast } from "@/components/ui";

// Calculate totals from subject data
function calculateTotals(data: SubjectDetail) {
  let totalQuestions = 0;
  let totalVariants = 0;
  for (const test of data.tests) {
    totalQuestions += test.finalized_count;
    totalVariants += test.variants_count;
  }
  return { totalQuestions, totalVariants };
}
import { cn, getEjeColor, getEjeBgColor } from "@/lib/utils";
import { KnowledgeGraphModal } from "@/components/knowledge-graph";
import { PipelineCard, SyncItem, RegenerateDialog } from "./components";

type GenerateModalType = "standards" | "atoms" | null;
type RegenerateModalType = "standards" | "atoms" | null;

export default function CoursePage() {
  const params = useParams();
  const courseId = params.id as string;
  const { showToast } = useToast();

  const [data, setData] = useState<SubjectDetail | null>(null);
  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [showGraph, setShowGraph] = useState(false);
  const [generateModal, setGenerateModal] = useState<GenerateModalType>(null);
  const [regenerateModal, setRegenerateModal] = useState<RegenerateModalType>(null);

  const fetchData = useCallback(async () => {
    if (!courseId) return;
    setLoading(true);
    try {
      const [subjectData, sync] = await Promise.all([
        getSubject(courseId),
        getSyncStatus().catch(() => null),
      ]);
      setData(subjectData);
      setSyncStatus(sync);
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

  // Pipeline status helpers
  const hasTemario = data.temario_exists;
  const hasStandards = data.standards.length > 0;
  const hasAtoms = data.atoms_count > 0;

  const canGenerateStandards = hasTemario && !hasStandards;
  const canGenerateAtoms = hasStandards && !hasAtoms;

  // Calculate totals for sync display
  const { totalQuestions, totalVariants } = calculateTotals(data);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold">{data.full_name}</h1>
          <p className="text-text-secondary mt-1">{data.year}</p>
        </div>
        <button
          onClick={() => setShowGraph(true)}
          className="flex items-center gap-2 px-4 py-2 bg-accent/10 text-accent rounded-lg text-sm font-medium hover:bg-accent/20 transition-colors"
        >
          <Network className="w-4 h-4" />
          Knowledge Graph
        </button>
      </div>

      {/* Knowledge Graph Pipeline */}
      <section>
        <h2 className="text-lg font-semibold mb-4 text-text-secondary uppercase tracking-wide text-xs">
          Knowledge Graph Pipeline
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Temario */}
          <PipelineCard
            step={1}
            title="Temario"
            done={hasTemario}
            description={hasTemario ? "Parsed from DEMRE PDF" : "Not yet parsed"}
            detail={data.temario_file}
            pdfUrl={hasTemario ? getTemarioPdfUrl(courseId) : undefined}
          />

          {/* Standards */}
          <PipelineCard
            step={2}
            title="Standards"
            done={hasStandards}
            description={
              hasStandards
                ? `${data.standards.length} standards defined`
                : "Not yet generated"
            }
            canGenerate={canGenerateStandards}
            canRegenerate={hasStandards && hasTemario}
            isBlocked={!hasTemario}
            blockedReason="Requires Temario"
            onGenerate={() => setGenerateModal("standards")}
            onRegenerate={() => setRegenerateModal("standards")}
          >
            {hasStandards && (
              <div className="flex flex-wrap gap-1 mt-3">
                {["numeros", "algebra_y_funciones", "geometria", "probabilidad_y_estadistica"].map(
                  (eje) => {
                    const count = data.standards.filter((s) => s.eje === eje).length;
                    if (count === 0) return null;
                    return (
                      <span
                        key={eje}
                        className={cn(
                          "text-xs px-2 py-0.5 rounded",
                          getEjeBgColor(eje),
                          getEjeColor(eje)
                        )}
                      >
                        {count}
                      </span>
                    );
                  }
                )}
              </div>
            )}
          </PipelineCard>

          {/* Atoms */}
          <PipelineCard
            step={3}
            title="Atoms"
            done={hasAtoms}
            description={
              hasAtoms
                ? `${data.atoms_count} learning atoms`
                : "Not yet generated"
            }
            canGenerate={canGenerateAtoms}
            canRegenerate={hasAtoms && hasStandards}
            isBlocked={!hasStandards}
            blockedReason="Requires Standards"
            onGenerate={() => setGenerateModal("atoms")}
            onRegenerate={() => setRegenerateModal("atoms")}
            linkHref={`/courses/${courseId}/atoms`}
            linkText="View atoms →"
          />
        </div>
      </section>

      {/* Sync Status */}
      <section>
        <h2 className="text-lg font-semibold mb-4 text-text-secondary uppercase tracking-wide text-xs">
          Sync Status
        </h2>

        <div className="bg-surface border border-border rounded-lg p-5">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-4">
            <SyncItem
              label="Standards"
              count={data.standards.length}
              status={data.standards.length > 0 ? "synced" : "empty"}
            />
            <SyncItem
              label="Atoms"
              count={data.atoms_count}
              status={data.atoms_count > 0 ? "synced" : "empty"}
            />
            <SyncItem
              label="Questions"
              count={totalQuestions}
              status={totalQuestions > 0 ? "synced" : "empty"}
            />
            <SyncItem
              label="Variants"
              count={totalVariants}
              status={totalVariants > 0 ? "synced" : "empty"}
            />
            <SyncItem
              label="Images"
              count={0}
              status={syncStatus?.s3_configured ? "synced" : "warning"}
              warning={!syncStatus?.s3_configured ? "S3 not configured" : undefined}
            />
          </div>

          <div className="flex items-center justify-between pt-4 border-t border-border">
            <div className="text-sm text-text-secondary">
              {syncStatus?.s3_configured ? (
                <span className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-success" />
                  S3 configured for images
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
              className={cn(
                "flex items-center gap-2 px-4 py-2 bg-accent/10 text-accent",
                "rounded-lg text-sm font-medium hover:bg-accent/20 transition-colors"
              )}
            >
              <RefreshCw className="w-4 h-4" />
              Sync Settings
            </Link>
          </div>
        </div>
      </section>

      {/* Tests & Questions */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-text-secondary uppercase tracking-wide text-xs">
            Tests & Questions
          </h2>
          <Link
            href={`/courses/${courseId}/tests`}
            className="text-accent text-sm hover:underline"
          >
            View all tests →
          </Link>
        </div>

        <div className="bg-surface border border-border rounded-lg overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border text-left text-xs text-text-secondary uppercase tracking-wide">
                <th className="px-4 py-3 font-medium">Test</th>
                <th className="px-4 py-3 font-medium text-center">Raw</th>
                <th className="px-4 py-3 font-medium text-center">Split</th>
                <th className="px-4 py-3 font-medium text-center">QTI</th>
                <th className="px-4 py-3 font-medium text-center">Tagged</th>
                <th className="px-4 py-3 font-medium text-center">Variants</th>
                <th className="px-4 py-3 font-medium"></th>
              </tr>
            </thead>
            <tbody>
              {data.tests.map((test) => (
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
                        test.tagged_count === test.finalized_count &&
                          test.tagged_count > 0
                          ? "text-success"
                          : "text-text-secondary"
                      )}
                    >
                      {test.tagged_count}/{test.finalized_count}
                    </span>
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
              ))}
            </tbody>
          </table>
        </div>
      </section>

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
