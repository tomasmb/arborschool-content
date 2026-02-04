"use client";

import { useMemo, useEffect } from "react";
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
  /** Show feedback for each option */
  showFeedback?: boolean;
  /** Show worked solution */
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

    // Check for parse errors
    const parseError = doc.querySelector("parsererror");
    if (parseError) {
      console.error("QTI XML parse error:", parseError.textContent);
      return null;
    }

    // Extract correct answer
    const correctValueEl = doc.querySelector("qti-correct-response qti-value");
    const correctAnswer = correctValueEl?.textContent?.trim() || null;

    // Extract prompt/stem
    const promptEl = doc.querySelector("qti-prompt");
    const itemBodyEl = doc.querySelector("qti-item-body");
    let stem = "";

    if (promptEl) {
      stem = extractContent(promptEl);
    } else if (itemBodyEl) {
      // Get content before the choice interaction
      const choiceInteraction = itemBodyEl.querySelector("qti-choice-interaction");
      if (choiceInteraction) {
        // Clone and remove choice interaction to get remaining content
        const clone = itemBodyEl.cloneNode(true) as Element;
        const toRemove = clone.querySelector("qti-choice-interaction");
        toRemove?.remove();
        stem = extractContent(clone);
      } else {
        stem = extractContent(itemBodyEl);
      }
    }

    // Extract options
    const options: QTIOption[] = [];
    const choiceElements = doc.querySelectorAll("qti-simple-choice");

    choiceElements.forEach((choice) => {
      const id = choice.getAttribute("identifier") || "";

      // Get choice text (excluding feedback elements)
      const clone = choice.cloneNode(true) as Element;
      const feedbackEl = clone.querySelector("qti-feedback-inline");
      const feedbackText = feedbackEl?.textContent?.trim() || "";
      feedbackEl?.remove();

      const text = extractContent(clone);

      options.push({
        id,
        text,
        isCorrect: id === correctAnswer,
        feedback: feedbackText || undefined,
      });
    });

    // Extract images
    const images: string[] = [];
    const imgElements = doc.querySelectorAll("img");
    imgElements.forEach((img) => {
      const src = img.getAttribute("src");
      if (src) images.push(src);
    });

    // Extract worked solution
    const solutionBlock =
      doc.querySelector('qti-feedback-block[outcome-identifier="SOLUTION"]') ||
      doc.querySelector('qti-feedback-block[identifier="SOLUTION"]');
    const workedSolution = solutionBlock ? extractContent(solutionBlock) : null;

    return {
      stem,
      options,
      correctAnswer,
      images,
      workedSolution,
    };
  } catch (error) {
    console.error("Failed to parse QTI XML:", error);
    return null;
  }
}

/**
 * Extract text content from an element, handling MathML and other special cases.
 */
function extractContent(element: Element): string {
  // Get inner HTML first
  let html = element.innerHTML;

  // Clean up namespaced tags
  html = html.replace(/<qti-([^>]+)>/g, "<span data-qti-$1>");
  html = html.replace(/<\/qti-([^>]+)>/g, "</span>");

  // Convert MathML to HTML comment placeholder for later processing
  // We'll handle MathML rendering separately
  return html.trim();
}

// -----------------------------------------------------------------------------
// Math Rendering
// -----------------------------------------------------------------------------

/**
 * Render LaTeX math expressions in a string.
 * Handles both inline ($...$) and display ($$...$$) math.
 */
function renderMath(text: string): string {
  if (!text) return text;

  // Handle display math first ($$...$$)
  text = text.replace(/\$\$([\s\S]+?)\$\$/g, (_, latex) => {
    try {
      return katex.renderToString(latex.trim(), {
        displayMode: true,
        throwOnError: false,
      });
    } catch (e) {
      return `$$${latex}$$`;
    }
  });

  // Handle inline math ($...$)
  text = text.replace(/\$([^$]+)\$/g, (_, latex) => {
    try {
      return katex.renderToString(latex.trim(), {
        displayMode: false,
        throwOnError: false,
      });
    } catch (e) {
      return `$${latex}$`;
    }
  });

  // Handle MathML (attempt to convert or render as-is)
  // Note: Modern browsers support MathML natively
  // We leave MathML as-is since it renders in browsers

  return text;
}

// -----------------------------------------------------------------------------
// Sub-components
// -----------------------------------------------------------------------------

function QuestionStem({ html, size }: { html: string; size: "sm" | "md" | "lg" }) {
  const rendered = useMemo(() => renderMath(html), [html]);

  return (
    <div
      className={cn(
        "prose prose-invert max-w-none",
        size === "sm" && "text-sm",
        size === "md" && "text-base",
        size === "lg" && "text-lg"
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
  const rendered = useMemo(() => renderMath(option.text), [option.text]);

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
        "flex items-start gap-3 p-3 rounded-lg border transition-colors",
        showCorrect && option.isCorrect
          ? "bg-success/10 border-success/30"
          : "bg-surface border-border"
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
            showCorrect && option.isCorrect && "text-success"
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
            size === "lg" && "text-lg"
          )}
          dangerouslySetInnerHTML={{ __html: rendered }}
        />

        {showFeedback && option.feedback && (
          <div
            className={cn(
              "mt-2 pt-2 border-t border-border/50",
              size === "sm" && "text-xs",
              size === "md" && "text-sm",
              size === "lg" && "text-base"
            )}
          >
            <span className={cn("font-medium", option.isCorrect ? "text-success" : "text-warning")}>
              {option.isCorrect ? "Correct: " : "Feedback: "}
            </span>
            <span className="text-text-secondary">{option.feedback}</span>
          </div>
        )}
      </div>
    </div>
  );
}

function ImageGallery({ images }: { images: string[] }) {
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

function WorkedSolution({ html, size }: { html: string; size: "sm" | "md" | "lg" }) {
  const rendered = useMemo(() => renderMath(html), [html]);

  return (
    <div className="mt-4 pt-4 border-t border-border">
      <h4 className="text-sm font-semibold text-accent mb-2">Worked Solution</h4>
      <div
        className={cn(
          "prose prose-invert max-w-none text-text-secondary",
          size === "sm" && "text-sm",
          size === "md" && "text-base",
          size === "lg" && "text-lg"
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
      {/* Question stem */}
      <QuestionStem html={parsed.stem} size={size} />

      {/* Images */}
      <ImageGallery images={parsed.images} />

      {/* Options */}
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

      {/* Worked solution */}
      {showWorkedSolution && parsed.workedSolution && (
        <WorkedSolution html={parsed.workedSolution} size={size} />
      )}
    </div>
  );
}

/**
 * Simple preview of QTI content showing just stem and options.
 * Used in comparison views and tables.
 */
export interface QTIPreviewProps {
  qtiXml: string;
  showCorrectAnswer?: boolean;
  className?: string;
}

export function QTIPreview({ qtiXml, showCorrectAnswer = true, className }: QTIPreviewProps) {
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

/**
 * Full QTI display with all feedback and worked solution.
 * Used in detail panels.
 */
export interface QTIFullViewProps {
  qtiXml: string;
  className?: string;
}

export function QTIFullView({ qtiXml, className }: QTIFullViewProps) {
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
