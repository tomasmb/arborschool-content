"use client";

import { useState, useEffect } from "react";
import {
  Trash2,
  Loader2,
  AlertCircle,
  MessageSquarePlus,
  ShieldCheck,
  CheckCircle2,
  Circle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { getQuestionDetail, type VariantBrief } from "@/lib/api";

export interface VariantsExpandedContentProps {
  subjectId: string;
  testId: string;
  questionNum: number;
  variantCount: number;
  onDeleteVariant?: (variantId: string) => void;
}

/**
 * Expanded content showing individual variants for a question.
 * Fetches variant details and displays enrichment/validation status.
 */
export function VariantsExpandedContent({
  subjectId,
  testId,
  questionNum,
  variantCount,
  onDeleteVariant,
}: VariantsExpandedContentProps) {
  const [variants, setVariants] = useState<VariantBrief[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchVariants() {
      setLoading(true);
      setError(null);
      try {
        const detail = await getQuestionDetail(subjectId, testId, questionNum);
        if (!cancelled) {
          setVariants(detail.variants || []);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load variants");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    fetchVariants();
    return () => {
      cancelled = true;
    };
  }, [subjectId, testId, questionNum]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-6">
        <Loader2 className="w-4 h-4 animate-spin text-accent" />
        <span className="ml-2 text-text-secondary text-sm">Loading variants...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-6 text-error">
        <AlertCircle className="w-4 h-4" />
        <span className="ml-2 text-sm">{error}</span>
      </div>
    );
  }

  // Compute variant stats
  const enrichedCount = variants.filter((v) => v.is_enriched).length;
  const validatedCount = variants.filter((v) => v.is_validated).length;

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-medium">Q{questionNum} Variants</h4>
        <div className="flex items-center gap-4 text-xs">
          <span className="text-text-secondary">{variants.length} total</span>
          {enrichedCount > 0 && (
            <span className="text-accent">{enrichedCount} enriched</span>
          )}
          {validatedCount > 0 && (
            <span className="text-success">{validatedCount} validated</span>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
        {variants.map((v) => (
          <div
            key={v.id}
            className={cn(
              "flex items-center justify-between p-2 bg-background rounded border",
              v.is_validated
                ? "border-success/30"
                : v.is_enriched
                  ? "border-accent/30"
                  : v.has_qti
                    ? "border-border/50"
                    : "border-warning/30"
            )}
          >
            <div className="flex items-center gap-2">
              <span className="text-sm font-mono">{v.folder_name}</span>
              <div className="flex items-center gap-0.5">
                {v.is_validated ? (
                  <ShieldCheck className="w-3 h-3 text-success" aria-label="Validated" />
                ) : v.is_enriched ? (
                  <MessageSquarePlus className="w-3 h-3 text-accent" aria-label="Enriched" />
                ) : v.has_qti ? (
                  <CheckCircle2 className="w-3 h-3 text-text-secondary" aria-label="Has QTI" />
                ) : (
                  <Circle className="w-3 h-3 text-warning" aria-label="Missing QTI" />
                )}
              </div>
            </div>
            {onDeleteVariant && (
              <button
                onClick={() => onDeleteVariant(v.id)}
                className="text-xs text-error hover:underline ml-2"
              >
                <Trash2 className="w-3 h-3" />
              </button>
            )}
          </div>
        ))}
      </div>

      {variants.length === 0 && (
        <p className="text-center text-text-secondary text-sm py-4">
          No variants found for this question.
        </p>
      )}

      <p className="mt-3 text-xs text-text-secondary">
        Variants are generated with feedback included. View individual variants in the
        question detail panel.
      </p>
    </div>
  );
}
