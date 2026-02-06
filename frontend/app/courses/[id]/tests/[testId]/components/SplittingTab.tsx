"use client";

import { useState, useRef } from "react";
import {
  CheckCircle2,
  Circle,
  Eye,
  Play,
  RefreshCw,
  FileText,
  Upload,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { PDFViewerModal, PDFPreview } from "@/components/pdf";
import { StatusIcon, ActionButton } from "@/components/ui";
import { getTestRawPdfUrl, getQuestionPdfUrl, type QuestionBrief } from "@/lib/api";

export interface SplittingTabProps {
  subjectId: string;
  testId: string;
  rawPdfExists: boolean;
  questions: QuestionBrief[];
  onRunSplit?: () => void;
  onReRunSplit?: () => void;
  onPdfUploaded?: () => void;
}

export function SplittingTab({
  subjectId,
  testId,
  rawPdfExists,
  questions,
  onRunSplit,
  onReRunSplit,
  onPdfUploaded,
}: SplittingTabProps) {
  const [viewingPdf, setViewingPdf] = useState<{
    url: string;
    title: string;
    questionIndex?: number;
  } | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const splitQuestions = questions.filter((q) => q.has_split_pdf);
  const splitCount = splitQuestions.length;
  const isComplete = splitCount === questions.length && questions.length > 0;

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.name.endsWith(".pdf")) {
      setUploadError("Please select a PDF file");
      return;
    }

    setUploading(true);
    setUploadError(null);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(
        `/api/subjects/${subjectId}/tests/${testId}/upload-pdf`,
        {
          method: "POST",
          body: formData,
        }
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || "Upload failed");
      }

      // Clear input and refresh
      if (fileInputRef.current) fileInputRef.current.value = "";
      onPdfUploaded?.();
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const handleViewRawPdf = () => {
    setViewingPdf({
      url: getTestRawPdfUrl(subjectId, testId),
      title: `${testId} - Raw PDF`,
    });
  };

  const handleViewSplitPdf = (q: QuestionBrief, index: number) => {
    setViewingPdf({
      url: getQuestionPdfUrl(subjectId, testId, q.question_number),
      title: `Q${q.question_number} - Split PDF`,
      questionIndex: index,
    });
  };

  const handlePrevQuestion = () => {
    if (viewingPdf?.questionIndex === undefined || viewingPdf.questionIndex <= 0) return;
    const prevIndex = viewingPdf.questionIndex - 1;
    const prevQ = splitQuestions[prevIndex];
    handleViewSplitPdf(prevQ, prevIndex);
  };

  const handleNextQuestion = () => {
    if (
      viewingPdf?.questionIndex === undefined ||
      viewingPdf.questionIndex >= splitQuestions.length - 1
    )
      return;
    const nextIndex = viewingPdf.questionIndex + 1;
    const nextQ = splitQuestions[nextIndex];
    handleViewSplitPdf(nextQ, nextIndex);
  };

  return (
    <div className="p-6 space-y-6">
      {/* Status header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <StatusIcon status={isComplete ? "complete" : splitCount > 0 ? "partial" : "not_started"} size="lg" />
          <div>
            <h3 className="font-semibold">PDF Splitting</h3>
            <p className="text-sm text-text-secondary">
              {isComplete
                ? `Complete - ${splitCount} questions extracted`
                : splitCount > 0
                  ? `${splitCount} questions split`
                  : "Not started"}
            </p>
          </div>
        </div>

        <div className="flex gap-2">
          {splitCount > 0 && onReRunSplit && (
            <ActionButton
              variant="warning"
              icon={<RefreshCw className="w-4 h-4" />}
              onClick={onReRunSplit}
            >
              Re-run Split
            </ActionButton>
          )}
          {splitCount === 0 && rawPdfExists && onRunSplit && (
            <ActionButton
              variant="primary"
              icon={<Play className="w-4 h-4" />}
              onClick={onRunSplit}
            >
              Run PDF Split
            </ActionButton>
          )}
        </div>
      </div>

      {/* Main content - two columns */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Source PDF */}
        <div className="space-y-3">
          <h4 className="text-sm font-medium text-text-secondary uppercase tracking-wide">
            Source PDF
          </h4>
          {rawPdfExists ? (
            <div className="bg-surface border border-border rounded-lg overflow-hidden">
              <PDFPreview
                pdfUrl={getTestRawPdfUrl(subjectId, testId)}
                title="Original Test PDF"
                height="h-80"
                onExpand={handleViewRawPdf}
              />
            </div>
          ) : (
            <div className="bg-surface border border-border rounded-lg p-8 text-center">
              <FileText className="w-12 h-12 text-text-secondary mx-auto mb-3" />
              <p className="text-text-secondary mb-3">No raw PDF found</p>

              {/* Hidden file input */}
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf"
                onChange={handleFileChange}
                className="hidden"
              />

              <ActionButton
                variant="primary"
                icon={<Upload className="w-4 h-4" />}
                loading={uploading}
                onClick={handleUploadClick}
              >
                {uploading ? "Uploading..." : "Upload Test PDF"}
              </ActionButton>

              {uploadError && (
                <p className="text-xs text-error mt-2">{uploadError}</p>
              )}

              <p className="text-xs text-text-secondary mt-3">
                Or place PDF directly in:{" "}
                <code className="bg-background px-1 rounded">
                  app/data/pruebas/raw/{testId}/
                </code>
              </p>
            </div>
          )}
        </div>

        {/* Split Results */}
        <div className="space-y-3">
          <h4 className="text-sm font-medium text-text-secondary uppercase tracking-wide">
            Split Results ({splitCount} questions)
          </h4>
          <div className="bg-surface border border-border rounded-lg overflow-hidden max-h-96 overflow-y-auto">
            {splitCount === 0 ? (
              <div className="p-8 text-center">
                <Circle className="w-12 h-12 text-text-secondary mx-auto mb-3" />
                <p className="text-text-secondary">No questions split yet</p>
                {rawPdfExists && (
                  <p className="text-xs text-text-secondary mt-1">
                    Run PDF Split to extract questions
                  </p>
                )}
              </div>
            ) : (
              <table className="w-full">
                <thead className="sticky top-0 bg-surface">
                  <tr className="border-b border-border text-left text-xs text-text-secondary uppercase tracking-wide">
                    <th className="px-4 py-2 font-medium">Q#</th>
                    <th className="px-4 py-2 font-medium text-center">Status</th>
                    <th className="px-4 py-2 font-medium text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {questions.map((q, index) => (
                    <tr
                      key={q.id}
                      className="border-b border-border last:border-b-0 hover:bg-white/5"
                    >
                      <td className="px-4 py-2 font-mono text-sm">Q{q.question_number}</td>
                      <td className="px-4 py-2 text-center">
                        {q.has_split_pdf ? (
                          <CheckCircle2 className="w-4 h-4 text-success mx-auto" />
                        ) : (
                          <Circle className="w-4 h-4 text-text-secondary mx-auto" />
                        )}
                      </td>
                      <td className="px-4 py-2 text-right">
                        {q.has_split_pdf && (
                          <button
                            onClick={() => handleViewSplitPdf(q, index)}
                            className="inline-flex items-center gap-1 px-2 py-1 text-xs text-accent hover:bg-accent/10 rounded"
                          >
                            <Eye className="w-3 h-3" />
                            View
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>

      {/* PDF Viewer Modal */}
      {viewingPdf && (
        <PDFViewerModal
          isOpen={true}
          onClose={() => setViewingPdf(null)}
          pdfUrl={viewingPdf.url}
          title={viewingPdf.title}
          onPrevious={viewingPdf.questionIndex !== undefined ? handlePrevQuestion : undefined}
          onNext={viewingPdf.questionIndex !== undefined ? handleNextQuestion : undefined}
          previousLabel={
            viewingPdf.questionIndex !== undefined && viewingPdf.questionIndex > 0
              ? `Q${splitQuestions[viewingPdf.questionIndex - 1]?.question_number}`
              : undefined
          }
          nextLabel={
            viewingPdf.questionIndex !== undefined &&
            viewingPdf.questionIndex < splitQuestions.length - 1
              ? `Q${splitQuestions[viewingPdf.questionIndex + 1]?.question_number}`
              : undefined
          }
        />
      )}
    </div>
  );
}
