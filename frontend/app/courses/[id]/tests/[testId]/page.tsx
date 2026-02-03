"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  ArrowLeft,
  CheckCircle2,
  Circle,
  XCircle,
  MoreVertical,
  RefreshCw,
  Sparkles,
  Tag,
} from "lucide-react";
import { getTestDetail, type TestDetail } from "@/lib/api";
import { QuestionDetailPanel } from "@/components/questions";
import { LoadingPage } from "@/components/ui/LoadingSpinner";
import { ErrorPage } from "@/components/ui/ErrorMessage";
import { GeneratePipelineModal } from "@/components/pipelines/GeneratePipelineModal";
import { VariantOptionsDialog } from "@/components/pipelines/VariantOptionsDialog";

type PipelineAction = "pdf_to_qti" | "tagging" | "variant_gen" | null;

const PIPELINE_INFO = {
  pdf_to_qti: {
    id: "pdf_to_qti",
    name: "Regenerate QTI",
    description: "Re-convert question PDFs to QTI XML format",
  },
  tagging: {
    id: "tagging",
    name: "Regenerate Tags",
    description: "Re-tag questions with relevant atoms",
  },
  variant_gen: {
    id: "variant_gen",
    name: "Generate Variants",
    description: "Add new alternative versions of questions",
  },
};

