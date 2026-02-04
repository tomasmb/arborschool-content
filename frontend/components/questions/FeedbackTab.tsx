"use client";

import { useMemo } from "react";
import { CheckCircle2, BookOpen } from "lucide-react";
import { parseFeedbackFromQti } from "@/lib/qti-parser";

interface FeedbackTabProps {
  qtiXml: string | null;
}

/**
 * Tab component for displaying per-choice feedback and worked solution.
 * Parses feedback content from QTI XML and displays it in a readable format.
 */
export function FeedbackTab({ qtiXml }: FeedbackTabProps) {
  const feedback = useMemo(() => {
    if (!qtiXml) return null;
    return parseFeedbackFromQti(qtiXml);
  }, [qtiXml]);

  if (!feedback) {
    return (
      <div className="text-sm text-text-secondary p-4 text-center">
        <p>No feedback available.</p>
        <p className="mt-1 text-xs">
          Run &quot;Enrich Feedback&quot; to add educational content to this question.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Per-choice feedback */}
      {feedback.choices.length > 0 && feedback.choices.some((c) => c.feedbackText) && (
        <section>
          <h3 className="font-medium mb-3 text-sm flex items-center gap-2">
            Per-choice Feedback
          </h3>
          <div className="space-y-2">
            {feedback.choices.map((choice) => (
              <div
                key={choice.identifier}
                className={`p-3 rounded-lg border ${
                  choice.isCorrect
                    ? "border-success/30 bg-success/5"
                    : "border-border bg-surface"
                }`}
              >
                <div className="flex items-center gap-2 mb-1">
                  <span
                    className={`font-mono text-sm px-2 py-0.5 rounded ${
                      choice.isCorrect
                        ? "bg-success/20 text-success"
                        : "bg-background text-text-secondary"
                    }`}
                  >
                    {choice.identifier}
                  </span>
                  {choice.isCorrect && (
                    <span className="flex items-center gap-1 text-xs text-success">
                      <CheckCircle2 className="w-3 h-3" />
                      Correct
                    </span>
                  )}
                </div>
                {choice.feedbackText ? (
                  <p className="text-sm text-text-secondary mt-2">
                    {choice.feedbackText}
                  </p>
                ) : (
                  <p className="text-sm text-text-secondary/50 mt-2 italic">
                    No feedback for this choice
                  </p>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Worked solution */}
      {feedback.workedSolution && (
        <section>
          <h3 className="font-medium mb-3 text-sm flex items-center gap-2">
            <BookOpen className="w-4 h-4 text-accent" />
            Worked Solution
          </h3>
          <div className="p-4 bg-accent/5 border border-accent/20 rounded-lg">
            <div
              className="text-sm prose prose-sm prose-invert max-w-none"
              dangerouslySetInnerHTML={{ __html: feedback.workedSolution }}
            />
          </div>
        </section>
      )}

      {/* Correct answer indicator if no per-choice feedback */}
      {feedback.correctAnswer &&
        !feedback.choices.some((c) => c.feedbackText) &&
        !feedback.workedSolution && (
          <section>
            <h3 className="font-medium mb-3 text-sm">Correct Answer</h3>
            <div className="p-3 bg-success/5 border border-success/20 rounded-lg">
              <span className="font-mono text-success">{feedback.correctAnswer}</span>
            </div>
          </section>
        )}
    </div>
  );
}
