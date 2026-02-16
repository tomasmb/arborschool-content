"use client";

import {
  Shield,
  BarChart3,
  AlertTriangle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { EnrichmentData } from "@/lib/api-types-question-gen";
import { CollapsibleSection } from "./shared";

interface EnrichmentSectionProps {
  enrichment: EnrichmentData;
}

export function EnrichmentSection({ enrichment }: EnrichmentSectionProps) {
  return (
    <CollapsibleSection
      icon={Shield}
      title="Enrichment"
      subtitle="Phase 1 — scope, difficulty rubric, error families"
    >
      <div className="px-4 pb-4 space-y-6">
        <ScopeSection guardrails={enrichment.scope_guardrails} />
        <DifficultySection rubric={enrichment.difficulty_rubric} />
        <ErrorFamiliesSection families={enrichment.error_families} />
      </div>
    </CollapsibleSection>
  );
}


// ---------------------------------------------------------------------------
// Scope guardrails
// ---------------------------------------------------------------------------

function ScopeSection({
  guardrails,
}: {
  guardrails: EnrichmentData["scope_guardrails"];
}) {
  return (
    <div className="space-y-3">
      <SectionHeading icon={Shield} label="Scope Guardrails" />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <BulletList
          title="In Scope"
          items={guardrails.in_scope}
          variant="success"
        />
        <BulletList
          title="Out of Scope"
          items={guardrails.out_of_scope}
          variant="error"
        />
      </div>
      {guardrails.common_traps.length > 0 && (
        <BulletList
          title="Common Traps"
          items={guardrails.common_traps}
          variant="warning"
        />
      )}
    </div>
  );
}


// ---------------------------------------------------------------------------
// Difficulty rubric
// ---------------------------------------------------------------------------

function DifficultySection({
  rubric,
}: {
  rubric: EnrichmentData["difficulty_rubric"];
}) {
  return (
    <div className="space-y-3">
      <SectionHeading icon={BarChart3} label="Difficulty Rubric" />
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <DifficultyCard level="easy" items={rubric.easy} />
        <DifficultyCard level="medium" items={rubric.medium} />
        <DifficultyCard level="hard" items={rubric.hard} />
      </div>
    </div>
  );
}

function DifficultyCard({
  level,
  items,
}: {
  level: "easy" | "medium" | "hard";
  items: string[];
}) {
  const config = {
    easy: { label: "Easy", cls: "border-success/30 bg-success/5" },
    medium: { label: "Medium", cls: "border-warning/30 bg-warning/5" },
    hard: { label: "Hard", cls: "border-error/30 bg-error/5" },
  }[level];

  return (
    <div
      className={cn(
        "border rounded-lg p-3 space-y-2",
        config.cls,
      )}
    >
      <DifficultyBadge level={level} />
      <ul className="space-y-1">
        {items.map((item, i) => (
          <li key={i} className="text-xs text-text-secondary leading-relaxed">
            &bull; {item}
          </li>
        ))}
      </ul>
    </div>
  );
}


// ---------------------------------------------------------------------------
// Error families
// ---------------------------------------------------------------------------

function ErrorFamiliesSection({
  families,
}: {
  families: EnrichmentData["error_families"];
}) {
  if (families.length === 0) return null;

  return (
    <div className="space-y-3">
      <SectionHeading icon={AlertTriangle} label="Error Families" />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {families.map((fam) => (
          <div
            key={fam.name}
            className="border border-border rounded-lg p-3 space-y-1"
          >
            <h4 className="text-xs font-semibold">
              {fam.name.replace(/_/g, " ")}
            </h4>
            <p className="text-xs text-text-secondary leading-relaxed">
              {fam.description}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}


// ---------------------------------------------------------------------------
// Shared helpers
// ---------------------------------------------------------------------------

function SectionHeading({
  icon: Icon,
  label,
}: {
  icon: typeof Shield;
  label: string;
}) {
  return (
    <div className="flex items-center gap-2 border-b border-border pb-2">
      <Icon className="w-3.5 h-3.5 text-text-secondary" />
      <h3 className="text-xs font-semibold uppercase tracking-wide text-text-secondary">
        {label}
      </h3>
    </div>
  );
}

function BulletList({
  title,
  items,
  variant,
}: {
  title: string;
  items: string[];
  variant: "success" | "error" | "warning";
}) {
  const dotColor = {
    success: "text-success",
    error: "text-error",
    warning: "text-warning",
  }[variant];

  return (
    <div>
      <h4 className="text-xs font-semibold mb-1">{title}</h4>
      <ul className="space-y-1">
        {items.map((item, i) => (
          <li key={i} className="flex gap-1.5 text-xs text-text-secondary leading-relaxed">
            <span className={cn("mt-0.5 flex-shrink-0", dotColor)}>&bull;</span>
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** Reusable difficulty badge. Exported for use in other components. */
export function DifficultyBadge({
  level,
}: {
  level: "easy" | "medium" | "hard" | string;
}) {
  const config: Record<string, { label: string; cls: string }> = {
    easy: { label: "Easy", cls: "bg-success/10 text-success" },
    medium: { label: "Medium", cls: "bg-warning/10 text-warning" },
    hard: { label: "Hard", cls: "bg-error/10 text-error" },
  };
  const c = config[level] ?? { label: level, cls: "bg-white/10 text-text-secondary" };

  return (
    <span
      className={cn(
        "inline-flex px-1.5 py-0.5 rounded text-[10px] font-semibold",
        c.cls,
      )}
    >
      {c.label}
    </span>
  );
}