export default function TestDetailPage() {
  const params = useParams();
  const courseId = params.id as string;
  const testId = params.testId as string;

  const [data, setData] = useState<TestDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedQuestion, setSelectedQuestion] = useState<number | null>(null);
  const [showActionsMenu, setShowActionsMenu] = useState(false);
  const [activePipeline, setActivePipeline] = useState<PipelineAction>(null);
  const [showVariantOptions, setShowVariantOptions] = useState(false);
  const [variantsPerQuestion, setVariantsPerQuestion] = useState(3);
  const actionsMenuRef = useRef<HTMLDivElement>(null);

  const fetchData = useCallback(async () => {
    if (!courseId || !testId) return;
    setLoading(true);
    setError(null);
    try {
      const result = await getTestDetail(courseId, testId);
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load test");
    } finally {
      setLoading(false);
    }
  }, [courseId, testId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Close actions menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        actionsMenuRef.current &&
        !actionsMenuRef.current.contains(event.target as Node)
      ) {
        setShowActionsMenu(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handlePipelineAction = (action: PipelineAction) => {
    setShowActionsMenu(false);
    if (action === "variant_gen") {
      // Show variant options dialog first
      setShowVariantOptions(true);
    } else {
      setActivePipeline(action);
    }
  };

  const handleVariantOptionsConfirm = (count: number) => {
    setVariantsPerQuestion(count);
    setShowVariantOptions(false);
    setActivePipeline("variant_gen");
  };

  const handlePipelineSuccess = () => {
    fetchData(); // Refresh the test data
  };

  if (loading) {
    return <LoadingPage text="Loading test details..." />;
  }

  if (error) {
    return (
      <ErrorPage
        title="Failed to load test"
        message={error}
        onRetry={fetchData}
      />
    );
  }

  if (!data) return null;

  const StatusCell = ({ done }: { done: boolean }) =>
    done ? (
      <CheckCircle2 className="w-4 h-4 text-success mx-auto" />
    ) : (
      <Circle className="w-4 h-4 text-text-secondary mx-auto" />
    );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            href={`/courses/${courseId}`}
            className="p-2 hover:bg-white/5 rounded-lg transition-colors"
          >
            <ArrowLeft className="w-5 h-5 text-text-secondary" />
          </Link>
          <div>
            <h1 className="text-2xl font-semibold">{data.name}</h1>
            {data.application_type && (
              <p className="text-text-secondary mt-1 capitalize">
                {data.application_type} {data.admission_year}
              </p>
            )}
          </div>
        </div>

        {/* Actions Menu */}
        <div className="relative" ref={actionsMenuRef}>
          <button
            onClick={() => setShowActionsMenu(!showActionsMenu)}
            className="flex items-center gap-2 px-4 py-2 bg-surface border border-border rounded-lg hover:bg-white/5 transition-colors"
          >
            <MoreVertical className="w-4 h-4" />
            <span className="text-sm font-medium">Actions</span>
          </button>

          {showActionsMenu && (
            <div className="absolute right-0 top-full mt-2 w-56 bg-surface border border-border rounded-lg shadow-xl z-10 overflow-hidden">
              <button
                onClick={() => handlePipelineAction("pdf_to_qti")}
                disabled={data.split_count === 0}
                className="w-full flex items-center gap-3 px-4 py-3 text-left
                  hover:bg-white/5 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <RefreshCw className="w-4 h-4 text-accent" />
                <div>
                  <p className="text-sm font-medium">Regenerate QTI</p>
                  <p className="text-xs text-text-secondary">Re-convert PDFs to QTI</p>
                </div>
              </button>
              <button
                onClick={() => handlePipelineAction("tagging")}
                disabled={data.finalized_count === 0}
                className="w-full flex items-center gap-3 px-4 py-3 text-left border-t border-border
                  hover:bg-white/5 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Tag className="w-4 h-4 text-purple-400" />
                <div>
                  <p className="text-sm font-medium">Regenerate Tags</p>
                  <p className="text-xs text-text-secondary">Re-tag questions with atoms</p>
                </div>
              </button>
              <button
                onClick={() => handlePipelineAction("variant_gen")}
                disabled={data.tagged_count === 0}
                className="w-full flex items-center gap-3 px-4 py-3 text-left border-t border-border
                  hover:bg-white/5 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Sparkles className="w-4 h-4 text-yellow-400" />
                <div>
                  <p className="text-sm font-medium">Generate Variants</p>
                  <p className="text-xs text-text-secondary">Create question alternatives</p>
                </div>
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Pipeline Status */}
      <div className="flex flex-wrap gap-2 md:gap-4">
        {[
          { label: "Raw PDF", value: data.raw_pdf_exists, type: "boolean" },
          { label: "Split", value: `${data.split_count}`, type: "number" },
          { label: "QTI", value: `${data.qti_count}`, type: "number" },
          { label: "Finalized", value: `${data.finalized_count}`, type: "number" },
          {
            label: "Tagged",
            value: `${data.tagged_count}/${data.finalized_count}`,
            type: "fraction",
          },
          { label: "Variants", value: `${data.variants_count}`, type: "number" },
        ].map((item, idx) => (
          <div
            key={item.label}
            className="flex items-center gap-3 bg-surface border border-border rounded-lg px-4 py-2"
          >
            {idx > 0 && <span className="text-text-secondary">→</span>}
            <div className="text-center">
              <p className="text-xs text-text-secondary">{item.label}</p>
              {item.type === "boolean" ? (
                item.value ? (
                  <CheckCircle2 className="w-5 h-5 text-success mx-auto mt-1" />
                ) : (
                  <XCircle className="w-5 h-5 text-error mx-auto mt-1" />
                )
              ) : (
                <p className="font-semibold">{item.value}</p>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Questions Table */}
      <div className="bg-surface border border-border rounded-lg overflow-x-auto">
        <table className="w-full min-w-[640px]">
          <thead>
            <tr className="border-b border-border text-left text-xs text-text-secondary uppercase tracking-wide">
              <th className="px-4 py-3 font-medium">Q#</th>
              <th className="px-4 py-3 font-medium text-center">Split</th>
              <th className="px-4 py-3 font-medium text-center">QTI</th>
              <th className="px-4 py-3 font-medium text-center">Final</th>
              <th className="px-4 py-3 font-medium text-center">Tagged</th>
              <th className="px-4 py-3 font-medium text-center">Atoms</th>
              <th className="px-4 py-3 font-medium text-center">Variants</th>
            </tr>
          </thead>
          <tbody>
            {data.questions.map((q) => (
              <tr
                key={q.id}
                onClick={() => setSelectedQuestion(q.question_number)}
                className="border-b border-border last:border-b-0 hover:bg-white/5 transition-colors cursor-pointer"
              >
                <td className="px-4 py-3 font-mono text-sm">
                  Q{q.question_number}
                </td>
                <td className="px-4 py-3">
                  <StatusCell done={q.has_split_pdf} />
                </td>
                <td className="px-4 py-3">
                  <StatusCell done={q.has_qti} />
                </td>
                <td className="px-4 py-3">
                  <StatusCell done={q.is_finalized} />
                </td>
                <td className="px-4 py-3">
                  <StatusCell done={q.is_tagged} />
                </td>
                <td className="px-4 py-3 text-center text-sm">
                  {q.atoms_count > 0 ? (
                    <span className="text-accent">{q.atoms_count}</span>
                  ) : (
                    <span className="text-text-secondary">-</span>
                  )}
                </td>
                <td className="px-4 py-3 text-center text-sm">
                  {q.variants_count > 0 ? (
                    <span className="text-accent">{q.variants_count}</span>
                  ) : (
                    <span className="text-text-secondary">-</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Question Detail Panel */}
      {selectedQuestion !== null && (
        <QuestionDetailPanel
          subjectId={courseId}
          testId={testId}
          questionNumber={selectedQuestion}
          onClose={() => setSelectedQuestion(null)}
        />
      )}

      {/* Variant Options Dialog */}
      <VariantOptionsDialog
        isOpen={showVariantOptions}
        onClose={() => setShowVariantOptions(false)}
        onConfirm={handleVariantOptionsConfirm}
        existingCount={data.variants_count}
      />

      {/* Pipeline Modal */}
      {activePipeline && (
        <GeneratePipelineModal
          isOpen={activePipeline !== null}
          onClose={() => setActivePipeline(null)}
          onSuccess={handlePipelineSuccess}
          pipelineId={PIPELINE_INFO[activePipeline].id}
          pipelineName={PIPELINE_INFO[activePipeline].name}
          pipelineDescription={PIPELINE_INFO[activePipeline].description}
          params={
            activePipeline === "variant_gen"
              ? { test_id: testId, variants_per_question: variantsPerQuestion }
              : { test_id: testId }
          }
        />
      )}
    </div>
  );
}
