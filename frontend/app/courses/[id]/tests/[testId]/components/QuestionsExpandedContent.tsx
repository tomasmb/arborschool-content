"use client";

import { useState, useEffect } from "react";
import {
  CheckCircle2,
  XCircle,
  Tag,
  Loader2,
  AlertCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { StatusBadge } from "@/components/ui";
import { QTIRenderer } from "@/components/qti";
import {
  getQuestionDetail,
  type QuestionBrief,
  type QuestionDetail,
} from "@/lib/api";
import type { ValidationResultDetail } from "@/lib/api-types";

// ─── Public Interface ──────────────────────────────────────

export interface QuestionsExpandedContentProps {
  subjectId: string;
  testId: string;
  questionNum: number;
  question: QuestionBrief;
}

/**
 * Expanded row content for a single question.
 * Fetches full detail on mount and shows QTI preview + pipeline status.
 */
export function QuestionsExpandedContent({
  subjectId,
  testId,
  questionNum,
  question,
}: QuestionsExpandedContentProps) {
  const [detail, setDetail] = useState<QuestionDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchDetail() {
      setLoading(true);
      setError(null);
      try {
        const data = await getQuestionDetail(subjectId, testId, questionNum);
        if (!cancelled) setDetail(data);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load question");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchDetail();
    return () => { cancelled = true; };
  }, [subjectId, testId, questionNum]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-5 h-5 animate-spin text-accent" />
        <span className="ml-2 text-text-secondary text-sm">Loading question...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-8 text-error">
        <AlertCircle className="w-5 h-5" />
        <span className="ml-2 text-sm">{error}</span>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-4">
      {/* Left: Question preview */}
      <div>
        <h4 className="text-sm font-medium text-text-secondary mb-2">Question Preview</h4>
        <div className="bg-surface border border-border rounded-lg p-4">
          {detail?.qti_xml ? (
            <QTIRenderer qtiXml={detail.qti_xml} size="sm" />
          ) : (
            <p className="text-sm text-text-secondary">No QTI content available</p>
          )}
        </div>
      </div>

      {/* Right: Status and feedback */}
      <div className="space-y-4">
        <PipelineStatusBadges question={question} />

        {detail?.atom_tags && detail.atom_tags.length > 0 && (
          <AtomTagsList tags={detail.atom_tags} />
        )}

        {detail?.validation_result && (
          <ValidationResultCard result={detail.validation_result} />
        )}
      </div>
    </div>
  );
}

// ─── Private helpers ───────────────────────────────────────

function PipelineStatusBadges({ question }: { question: QuestionBrief }) {
  return (
    <div>
      <h4 className="text-sm font-medium text-text-secondary mb-2">Pipeline Status</h4>
      <div className="flex flex-wrap gap-2">
        <StatusBadge
          status={question.is_tagged ? "complete" : "not_started"}
          label="Tagged"
          size="sm"
        />
        <StatusBadge
          status={
            question.is_enriched
              ? "complete"
              : question.is_tagged ? "not_started" : "blocked"
          }
          label="Enriched"
          size="sm"
        />
        <StatusBadge
          status={
            question.is_validated
              ? "complete"
              : question.is_enriched ? "not_started" : "blocked"
          }
          label="Validated"
          size="sm"
        />
      </div>
    </div>
  );
}

function AtomTagsList({ tags }: { tags: { atom_id: string; titulo: string }[] }) {
  return (
    <div>
      <h4 className="text-sm font-medium text-text-secondary mb-2">Atom Tags</h4>
      <div className="flex flex-wrap gap-1">
        {tags.map((tag) => (
          <span
            key={tag.atom_id}
            className="inline-flex items-center gap-1 px-2 py-0.5 bg-accent/10 text-accent text-xs rounded"
            title={tag.titulo}
          >
            <Tag className="w-3 h-3" />
            {tag.atom_id}
          </span>
        ))}
      </div>
    </div>
  );
}

function ValidationResultCard({ result }: { result: ValidationResultDetail }) {
  const passed = result.validation_result === "pass";
  return (
    <div>
      <h4 className="text-sm font-medium text-text-secondary mb-2">Validation Result</h4>
      <div
        className={cn(
          "border rounded-lg p-3 text-sm",
          passed
            ? "bg-success/10 border-success/20 text-success"
            : "bg-error/10 border-error/20 text-error",
        )}
      >
        <div className="flex items-center gap-2">
          {passed ? <CheckCircle2 className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
          <span className="font-medium capitalize">
            {result.validation_result}
          </span>
        </div>
        {result.overall_reasoning && (
          <p className="mt-1 text-xs opacity-80">{result.overall_reasoning}</p>
        )}
      </div>
    </div>
  );
}
