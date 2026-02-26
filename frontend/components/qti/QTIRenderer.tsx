"use client";

import { useMemo } from "react";
import { CheckCircle2, XCircle, Circle } from "lucide-react";
import { cn } from "@/lib/utils";
import katex from "katex";
import "katex/dist/katex.min.css";

// -----------------------------------------------------------------------------
// Types
// -----------------------------------------------------------------------------

export interface QTIOption {
  id: string;
  text: string;
  isCorrect?: boolean;
  feedback?: string;
}

export interface ParsedQTI {
  stem: string;
  options: QTIOption[];
  correctAnswer: string | null;
  images: string[];
  workedSolution: string | null;
}

export interface QTIRendererProps {
  /** Raw QTI XML string */
  qtiXml: string;
  /** Show correct answer highlighting */
  showCorrectAnswer?: boolean;
  /** Show feedback for each option (always visible) */
  showFeedback?: boolean;
  /** Show worked solution (always visible) */
  showWorkedSolution?: boolean;
  /** Size variant */
  size?: "sm" | "md" | "lg";
  /** Additional class names */
  className?: string;
}

// -----------------------------------------------------------------------------
// QTI Parser
// -----------------------------------------------------------------------------

function parseQTIXml(qtiXml: string): ParsedQTI | null {
  if (!qtiXml || typeof qtiXml !== "string") {
    return null;
  }

  try {
    const parser = new DOMParser();
    const doc = parser.parseFromString(qtiXml, "text/xml");

    const parseError = doc.querySelector("parsererror");
    if (parseError) {
      console.error("QTI XML parse error:", parseError.textContent);
      return null;
    }

    const correctValueEl = doc.querySelector(
      "qti-correct-response qti-value",
    );
    const correctAnswer =
      correctValueEl?.textContent?.trim() || null;

    const promptEl = doc.querySelector("qti-prompt");
    const itemBodyEl = doc.querySelector("qti-item-body");
    let stem = "";

    if (promptEl) {
      stem = extractContent(promptEl);
    } else if (itemBodyEl) {
      const clone = itemBodyEl.cloneNode(true) as Element;
      clone
        .querySelector("qti-choice-interaction")
        ?.remove();
      clone
        .querySelectorAll("qti-feedback-block")
        .forEach((el) => el.remove());
      // Strip inline <img> so images render only via ImageGallery
      clone
        .querySelectorAll("img")
        .forEach((el) => el.remove());
      stem = extractContent(clone);
    }

    const options: QTIOption[] = [];
    const choiceElements = doc.querySelectorAll(
      "qti-simple-choice",
    );

    choiceElements.forEach((choice) => {
      const id = choice.getAttribute("identifier") || "";
      const clone = choice.cloneNode(true) as Element;
      const feedbackEl = clone.querySelector(
        "qti-feedback-inline",
      );
      const feedbackHtml = feedbackEl
        ? extractContent(feedbackEl)
        : "";
      feedbackEl?.remove();

      options.push({
        id,
        text: extractContent(clone),
        isCorrect: id === correctAnswer,
        feedback: feedbackHtml || undefined,
      });
    });

    const images: string[] = [];
    doc.querySelectorAll("img").forEach((img) => {
      const src = img.getAttribute("src");
      if (src) images.push(src);
    });

    const solutionBlock =
      doc.querySelector(
        'qti-feedback-block[outcome-identifier="SOLUTION"]',
      ) ||
      doc.querySelector(
        'qti-feedback-block[identifier="SOLUTION"]',
      );
    const workedSolution = solutionBlock
      ? extractContent(solutionBlock)
      : null;

    return { stem, options, correctAnswer, images, workedSolution };
  } catch (error) {
    console.error("Failed to parse QTI XML:", error);
    return null;
  }
}

/** Re-export parser for use by QuestionPreviewCard. */
export { parseQTIXml };

function extractContent(element: Element): string {
  let html = element.innerHTML;
  html = html.replace(/<qti-([^>]+)>/g, "<span data-qti-$1>");
  html = html.replace(/<\/qti-([^>]+)>/g, "</span>");
  return html.trim();
}

// -----------------------------------------------------------------------------
// Math Rendering
// -----------------------------------------------------------------------------

function renderMath(text: string): string {
  if (!text) return text;

  // QTI content uses native MathML (<math> elements) for math.
  // Skip LaTeX $...$ processing to avoid misinterpreting
  // currency dollar signs (e.g. "$15.000") as LaTeX delimiters.
  if (text.includes("<math")) return text;

  text = text.replace(/\$\$([\s\S]+?)\$\$/g, (_, latex) => {
    try {
      return katex.renderToString(latex.trim(), {
        displayMode: true,
        throwOnError: false,
      });
    } catch {
      return `$$${latex}$$`;
    }
  });

  text = text.replace(/\$([^$]+)\$/g, (_, latex) => {
    try {
      return katex.renderToString(latex.trim(), {
        displayMode: false,
        throwOnError: false,
      });
    } catch {
      return `$${latex}$`;
    }
  });

  return text;
}

/** Exported for reuse by shared question components. */
export { renderMath };

// -----------------------------------------------------------------------------
// Sub-components
// -----------------------------------------------------------------------------

