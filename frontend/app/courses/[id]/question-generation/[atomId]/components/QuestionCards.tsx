"use client";

import { useMemo, useState } from "react";
import {
  ChevronLeft,
  ChevronRight,
  Filter,
  FileText,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { QTIRenderer } from "@/components/qti/QTIRenderer";
import type {
  GeneratedItem,
  PlanSlot,
  ValidatorStatuses,
} from "@/lib/api-types-question-gen";
import { DifficultyBadge } from "./EnrichmentSection";
import { formatTag, formatContext } from "./shared";

const PAGE_SIZE = 10;

interface QuestionCardsProps {
  items: GeneratedItem[];
  planSlots: PlanSlot[] | null;
  sectionTitle?: string;
}

export function QuestionCards({
  items,
  planSlots,
  sectionTitle = "Generated Questions",
}: QuestionCardsProps) {
  const [page, setPage] = useState(0);
  const [diffFilter, setDiffFilter] = useState<string>("all");
  const [contextFilter, setContextFilter] = useState<string>("all");

  // Build plan slot lookup by index
  const slotMap = useMemo(() => {
    const map = new Map<number, PlanSlot>();
    if (planSlots) {
      for (const slot of planSlots) map.set(slot.slot_index, slot);
    }
    return map;
  }, [planSlots]);

  // Collect unique filter values
  const difficulties = useMemo(
    () => Array.from(new Set(items.map((i) => i.pipeline_meta.difficulty_level))).sort(),
    [items],
  );
  const contexts = useMemo(
    () => Array.from(new Set(items.map((i) => i.pipeline_meta.surface_context))).sort(),
    [items],
  );

  // Apply filters
  const filtered = useMemo(() => {
    let result = items;
    if (diffFilter !== "all") {
      result = result.filter(
        (i) => i.pipeline_meta.difficulty_level === diffFilter,
      );
    }
    if (contextFilter !== "all") {
      result = result.filter(
        (i) => i.pipeline_meta.surface_context === contextFilter,
      );
    }
    return result;
  }, [items, diffFilter, contextFilter]);

  // Paginate
  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages - 1);
  const pageItems = filtered.slice(
    safePage * PAGE_SIZE,
    (safePage + 1) * PAGE_SIZE,
  );

  // Reset page when filters change
  const handleDiffChange = (v: string) => { setDiffFilter(v); setPage(0); };
  const handleCtxChange = (v: string) => { setContextFilter(v); setPage(0); };

  return (
    <div className="space-y-4">
      {/* Header + filters */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-accent" />
          <h2 className="text-sm font-semibold">
            {sectionTitle}
          </h2>
          <span className="text-xs text-text-secondary">
            {filtered.length} of {items.length}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Filter className="w-3.5 h-3.5 text-text-secondary" />
          <FilterSelect
            value={diffFilter}
            onChange={handleDiffChange}
            options={difficulties}
            allLabel="All difficulties"
          />
          <FilterSelect
            value={contextFilter}
            onChange={handleCtxChange}
            options={contexts}
            allLabel="All contexts"
          />
        </div>
      </div>

      {/* Question cards */}
      <div className="space-y-4">
        {pageItems.map((item) => (
          <QuestionCard
            key={item.item_id}
            item={item}
            planSlot={slotMap.get(item.slot_index) ?? null}
          />
        ))}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <Pagination
          page={safePage}
          totalPages={totalPages}
          onPageChange={setPage}
        />
      )}
    </div>
  );
}


// ---------------------------------------------------------------------------
// Single question card
// ---------------------------------------------------------------------------

