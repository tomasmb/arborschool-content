"use client";

import { useEffect, useState } from "react";
import {
  X,
  CheckCircle2,
  Circle,
  XCircle,
  Tag,
  FileText,
  Loader2,
  Copy,
  ExternalLink,
  ChevronDown,
  ChevronRight,
  FileImage,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import { getQuestionDetail, getQuestionPdfUrl, QuestionDetail } from "@/lib/api";
import { cn } from "@/lib/utils";
import { GeneratePipelineModal } from "@/components/pipelines/GeneratePipelineModal";
import { VariantOptionsDialog } from "@/components/pipelines/VariantOptionsDialog";

type PipelineAction = "pdf_to_qti" | "tagging" | "variant_gen" | null;

const PIPELINE_INFO = {
  pdf_to_qti: {
    id: "pdf_to_qti",
    name: "Regenerate QTI",
    description: "Re-convert this question's PDF to QTI XML format",
  },
  tagging: {
    id: "tagging",
    name: "Regenerate Tags",
    description: "Re-tag this question with relevant atoms",
  },
  variant_gen: {
    id: "variant_gen",
    name: "Generate Variants",
    description: "Add new alternative versions of this question",
  },
};

interface QuestionDetailPanelProps {
  subjectId: string;
  testId: string;
  questionNumber: number;
  onClose: () => void;
}

export function QuestionDetailPanel({
  subjectId,
  testId,
  questionNumber,
  onClose,
}: QuestionDetailPanelProps) {
  const [data, setData] = useState<QuestionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showRawXml, setShowRawXml] = useState(false);
  const [copiedXml, setCopiedXml] = useState(false);
  const [activePipeline, setActivePipeline] = useState<PipelineAction>(null);
  const [showVariantOptions, setShowVariantOptions] = useState(false);
  const [variantsPerQuestion, setVariantsPerQuestion] = useState(3);

  const fetchData = () => {
    setLoading(true);
    setError(null);

    getQuestionDetail(subjectId, testId, questionNumber)
      .then(setData)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchData();
  }, [subjectId, testId, questionNumber]);

  const handlePipelineSuccess = () => {
    fetchData(); // Refresh question data after pipeline completes
  };

  const handlePipelineAction = (action: PipelineAction) => {
    if (action === "variant_gen") {
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

  // Handle escape key
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleEsc);
    return () => window.removeEventListener("keydown", handleEsc);
  }, [onClose]);

  const copyXml = () => {
    if (data?.qti_xml) {
      navigator.clipboard.writeText(data.qti_xml);
      setCopiedXml(true);
      setTimeout(() => setCopiedXml(false), 2000);
    }
  };

  const StatusIcon = ({ done }: { done: boolean }) =>
    done ? (
      <CheckCircle2 className="w-4 h-4 text-success" />
    ) : (
      <Circle className="w-4 h-4 text-text-secondary" />
    );

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-40"
        onClick={onClose}
      />

      {/* Panel */}
      <div className="fixed right-0 top-0 h-full w-full max-w-2xl bg-background border-l border-border z-50 overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border bg-surface">
          <div>
            <h2 className="text-lg font-semibold">Question {questionNumber}</h2>
            <p className="text-sm text-text-secondary">{testId}</p>
          </div>
          <div className="flex items-center gap-2">
            {data?.has_split_pdf && (
              <a
                href={getQuestionPdfUrl(subjectId, testId, questionNumber)}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 px-3 py-2 bg-accent/10 hover:bg-accent/20
                  text-accent rounded-lg transition-colors text-sm font-medium"
              >
                <FileImage className="w-4 h-4" />
                View PDF
              </a>
            )}
            <button
              onClick={onClose}
              className="p-2 hover:bg-white/10 rounded-lg transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-6">
          {loading && (
            <div className="flex items-center justify-center h-48">
              <Loader2 className="w-6 h-6 animate-spin text-text-secondary" />
            </div>
          )}

          {error && (
            <div className="bg-error/10 border border-error/20 rounded-lg p-4 flex items-start gap-3">
              <XCircle className="w-5 h-5 text-error flex-shrink-0" />
              <div>
                <p className="font-medium text-error">Error loading question</p>
                <p className="text-sm text-text-secondary mt-1">{error}</p>
              </div>
            </div>
          )}

          {data && (
            <>
              {/* Pipeline Status */}
              <section>
                <h3 className="text-sm font-medium text-text-secondary mb-3">
                  Pipeline Status
                </h3>
                <div className="flex flex-wrap gap-4">
                  {[
                    { label: "Split PDF", done: data.has_split_pdf },
                    { label: "QTI", done: data.has_qti },
                    { label: "Finalized", done: data.is_finalized },
                    { label: "Tagged", done: data.is_tagged },
                  ].map((item) => (
                    <div key={item.label} className="flex items-center gap-2">
                      <StatusIcon done={item.done} />
                      <span className="text-sm">{item.label}</span>
                    </div>
                  ))}
                </div>
              </section>

              {/* Actions */}
              <section>
                <h3 className="text-sm font-medium text-text-secondary mb-3">
                  Actions
                </h3>
                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={() => handlePipelineAction("pdf_to_qti")}
                    disabled={!data.has_split_pdf}
                    className="flex items-center gap-2 px-3 py-2 bg-surface border border-border
                      rounded-lg hover:bg-white/5 transition-colors text-sm
                      disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <RefreshCw className="w-4 h-4 text-accent" />
                    Regenerate QTI
                  </button>
                  <button
                    onClick={() => handlePipelineAction("tagging")}
                    disabled={!data.is_finalized}
                    className="flex items-center gap-2 px-3 py-2 bg-surface border border-border
                      rounded-lg hover:bg-white/5 transition-colors text-sm
                      disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <Tag className="w-4 h-4 text-purple-400" />
                    Regenerate Tags
                  </button>
                  <button
                    onClick={() => handlePipelineAction("variant_gen")}
                    disabled={!data.is_tagged}
                    className="flex items-center gap-2 px-3 py-2 bg-surface border border-border
                      rounded-lg hover:bg-white/5 transition-colors text-sm
                      disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <Sparkles className="w-4 h-4 text-yellow-400" />
                    Generate Variants
                  </button>
                </div>
              </section>

              {/* Question Preview */}
              {data.qti_stem && (
                <section>
                  <h3 className="text-sm font-medium text-text-secondary mb-3">
                    Question Preview
                  </h3>
                  <div className="bg-surface border border-border rounded-lg p-4">
                    <p className="text-sm leading-relaxed whitespace-pre-wrap">
                      {data.qti_stem}
                    </p>

                    {data.qti_options && data.qti_options.length > 0 && (
                      <div className="mt-4 space-y-2">
                        {data.qti_options.map((opt) => (
                          <div
                            key={opt.id}
                            className="flex items-start gap-3 p-2 rounded bg-background"
                          >
                            <span className={
                              "flex-shrink-0 w-6 h-6 flex items-center justify-center " +
                              "rounded-full text-xs font-medium bg-surface border border-border"
                            }>
                              {opt.id}
                            </span>
                            <span className="text-sm">{opt.text}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </section>
              )}

              {/* Metadata */}
              {data.difficulty && (
                <section>
                  <h3 className="text-sm font-medium text-text-secondary mb-3">
                    Metadata
                  </h3>
                  <div className="bg-surface border border-border rounded-lg p-3">
                    <p className="text-xs text-text-secondary">Difficulty</p>
                    <p className="font-medium mt-1 capitalize">
                      {data.difficulty}
                    </p>
                  </div>
                </section>
              )}

              {/* Atom Tags */}
              <section>
                <h3 className="text-sm font-medium text-text-secondary mb-3 flex items-center gap-2">
                  <Tag className="w-4 h-4" />
                  Atom Tags ({data.atom_tags.length})
                </h3>
                {data.atom_tags.length > 0 ? (
                  <div className="space-y-2">
                    {data.atom_tags.map((tag) => (
                      <div
                        key={tag.atom_id}
                        className="bg-surface border border-border rounded-lg p-3"
                      >
                        <div className="flex items-start justify-between">
                          <div>
                            <p className="font-mono text-xs text-accent">
                              {tag.atom_id}
                            </p>
                            <p className="text-sm mt-1">{tag.titulo}</p>
                          </div>
                          <span
                            className={cn(
                              "text-xs px-2 py-0.5 rounded capitalize",
                              tag.eje === "numeros" && "bg-blue-500/10 text-blue-400",
                              tag.eje === "algebra_y_funciones" && "bg-purple-500/10 text-purple-400",
                              tag.eje === "geometria" && "bg-green-500/10 text-green-400",
                              tag.eje === "probabilidad_y_estadistica" && "bg-orange-500/10 text-orange-400"
                            )}
                          >
                            {tag.eje.replace(/_/g, " ")}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-text-secondary">
                    No atoms tagged yet
                  </p>
                )}
              </section>

              {/* Variants */}
              <section>
                <h3 className="text-sm font-medium text-text-secondary mb-3 flex items-center gap-2">
                  <FileText className="w-4 h-4" />
                  Variants ({data.variants.length})
                </h3>
                {data.variants.length > 0 ? (
                  <div className="space-y-2">
                    {data.variants.map((variant) => (
                      <div
                        key={variant.id}
                        className="bg-surface border border-border rounded-lg p-3 flex items-center justify-between"
                      >
                        <div>
                          <p className="font-mono text-sm">{variant.folder_name}</p>
                          <div className="flex items-center gap-3 mt-1">
                            <span className="flex items-center gap-1 text-xs text-text-secondary">
                              <StatusIcon done={variant.has_qti} />
                              QTI
                            </span>
                            <span className="flex items-center gap-1 text-xs text-text-secondary">
                              <StatusIcon done={variant.has_metadata} />
                              Metadata
                            </span>
                          </div>
                        </div>
                        <ExternalLink className="w-4 h-4 text-text-secondary" />
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-text-secondary">
                    No variants generated yet
                  </p>
                )}
              </section>

              {/* Raw QTI XML */}
              {data.qti_xml && (
                <section>
                  <button
                    onClick={() => setShowRawXml(!showRawXml)}
                    className="flex items-center gap-2 text-sm font-medium text-text-secondary hover:text-white transition-colors"
                  >
                    {showRawXml ? (
                      <ChevronDown className="w-4 h-4" />
                    ) : (
                      <ChevronRight className="w-4 h-4" />
                    )}
                    Raw QTI XML
                  </button>
                  {showRawXml && (
                    <div className="mt-2 relative">
                      <button
                        onClick={copyXml}
                        className="absolute top-2 right-2 p-1.5 bg-background hover:bg-white/10 rounded transition-colors"
                        title="Copy XML"
                      >
                        <Copy className="w-4 h-4" />
                      </button>
                      {copiedXml && (
                        <span className="absolute top-2 right-10 text-xs text-success">
                          Copied!
                        </span>
                      )}
                      <pre className="bg-surface border border-border rounded-lg p-4 text-xs overflow-x-auto max-h-96">
                        {data.qti_xml}
                      </pre>
                    </div>
                  )}
                </section>
              )}
            </>
          )}
        </div>

        {/* Variant Options Dialog */}
        <VariantOptionsDialog
          isOpen={showVariantOptions}
          onClose={() => setShowVariantOptions(false)}
          onConfirm={handleVariantOptionsConfirm}
          existingCount={data?.variants.length ?? 0}
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
                ? {
                    test_id: testId,
                    question_ids: `Q${questionNumber}`,
                    variants_per_question: variantsPerQuestion,
                  }
                : {
                    test_id: testId,
                    question_ids: `Q${questionNumber}`,
                  }
            }
          />
        )}
      </div>
    </>
  );
}
