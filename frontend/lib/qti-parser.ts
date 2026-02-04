/**
 * QTI XML parsing utilities for extracting feedback content.
 *
 * These functions parse QTI 3.0 XML to extract feedback elements that are
 * embedded in the question XML after enrichment.
 */

// -----------------------------------------------------------------------------
// Types
// -----------------------------------------------------------------------------

export interface ChoiceFeedback {
  identifier: string;
  isCorrect: boolean;
  feedbackText: string;
}

export interface ParsedFeedback {
  choices: ChoiceFeedback[];
  workedSolution: string | null;
  correctAnswer: string | null;
}

// -----------------------------------------------------------------------------
// Parser
// -----------------------------------------------------------------------------

/**
 * Parse feedback elements from QTI XML.
 *
 * Extracts:
 * - Per-choice feedback from qti-feedback-inline elements
 * - Worked solution from qti-feedback-block with outcome-identifier="SOLUTION"
 * - Correct answer from qti-correct-response
 *
 * @param qtiXml - Raw QTI XML string
 * @returns ParsedFeedback or null if parsing fails or no feedback found
 */
export function parseFeedbackFromQti(qtiXml: string): ParsedFeedback | null {
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

    // Extract correct answer from qti-correct-response
    const correctValueEl = doc.querySelector("qti-correct-response qti-value");
    const correctAnswer = correctValueEl?.textContent?.trim() || null;

    // Extract choice feedback
    const choices: ChoiceFeedback[] = [];
    const choiceElements = doc.querySelectorAll("qti-simple-choice");

    choiceElements.forEach((choice) => {
      const identifier = choice.getAttribute("identifier") || "";

      // Look for feedback-inline within the choice
      const feedbackEl = choice.querySelector("qti-feedback-inline");
      const feedbackText = feedbackEl?.textContent?.trim() || "";

      choices.push({
        identifier,
        isCorrect: identifier === correctAnswer,
        feedbackText,
      });
    });

    // Extract worked solution from feedback-block
    // Look for SOLUTION outcome identifier or general feedback block
    const solutionBlock =
      doc.querySelector('qti-feedback-block[outcome-identifier="SOLUTION"]') ||
      doc.querySelector('qti-feedback-block[identifier="SOLUTION"]');

    let workedSolution: string | null = null;
    if (solutionBlock) {
      // Get inner HTML to preserve formatting
      workedSolution = solutionBlock.innerHTML.trim();
      // Clean up any extra whitespace
      workedSolution = workedSolution.replace(/\s+/g, " ").trim();
    }

    // Return null if no feedback content found
    const hasFeedback = choices.some((c) => c.feedbackText) || workedSolution;
    if (!hasFeedback) {
      return null;
    }

    return {
      choices,
      workedSolution,
      correctAnswer,
    };
  } catch (error) {
    console.error("Failed to parse QTI XML:", error);
    return null;
  }
}

/**
 * Check if QTI XML has any feedback content.
 *
 * Quick check without full parsing - looks for feedback element tags.
 */
export function hasFeedbackContent(qtiXml: string): boolean {
  if (!qtiXml) return false;
  return (
    qtiXml.includes("qti-feedback-inline") ||
    qtiXml.includes("qti-feedback-block")
  );
}
