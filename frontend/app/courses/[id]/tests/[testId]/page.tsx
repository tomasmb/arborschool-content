"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { getTestDetail, type TestDetail } from "@/lib/api";
import { QuestionDetailPanel } from "@/components/questions";
import { LoadingPage } from "@/components/ui/LoadingSpinner";
import { ErrorPage } from "@/components/ui/ErrorMessage";
import { GeneratePipelineModal } from "@/components/pipelines/GeneratePipelineModal";
import { VariantOptionsDialog } from "@/components/pipelines/VariantOptionsDialog";
import { EnrichmentModal } from "@/components/pipelines/EnrichmentModal";
import { ValidationModal } from "@/components/pipelines/ValidationModal";
import { TestSyncModal } from "@/components/pipelines/TestSyncModal";
import {
  TestTabs,
  SplittingTab,
  ParsingTab,
  QuestionsTab,
  VariantsTab,
  SyncTab,
  type TestTab,
} from "./components";

type PipelineAction = "pdf_split" | "pdf_to_qti" | "tagging" | "variant_gen" | null;

const PIPELINE_INFO = {
  pdf_split: {
    id: "pdf_split",
    name: "Split PDF",
    description: "Split the test PDF into individual question PDFs",
  },
  pdf_to_qti: {
    id: "pdf_to_qti",
    name: "Parse to QTI",
    description: "Convert question PDFs to QTI XML format",
  },
  tagging: {
    id: "tagging",
    name: "Tag Questions",
    description: "Tag questions with relevant atoms",
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
  const [activeTab, setActiveTab] = useState<TestTab>("splitting");
  const [selectedQuestion, setSelectedQuestion] = useState<number | null>(null);
  const [activePipeline, setActivePipeline] = useState<PipelineAction>(null);
  const [showVariantOptions, setShowVariantOptions] = useState(false);
  const [variantsPerQuestion, setVariantsPerQuestion] = useState(3);
  const [showEnrichmentModal, setShowEnrichmentModal] = useState(false);
  const [showValidationModal, setShowValidationModal] = useState(false);
  const [showVariantEnrichmentModal, setShowVariantEnrichmentModal] = useState(false);
  const [showVariantValidationModal, setShowVariantValidationModal] = useState(false);
  const [showSyncModal, setShowSyncModal] = useState(false);
  const [pipelineParams, setPipelineParams] = useState<Record<string, string>>({});

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

  const handlePipelineAction = (
    action: PipelineAction,
    params?: Record<string, string>
  ) => {
    if (action === "variant_gen") {
      setShowVariantOptions(true);
    } else {
      setPipelineParams(params ?? {});
      setActivePipeline(action);
    }
  };

  const handleVariantOptionsConfirm = (count: number) => {
    setVariantsPerQuestion(count);
    setShowVariantOptions(false);
    setActivePipeline("variant_gen");
  };

  const handlePipelineSuccess = () => {
    fetchData();
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

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="px-6 py-4 border-b border-border flex items-center justify-between shrink-0">
        <div className="flex items-center gap-4">
          {/* Back to course link - prominent */}
          <Link
            href={`/courses/${courseId}`}
            className="flex items-center gap-2 px-3 py-1.5 text-sm text-text-secondary
              hover:text-text-primary hover:bg-white/5 rounded-lg transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            <span className="hidden sm:inline">Course</span>
          </Link>
          <div className="border-l border-border pl-4">
            <h1 className="text-xl font-semibold">{data.name}</h1>
            {data.application_type && (
              <p className="text-text-secondary text-sm capitalize">
                {data.application_type} {data.admission_year}
              </p>
            )}
          </div>
        </div>

        {/* Pipeline status summary - compact on mobile */}
        <div className="hidden md:flex items-center gap-4 text-sm">
          <div className="flex items-center gap-2">
            <span className="text-text-secondary">Split:</span>
            <span className="font-mono">{data.split_count}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-text-secondary">QTI:</span>
            <span className="font-mono">{data.qti_count}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-text-secondary">Enriched:</span>
            <span className="font-mono">{data.enriched_count}/{data.finalized_count}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-text-secondary">Validated:</span>
            <span className="font-mono">{data.validated_count}/{data.finalized_count}</span>
          </div>
        </div>
        {/* Mobile: show completion percentage */}
        <div className="flex md:hidden items-center gap-2 text-sm">
          <span className="text-text-secondary">Progress:</span>
          <span className="font-mono text-accent">
            {data.finalized_count > 0
              ? Math.round((data.validated_count / data.finalized_count) * 100)
              : 0}%
          </span>
        </div>
      </div>

      {/* Tabs */}
      <TestTabs
        activeTab={activeTab}
        onTabChange={setActiveTab}
        hasPdf={data.raw_pdf_exists}
        counts={{
          split: data.split_count,
          qti: data.qti_count,
          questions: data.finalized_count,
          enriched: data.enriched_count,
          validated: data.validated_count,
          variants: data.variants_count,
        }}
      />

      {/* Tab content */}
      <div className="flex-1 overflow-auto">
        {activeTab === "splitting" && (
          <SplittingTab
            subjectId={courseId}
            testId={testId}
            rawPdfExists={data.raw_pdf_exists}
            questions={data.questions}
            onRunSplit={() => handlePipelineAction("pdf_split")}
            onReRunSplit={() => handlePipelineAction("pdf_split")}
            onPdfUploaded={fetchData}
          />
        )}

        {activeTab === "parsing" && (
          <ParsingTab
            subjectId={courseId}
            testId={testId}
            questions={data.questions}
            onRunParsing={() => handlePipelineAction("pdf_to_qti")}
            onReparse={(questionNums) => {
              // Pass specific question IDs to re-parse only those
              const questionIds = questionNums.map((n) => `Q${n}`).join(",");
              handlePipelineAction("pdf_to_qti", { question_ids: questionIds });
            }}
          />
        )}

        {activeTab === "questions" && (
          <QuestionsTab
            subjectId={courseId}
            testId={testId}
            questions={data.questions}
            data={data}
            onOpenEnrichment={() => setShowEnrichmentModal(true)}
            onOpenValidation={() => setShowValidationModal(true)}
            onRunTagging={() => handlePipelineAction("tagging")}
            onSelectQuestion={setSelectedQuestion}
          />
        )}

        {activeTab === "variants" && (
          <VariantsTab
            subjectId={courseId}
            testId={testId}
            questions={data.questions}
            data={data}
            onGenerateVariants={() => handlePipelineAction("variant_gen")}
            onEnrichVariants={() => setShowVariantEnrichmentModal(true)}
            onValidateVariants={() => setShowVariantValidationModal(true)}
            onDeleteVariants={(questionNum) => {
              // TODO: Implement when variant delete API is available
              console.log(`Delete variants for Q${questionNum}`);
            }}
          />
        )}

        {activeTab === "sync" && (
          <SyncTab
            subjectId={courseId}
            testId={testId}
            questions={data.questions}
            data={data}
            onSync={() => setShowSyncModal(true)}
            onViewDiff={() => {
              // TODO: Implement diff viewer modal
              console.log("View diff");
            }}
          />
        )}
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
          onClose={() => {
            setActivePipeline(null);
            setPipelineParams({});
          }}
          onSuccess={handlePipelineSuccess}
          pipelineId={PIPELINE_INFO[activePipeline].id}
          pipelineName={PIPELINE_INFO[activePipeline].name}
          pipelineDescription={PIPELINE_INFO[activePipeline].description}
          params={
            activePipeline === "variant_gen"
              ? { test_id: testId, variants_per_question: variantsPerQuestion }
              : { test_id: testId, ...pipelineParams }
          }
        />
      )}

      {/* Enrichment Modal */}
      <EnrichmentModal
        open={showEnrichmentModal}
        onOpenChange={setShowEnrichmentModal}
        testId={testId}
        subjectId={courseId}
        stats={{
          tagged_count: data.tagged_count,
          enriched_count: data.enriched_count,
          failed_validation_count: data.enriched_count - data.validated_count,
        }}
        onSuccess={fetchData}
      />

      {/* Validation Modal */}
      <ValidationModal
        open={showValidationModal}
        onOpenChange={setShowValidationModal}
        testId={testId}
        subjectId={courseId}
        stats={{
          enriched_count: data.enriched_count,
          validated_count: data.validated_count,
        }}
        onSuccess={fetchData}
      />

      {/* Variant Enrichment Modal (DRY - reuses same modal with target="variants") */}
      <EnrichmentModal
        open={showVariantEnrichmentModal}
        onOpenChange={setShowVariantEnrichmentModal}
        testId={testId}
        subjectId={courseId}
        target="variants"
        stats={{
          // Variants stats - using variants_count as proxy
          // Ideally would have enriched_variants_count from API
          tagged_count: data.variants_count,
          enriched_count: 0, // Would need API to track this
        }}
        onSuccess={fetchData}
      />

      {/* Variant Validation Modal (DRY - reuses same modal with target="variants") */}
      <ValidationModal
        open={showVariantValidationModal}
        onOpenChange={setShowVariantValidationModal}
        testId={testId}
        subjectId={courseId}
        target="variants"
        stats={{
          // Variants stats - would need API to track enriched/validated variants
          enriched_count: data.variants_count,
          validated_count: 0, // Would need API to track this
        }}
        onSuccess={fetchData}
      />

      {/* Test Sync Modal */}
      <TestSyncModal
        open={showSyncModal}
        onOpenChange={setShowSyncModal}
        testId={testId}
        subjectId={courseId}
        stats={{
          validated_count: data.validated_count,
          total: data.questions.length,
        }}
        onSuccess={fetchData}
      />
    </div>
  );
}
