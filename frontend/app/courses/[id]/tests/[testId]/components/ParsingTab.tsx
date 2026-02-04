"use client";

import { useState, useEffect, useCallback } from "react";
import { CheckCircle2, Circle, AlertTriangle, Play, RefreshCw, Eye } from "lucide-react";
import { cn } from "@/lib/utils";
import { PDFViewerModal } from "@/components/pdf";
import { QTIPreview } from "@/components/qti";
import { StatusIcon } from "@/components/ui";
import { getQuestionPdfUrl, getQuestionDetail, type QuestionBrief, type QuestionDetail } from "@/lib/api";

export interface ParsingTabProps {
  subjectId: string;
  testId: string;
  questions: QuestionBrief[];
  onRunParsing?: () => void;
  onReparse?: (questionNums: number[]) => void;
}

export function ParsingTab({
  subjectId,
  testId,
  questions,
  onRunParsing,
  onReparse,
}: ParsingTabProps) {
  const [selectedQuestion, setSelectedQuestion] = useState<number | null>(
    questions.length > 0 ? questions[0].question_number : null
  );
  const [questionDetail, setQuestionDetail] = useState<QuestionDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [viewingPdf, setViewingPdf] = useState(false);
  const [filter, setFilter] = useState<"all" | "parsed" | "issues" | "none">("all");

  const parsedQuestions = questions.filter((q) => q.has_qti);
  const unparsedQuestions = questions.filter((q) => q.has_split_pdf && !q.has_qti);
  const parseCount = parsedQuestions.length;
  const splitCount = questions.filter((q) => q.has_split_pdf).length;
  const isComplete = parseCount === splitCount && splitCount > 0;

  // Filter questions based on selected filter
  const filteredQuestions = questions.filter((q) => {
    if (filter === "all") return q.has_split_pdf;
    if (filter === "parsed") return q.has_qti;
    if (filter === "none") return q.has_split_pdf && !q.has_qti;
    // "issues" - would need validation data to filter properly
    return q.has_split_pdf;
  });

  // Load question detail when selection changes
  const loadQuestionDetail = useCallback(async () => {
    if (!selectedQuestion) {
      setQuestionDetail(null);
      return;
    }
    setLoadingDetail(true);
    try {
      const detail = await getQuestionDetail(subjectId, testId, selectedQuestion);
      setQuestionDetail(detail);
    } catch (err) {
      console.error("Failed to load question detail:", err);
      setQuestionDetail(null);
    } finally {
      setLoadingDetail(false);
    }
  }, [subjectId, testId, selectedQuestion]);

  useEffect(() => {
    loadQuestionDetail();
  }, [loadQuestionDetail]);

  const currentQuestion = questions.find((q) => q.question_number === selectedQuestion);
  const currentIndex = filteredQuestions.findIndex((q) => q.question_number === selectedQuestion);

  const handlePrevQuestion = () => {
    if (currentIndex > 0) {
      setSelectedQuestion(filteredQuestions[currentIndex - 1].question_number);
    }
  };

  const handleNextQuestion = () => {
    if (currentIndex < filteredQuestions.length - 1) {
      setSelectedQuestion(filteredQuestions[currentIndex + 1].question_number);
    }
  };

  return (
    <div className="h-full flex flex-col">
      {/* Status header */}
      <div className="p-4 border-b border-border flex items-center justify-between">
        <div className="flex items-center gap-3">
          <StatusIcon
            status={isComplete ? "complete" : parseCount > 0 ? "partial" : "not_started"}
            size="lg"
          />
          <div>
            <h3 className="font-semibold">QTI Parsing</h3>
            <p className="text-sm text-text-secondary">
              {parseCount}/{splitCount} questions parsed
            </p>
          </div>
        </div>

        <div className="flex gap-2">
          {unparsedQuestions.length > 0 && onRunParsing && (
            <button
              onClick={onRunParsing}
              className="flex items-center gap-2 px-3 py-2 bg-accent text-white rounded-lg text-sm font-medium hover:bg-accent/90"
            >
              <Play className="w-4 h-4" />
              Parse {unparsedQuestions.length} Remaining
            </button>
          )}
          {selectedQuestion && onReparse && (
            <button
              onClick={() => onReparse([selectedQuestion])}
              className="flex items-center gap-2 px-3 py-2 bg-warning/10 text-warning rounded-lg text-sm font-medium hover:bg-warning/20 border border-warning/20"
            >
              <RefreshCw className="w-4 h-4" />
              Re-parse Q{selectedQuestion}
            </button>
          )}
        </div>
      </div>

      {/* Main content - three column layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Question selector (left rail) */}
        <div className="w-48 border-r border-border flex flex-col">
          {/* Filter */}
          <div className="p-2 border-b border-border">
            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value as typeof filter)}
              className="w-full px-2 py-1 text-xs bg-surface border border-border rounded"
            >
              <option value="all">All ({splitCount})</option>
              <option value="parsed">Parsed ({parseCount})</option>
              <option value="none">Not Parsed ({unparsedQuestions.length})</option>
            </select>
          </div>

          {/* Question list */}
          <div className="flex-1 overflow-y-auto">
            {filteredQuestions.map((q) => (
              <button
                key={q.id}
                onClick={() => setSelectedQuestion(q.question_number)}
                className={cn(
                  "w-full flex items-center gap-2 px-3 py-2 text-left text-sm border-b border-border transition-colors",
                  selectedQuestion === q.question_number
                    ? "bg-accent/10 text-accent"
                    : "hover:bg-white/5"
                )}
              >
                <span className="font-mono">Q{q.question_number}</span>
                <span className="flex-1" />
                {q.has_qti ? (
                  <CheckCircle2 className="w-3 h-3 text-success" />
                ) : (
                  <Circle className="w-3 h-3 text-text-secondary" />
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Comparison view (main area) */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {selectedQuestion && currentQuestion ? (
            <>
              {/* Navigation header */}
              <div className="p-3 border-b border-border flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <button
                    onClick={handlePrevQuestion}
                    disabled={currentIndex === 0}
                    className="p-1 rounded hover:bg-white/10 disabled:opacity-50"
                  >
                    ←
                  </button>
                  <span className="font-medium">Q{selectedQuestion}</span>
                  <button
                    onClick={handleNextQuestion}
                    disabled={currentIndex === filteredQuestions.length - 1}
                    className="p-1 rounded hover:bg-white/10 disabled:opacity-50"
                  >
                    →
                  </button>
                </div>

                {currentQuestion.has_split_pdf && (
                  <button
                    onClick={() => setViewingPdf(true)}
                    className="flex items-center gap-1 px-2 py-1 text-xs text-accent hover:bg-accent/10 rounded"
                  >
                    <Eye className="w-3 h-3" />
                    View PDF Fullscreen
                  </button>
                )}
              </div>

              {/* Side-by-side comparison */}
              <div className="flex-1 grid grid-cols-2 divide-x divide-border overflow-hidden">
                {/* PDF side */}
                <div className="flex flex-col overflow-hidden">
                  <div className="px-3 py-2 border-b border-border bg-surface/50">
                    <h4 className="text-xs font-medium text-text-secondary uppercase">
                      Original PDF
                    </h4>
                  </div>
                  <div className="flex-1 overflow-auto bg-gray-900 flex items-center justify-center">
                    {currentQuestion.has_split_pdf ? (
                      <iframe
                        src={getQuestionPdfUrl(subjectId, testId, selectedQuestion)}
                        className="w-full h-full"
                        title={`Q${selectedQuestion} PDF`}
                      />
                    ) : (
                      <div className="text-text-secondary text-sm">No split PDF</div>
                    )}
                  </div>
                </div>

                {/* QTI side */}
                <div className="flex flex-col overflow-hidden">
                  <div className="px-3 py-2 border-b border-border bg-surface/50">
                    <h4 className="text-xs font-medium text-text-secondary uppercase">
                      Parsed QTI
                    </h4>
                  </div>
                  <div className="flex-1 overflow-auto p-4">
                    {loadingDetail ? (
                      <div className="text-text-secondary text-sm">Loading...</div>
                    ) : questionDetail?.qti_xml ? (
                      <QTIPreview qtiXml={questionDetail.qti_xml} showCorrectAnswer />
                    ) : (
                      <div className="text-center py-8">
                        <Circle className="w-8 h-8 text-text-secondary mx-auto mb-2" />
                        <p className="text-text-secondary text-sm">Not parsed yet</p>
                        {onRunParsing && (
                          <button
                            onClick={onRunParsing}
                            className="mt-3 px-3 py-1.5 bg-accent text-white rounded text-sm"
                          >
                            Parse Question
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-text-secondary">
              Select a question to view comparison
            </div>
          )}
        </div>
      </div>

      {/* PDF Viewer Modal */}
      {viewingPdf && selectedQuestion && (
        <PDFViewerModal
          isOpen={true}
          onClose={() => setViewingPdf(false)}
          pdfUrl={getQuestionPdfUrl(subjectId, testId, selectedQuestion)}
          title={`Q${selectedQuestion} - PDF`}
          onPrevious={currentIndex > 0 ? handlePrevQuestion : undefined}
          onNext={currentIndex < filteredQuestions.length - 1 ? handleNextQuestion : undefined}
          previousLabel={currentIndex > 0 ? `Q${filteredQuestions[currentIndex - 1]?.question_number}` : undefined}
          nextLabel={
            currentIndex < filteredQuestions.length - 1
              ? `Q${filteredQuestions[currentIndex + 1]?.question_number}`
              : undefined
          }
        />
      )}
    </div>
  );
}