function QuestionCard({
  item,
  planSlot,
}: {
  item: GeneratedItem;
  planSlot: PlanSlot | null;
}) {
  const meta = item.pipeline_meta;

  return (
    <div
      id={`question-${item.slot_index}`}
      className={cn(
        "bg-surface border border-border rounded-lg",
        "transition-all duration-300",
      )}
    >
      {/* Card header */}
      <div className="px-4 py-2 border-b border-border flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-text-secondary">
            {item.item_id}
          </span>
          <DifficultyBadge level={meta.difficulty_level} />
          <span className="text-[10px] text-text-secondary">
            slot {item.slot_index}
          </span>
        </div>
        <ValidatorPills validators={meta.validators} />
      </div>

      {/* Two-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-0">
        {/* Left: Plan metadata */}
        <div className="p-4 border-b lg:border-b-0 lg:border-r border-border space-y-2">
          <h3 className="text-[11px] font-semibold uppercase tracking-wide text-text-secondary mb-2">
            Plan Spec
          </h3>
          <MetaRow label="Component" value={formatTag(meta.component_tag)} />
          <MetaRow label="Skeleton" value={meta.operation_skeleton_ast} mono />
          <MetaRow label="Context" value={formatContext(meta.surface_context)} />
          <MetaRow label="Numbers" value={formatContext(meta.numbers_profile)} />
          {meta.target_exemplar_id && (
            <MetaRow label="Exemplar" value={meta.target_exemplar_id} />
          )}
          {meta.distance_level && (
            <MetaRow label="Distance" value={meta.distance_level} />
          )}
          {planSlot?.image_required && (
            <MetaRow
              label="Image"
              value={planSlot.image_type ?? "required"}
            />
          )}
        </div>

        {/* Right: QTI preview */}
        <div className="lg:col-span-2 p-4">
          <QTIRenderer
            qtiXml={item.qti_xml}
            showCorrectAnswer={true}
            showFeedback={false}
            showWorkedSolution={false}
            size="sm"
          />
        </div>
      </div>
    </div>
  );
}


// ---------------------------------------------------------------------------
// Validator status pills
// ---------------------------------------------------------------------------

function ValidatorPills({
  validators,
}: {
  validators: ValidatorStatuses;
}) {
  const entries = (
    Object.entries(validators) as [string, string][]
  ).filter(([, v]) => v !== "pending");

  // If all pending, show a single "all pending" indicator
  if (entries.length === 0) {
    return (
      <span className="text-[10px] text-text-secondary">
        validators pending
      </span>
    );
  }

  return (
    <div className="flex items-center gap-1">
      {entries.map(([key, value]) => (
        <span
          key={key}
          className={cn(
            "px-1.5 py-0.5 rounded text-[10px] font-medium",
            value === "pass"
              ? "bg-success/10 text-success"
              : value === "fail"
                ? "bg-error/10 text-error"
                : "bg-white/10 text-text-secondary",
          )}
        >
          {key}
        </span>
      ))}
    </div>
  );
}


// ---------------------------------------------------------------------------
// Metadata row
// ---------------------------------------------------------------------------

function MetaRow({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="flex items-baseline gap-2">
      <span className="text-[11px] text-text-secondary min-w-[70px]">
        {label}
      </span>
      <span
        className={cn(
          "text-xs",
          mono && "font-mono",
        )}
      >
        {value}
      </span>
    </div>
  );
}


// ---------------------------------------------------------------------------
// Filter dropdown
// ---------------------------------------------------------------------------

function FilterSelect({
  value,
  onChange,
  options,
  allLabel,
}: {
  value: string;
  onChange: (v: string) => void;
  options: string[];
  allLabel: string;
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className={cn(
        "bg-surface border border-border rounded px-2 py-1",
        "text-xs text-text-primary",
        "focus:outline-none focus:ring-1 focus:ring-accent/50",
      )}
    >
      <option value="all">{allLabel}</option>
      {options.map((opt) => (
        <option key={opt} value={opt}>
          {formatContext(opt)}
        </option>
      ))}
    </select>
  );
}


// ---------------------------------------------------------------------------
// Pagination
// ---------------------------------------------------------------------------

function Pagination({
  page,
  totalPages,
  onPageChange,
}: {
  page: number;
  totalPages: number;
  onPageChange: (p: number) => void;
}) {
  return (
    <div className="flex items-center justify-center gap-3 py-2">
      <button
        onClick={() => onPageChange(Math.max(0, page - 1))}
        disabled={page === 0}
        className={cn(
          "p-1.5 rounded border border-border transition-colors",
          page === 0
            ? "opacity-40 cursor-not-allowed"
            : "hover:bg-white/5",
        )}
      >
        <ChevronLeft className="w-4 h-4" />
      </button>
      <span className="text-xs text-text-secondary">
        Page {page + 1} of {totalPages}
      </span>
      <button
        onClick={() => onPageChange(Math.min(totalPages - 1, page + 1))}
        disabled={page >= totalPages - 1}
        className={cn(
          "p-1.5 rounded border border-border transition-colors",
          page >= totalPages - 1
            ? "opacity-40 cursor-not-allowed"
            : "hover:bg-white/5",
        )}
      >
        <ChevronRight className="w-4 h-4" />
      </button>
    </div>
  );
}


