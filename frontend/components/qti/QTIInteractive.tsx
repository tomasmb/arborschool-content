"use client";

import { useMemo, useState } from "react";
import {
  CheckCircle2,
  XCircle,
  Circle,
  ChevronDown,
  ChevronRight,
  BookOpen,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  parseQTIXml,
  renderMath,
  QuestionStem,
  ImageGallery,
  FeedbackBlock,
  type QTIOption,
} from "./QTIRenderer";

function InteractiveOptionItem({
  option,
  showCorrect,
  size,
}: {
  option: QTIOption;
  showCorrect: boolean;
  size: "sm" | "md" | "lg";
}) {
  const [showFb, setShowFb] = useState(false);
  const rendered = useMemo(
    () => renderMath(option.text),
    [option.text],
  );

  const hasFeedback = !!option.feedback;

  const Icon = showCorrect
    ? option.isCorrect
      ? CheckCircle2
      : XCircle
    : Circle;

  const iconColor = showCorrect
    ? option.isCorrect
      ? "text-success"
      : "text-error/50"
    : "text-text-secondary";

  return (
    <div
      className={cn(
        "rounded-lg border transition-all duration-200",
        showCorrect && option.isCorrect
          ? "bg-success/10 border-success/30"
          : "bg-surface border-border",
      )}
    >
      <button
        type="button"
        onClick={() => hasFeedback && setShowFb(!showFb)}
        className={cn(
          "w-full flex items-start gap-3 p-3 text-left",
          hasFeedback && "cursor-pointer hover:bg-white/[0.03]",
          !hasFeedback && "cursor-default",
        )}
      >
        <div className="flex items-center gap-2 shrink-0">
          <Icon className={cn("w-4 h-4", iconColor)} />
          <span
            className={cn(
              "font-mono font-medium",
              size === "sm" && "text-xs",
              size === "md" && "text-sm",
              size === "lg" && "text-base",
              showCorrect &&
                option.isCorrect &&
                "text-success",
            )}
          >
            {option.id})
          </span>
        </div>

        <div className="flex-1 min-w-0">
          <div
            className={cn(
              "prose prose-invert max-w-none",
              size === "sm" && "text-sm",
              size === "md" && "text-base",
              size === "lg" && "text-lg",
            )}
            dangerouslySetInnerHTML={{ __html: rendered }}
          />
        </div>

        {hasFeedback && (
          <div className="shrink-0 mt-0.5">
            {showFb ? (
              <ChevronDown className="w-3.5 h-3.5 text-text-secondary" />
            ) : (
              <ChevronRight className="w-3.5 h-3.5 text-text-secondary" />
            )}
          </div>
        )}
      </button>

      {showFb && option.feedback && (
        <div
          className={cn(
            "px-3 pb-3 pt-0 ml-[52px]",
            "border-t border-border/30 mt-0",
          )}
        >
          <FeedbackBlock
            html={option.feedback}
            isCorrect={!!option.isCorrect}
            size={size}
          />
        </div>
      )}
    </div>
  );
}

function InteractiveSolution({
  html,
  size,
}: {
  html: string;
  size: "sm" | "md" | "lg";
}) {
  const [show, setShow] = useState(false);
  const rendered = useMemo(() => renderMath(html), [html]);

  return (
    <div className="mt-3 border-t border-border pt-3">
      <button
        type="button"
        onClick={() => setShow(!show)}
        className={cn(
          "inline-flex items-center gap-1.5 text-xs font-medium",
          "px-2.5 py-1.5 rounded-md transition-all duration-150",
          show
            ? "bg-accent/10 text-accent border border-accent/30"
            : "text-text-secondary hover:text-text-primary"
              + " hover:bg-white/[0.06] border border-border",
        )}
      >
        <BookOpen className="w-3.5 h-3.5" />
        {show ? "Hide Solution" : "Show Solution"}
      </button>

      {show && (
        <div
          className={cn(
            "mt-3 prose prose-invert max-w-none",
            "text-text-secondary",
            size === "sm" && "text-sm",
            size === "md" && "text-base",
            size === "lg" && "text-lg",
          )}
          dangerouslySetInnerHTML={{ __html: rendered }}
        />
      )}
    </div>
  );
}

export interface QTIInteractiveProps {
  qtiXml: string;
  showCorrectAnswer?: boolean;
  size?: "sm" | "md" | "lg";
  className?: string;
}

export function QTIInteractive({
  qtiXml,
  showCorrectAnswer = true,
  size = "sm",
  className,
}: QTIInteractiveProps) {
  const parsed = useMemo(() => parseQTIXml(qtiXml), [qtiXml]);

  if (!parsed) {
    return (
      <div className={cn("text-error text-sm", className)}>
        Failed to parse QTI XML
      </div>
    );
  }

  const hasSolution = !!parsed.workedSolution;

  return (
    <div className={cn("space-y-4", className)}>
      <QuestionStem html={parsed.stem} size={size} />
      <ImageGallery images={parsed.images} />

      <div className="space-y-2">
        {parsed.options.map((option) => (
          <InteractiveOptionItem
            key={option.id}
            option={option}
            showCorrect={showCorrectAnswer}
            size={size}
          />
        ))}
      </div>

      {hasSolution && (
        <InteractiveSolution
          html={parsed.workedSolution!}
          size={size}
        />
      )}
    </div>
  );
}
