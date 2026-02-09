"use client";

import { Sparkles, Calendar, Database } from "lucide-react";
import type { AtomPipelineSummary } from "@/lib/api";

interface GenerationTabProps {
  subjectId: string;
  summary: AtomPipelineSummary;
  onRunGeneration: () => void;
}

export function GenerationTab({
  subjectId,
  summary,
  onRunGeneration,
}: GenerationTabProps) {
  const hasAtoms = summary.atom_count > 0;

  return (
    <div className="space-y-6">
      {/* Status card */}
      <div className="bg-surface border border-border rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-4">
          Atom Generation
        </h3>
        <p className="text-sm text-text-secondary mb-6">
          Generate learning atoms from standards using Gemini.
          Each standard is decomposed into granular, assessable
          learning units.
        </p>

        {/* Current stats */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="bg-background rounded-lg p-4 text-center">
            <Database className="w-5 h-5 text-accent mx-auto mb-2" />
            <div className="text-2xl font-bold">
              {summary.atom_count}
            </div>
            <div className="text-xs text-text-secondary mt-1">
              Total Atoms
            </div>
          </div>
          <div className="bg-background rounded-lg p-4 text-center">
            <Sparkles className="w-5 h-5 text-accent mx-auto mb-2" />
            <div className="text-2xl font-bold">
              {summary.standards_count}
            </div>
            <div className="text-xs text-text-secondary mt-1">
              Standards
            </div>
          </div>
          <div className="bg-background rounded-lg p-4 text-center">
            <Calendar className="w-5 h-5 text-accent mx-auto mb-2" />
            <div className="text-sm font-mono font-bold mt-1">
              {summary.last_generation_date || "—"}
            </div>
            <div className="text-xs text-text-secondary mt-1">
              Last Generated
            </div>
          </div>
        </div>

        {/* CTA */}
        {!summary.has_standards ? (
          <div className="text-sm text-text-secondary bg-background rounded-lg p-4">
            No standards file found. Generate standards from
            temario first.
          </div>
        ) : (
          <button
            onClick={onRunGeneration}
            className="flex items-center gap-2 px-5 py-2.5 bg-accent text-white rounded-lg text-sm font-medium hover:bg-accent/90 transition-colors"
          >
            <Sparkles className="w-4 h-4" />
            {hasAtoms ? "Re-generate Atoms" : "Generate Atoms"}
          </button>
        )}
      </div>

      {/* Info card */}
      {hasAtoms && (
        <div className="bg-surface border border-border rounded-lg p-6">
          <h4 className="text-sm font-semibold mb-2">
            About Re-generation
          </h4>
          <p className="text-sm text-text-secondary">
            Re-generating atoms will overwrite the current atoms
            file. Use the optional eje and standard ID filters in
            the generation modal to regenerate specific subsets.
            Validation results will need to be re-run after
            regeneration.
          </p>
        </div>
      )}
    </div>
  );
}