export function QuestionStem({
  html,
  size,
}: {
  html: string;
  size: "sm" | "md" | "lg";
}) {
  const rendered = useMemo(() => renderMath(html), [html]);

  return (
    <div
      className={cn(
        "prose prose-invert max-w-none",
        size === "sm" && "text-sm",
        size === "md" && "text-base",
        size === "lg" && "text-lg",
      )}
      dangerouslySetInnerHTML={{ __html: rendered }}
    />
  );
}

function OptionItem({
  option,
  showCorrect,
  showFeedback,
  size,
}: {
  option: QTIOption;
  showCorrect: boolean;
  showFeedback: boolean;
  size: "sm" | "md" | "lg";
}) {
  const rendered = useMemo(
    () => renderMath(option.text),
    [option.text],
  );

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
        "flex items-start gap-3 p-3 rounded-lg border",
        "transition-colors",
        showCorrect && option.isCorrect
          ? "bg-success/10 border-success/30"
          : "bg-surface border-border",
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
            showCorrect && option.isCorrect && "text-success",
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

        {showFeedback && option.feedback && (
          <FeedbackBlock
            html={option.feedback}
            isCorrect={!!option.isCorrect}
            size={size}
          />
        )}
      </div>
    </div>
  );
}

export function FeedbackBlock({
  html,
  isCorrect,
  size,
}: {
  html: string;
  isCorrect: boolean;
  size: "sm" | "md" | "lg";
}) {
  const rendered = useMemo(() => renderMath(html), [html]);

  return (
    <div
      className={cn(
        "mt-2 pt-2 border-t border-border/50",
        size === "sm" && "text-xs",
        size === "md" && "text-sm",
        size === "lg" && "text-base",
      )}
    >
      <span
        className={cn(
          "font-medium",
          isCorrect ? "text-success" : "text-warning",
        )}
      >
        {isCorrect ? "Correct: " : "Feedback: "}
      </span>
      <span
        className="text-text-secondary prose prose-invert
          max-w-none inline"
        dangerouslySetInnerHTML={{ __html: rendered }}
      />
    </div>
  );
}

export function ImageGallery({ images }: { images: string[] }) {
  if (images.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-2 my-4">
      {images.map((src, i) => (
        <img
          key={i}
          src={src}
          alt={`Question image ${i + 1}`}
          className="max-w-full h-auto rounded-lg border border-border"
          style={{ maxHeight: "300px" }}
        />
      ))}
    </div>
  );
}

function WorkedSolution({
  html,
  size,
}: {
  html: string;
  size: "sm" | "md" | "lg";
}) {
  const rendered = useMemo(() => renderMath(html), [html]);

  return (
    <div className="mt-4 pt-4 border-t border-border">
      <h4 className="text-sm font-semibold text-accent mb-2">
        Worked Solution
      </h4>
      <div
        className={cn(
          "prose prose-invert max-w-none text-text-secondary",
          size === "sm" && "text-sm",
          size === "md" && "text-base",
          size === "lg" && "text-lg",
        )}
        dangerouslySetInnerHTML={{ __html: rendered }}
      />
    </div>
  );
}

// -----------------------------------------------------------------------------
// Main Component
// -----------------------------------------------------------------------------

export function QTIRenderer({
  qtiXml,
  showCorrectAnswer = false,
  showFeedback = false,
  showWorkedSolution = false,
  size = "md",
  className,
}: QTIRendererProps) {
  const parsed = useMemo(() => parseQTIXml(qtiXml), [qtiXml]);

  if (!parsed) {
    return (
      <div className={cn("text-error text-sm", className)}>
        Failed to parse QTI XML
      </div>
    );
  }

  return (
    <div className={cn("space-y-4", className)}>
      <QuestionStem html={parsed.stem} size={size} />
      <ImageGallery images={parsed.images} />

      <div className="space-y-2">
        {parsed.options.map((option) => (
          <OptionItem
            key={option.id}
            option={option}
            showCorrect={showCorrectAnswer}
            showFeedback={showFeedback}
            size={size}
          />
        ))}
      </div>

      {showWorkedSolution && parsed.workedSolution && (
        <WorkedSolution
          html={parsed.workedSolution}
          size={size}
        />
      )}
    </div>
  );
}

// -----------------------------------------------------------------------------
// Preset components
// -----------------------------------------------------------------------------

export interface QTIPreviewProps {
  qtiXml: string;
  showCorrectAnswer?: boolean;
  className?: string;
}

export function QTIPreview({
  qtiXml,
  showCorrectAnswer = true,
  className,
}: QTIPreviewProps) {
  return (
    <QTIRenderer
      qtiXml={qtiXml}
      showCorrectAnswer={showCorrectAnswer}
      showFeedback={false}
      showWorkedSolution={false}
      size="sm"
      className={className}
    />
  );
}

export interface QTIFullViewProps {
  qtiXml: string;
  className?: string;
}

export function QTIFullView({
  qtiXml,
  className,
}: QTIFullViewProps) {
  return (
    <QTIRenderer
      qtiXml={qtiXml}
      showCorrectAnswer={true}
      showFeedback={true}
      showWorkedSolution={true}
      size="md"
      className={className}
    />
  );
}
