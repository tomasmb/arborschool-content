"use client";

import { useEffect, useMemo, useState } from "react";
import {
  FileText,
  Filter,
  CheckCircle2,
  XCircle,
  Clock,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type {
  GeneratedItem,
  PlanSlot,
} from "@/lib/api-types-question-gen";
import {
  ProPagination,
  getOverallStatus,
  formatContext,
  type OverallStatus,
} from "./shared";
import { QuestionCardDetail } from "./QuestionCardDetail";

// ---------------------------------------------------------------------------
// Types & constants
// ---------------------------------------------------------------------------

const DEFAULT_PAGE_SIZE = 10;

type StatusFilter = "all" | "pass" | "fail" | "pending";

interface QuestionCardsProps {
  items: GeneratedItem[];
  planSlots: PlanSlot[] | null;
  sectionTitle?: string;
  hasValidation: boolean;
  passedIds: Set<string>;
  /** Increment to programmatically switch filter to "fail". */
  filterFailedTrigger?: number;
  /** Atom ID — passed to cards for per-item revalidation. */
  atomId?: string;
  /** Called after a card finishes revalidation (silent refresh). */
  onItemRevalidated?: () => void;
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function QuestionCards({
  items,
  planSlots,
  sectionTitle = "Questions",
  hasValidation,
  passedIds,
  filterFailedTrigger = 0,
  atomId,
  onItemRevalidated,
}: QuestionCardsProps) {
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [diffFilter, setDiffFilter] = useState("all");
  const [contextFilter, setContextFilter] = useState("all");

  // React to external "show failed" trigger
  useEffect(() => {
    if (filterFailedTrigger > 0) {
      setStatusFilter("fail");
      setPage(0);
    }
  }, [filterFailedTrigger]);

  // Build plan slot lookup by slot_index
  const slotMap = useMemo(() => {
    const map = new Map<number, PlanSlot>();
    if (planSlots) {
      for (const slot of planSlots) map.set(slot.slot_index, slot);
    }
    return map;
  }, [planSlots]);

  // Compute status for each item
  const itemsWithStatus = useMemo(
    () =>
      items.map((item) => ({
        item,
        status: computeStatus(item, hasValidation, passedIds),
      })),
    [items, hasValidation, passedIds],
  );

  // Unique filter values
  const difficulties = useMemo(
    () =>
      Array.from(new Set(items.map((i) => i.pipeline_meta.difficulty_level)))
        .sort(),
    [items],
  );
  const contexts = useMemo(
    () =>
      Array.from(new Set(items.map((i) => i.pipeline_meta.surface_context)))
        .sort(),
    [items],
  );

  // Status counts for chips
  const statusCounts = useMemo(() => {
    const c = { all: items.length, pass: 0, fail: 0, pending: 0 };
    for (const { status } of itemsWithStatus) c[status]++;
    return c;
  }, [itemsWithStatus, items.length]);

  // Apply all filters
  const filtered = useMemo(() => {
    let result = itemsWithStatus;
    if (statusFilter !== "all") {
      result = result.filter((r) => r.status === statusFilter);
    }
    if (diffFilter !== "all") {
      result = result.filter(
        (r) => r.item.pipeline_meta.difficulty_level === diffFilter,
      );
    }
    if (contextFilter !== "all") {
      result = result.filter(
        (r) => r.item.pipeline_meta.surface_context === contextFilter,
      );
    }
    return result;
  }, [itemsWithStatus, statusFilter, diffFilter, contextFilter]);

  // Paginate
  const totalPages = Math.max(
    1,
    Math.ceil(filtered.length / pageSize),
  );
  const safePage = Math.min(page, totalPages - 1);
  const pageItems = filtered.slice(
    safePage * pageSize,
    (safePage + 1) * pageSize,
  );

  const resetPage = () => setPage(0);

  return (
    <div className="space-y-4">
      {/* Section header */}
      <div className="flex items-center gap-2">
        <FileText className="w-4 h-4 text-accent" />
        <h2 className="text-sm font-semibold">{sectionTitle}</h2>
        <span className="text-xs text-text-secondary">
          {filtered.length} of {items.length}
        </span>
      </div>

      {/* Filter bar */}
      <div
        className={cn(
          "flex items-center justify-between flex-wrap gap-3",
        )}
      >
        {/* Status chips */}
        <div className="flex items-center gap-1.5">
          {(
            ["all", "pass", "fail", "pending"] as StatusFilter[]
          ).map((s) => (
            <StatusChip
              key={s}
              status={s}
              count={statusCounts[s]}
              active={statusFilter === s}
              onClick={() => {
                setStatusFilter(s);
                resetPage();
              }}
            />
          ))}
        </div>

        {/* Dropdown filters */}
        <div className="flex items-center gap-2">
          <Filter className="w-3.5 h-3.5 text-text-secondary" />
          <FilterSelect
            value={diffFilter}
            onChange={(v) => { setDiffFilter(v); resetPage(); }}
            options={difficulties}
            allLabel="All difficulties"
          />
          <FilterSelect
            value={contextFilter}
            onChange={(v) => { setContextFilter(v); resetPage(); }}
            options={contexts}
            allLabel="All contexts"
          />
        </div>
      </div>

      {/* Question cards */}
      <div className="space-y-3">
        {pageItems.length === 0 ? (
          <EmptyState filter={statusFilter} />
        ) : (
          pageItems.map(({ item, status }) => (
            <QuestionCardDetail
              key={item.item_id}
              item={item}
              status={status}
              planSlot={slotMap.get(item.slot_index) ?? null}
              atomId={atomId}
              onRevalidated={onItemRevalidated}
            />
          ))
        )}
      </div>

      {/* Pro pagination */}
      {filtered.length > pageSize && (
        <ProPagination
          page={safePage}
          totalPages={totalPages}
          totalItems={filtered.length}
          pageSize={pageSize}
          onPageChange={setPage}
          onPageSizeChange={(size) => {
            setPageSize(size);
            setPage(0);
          }}
        />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Status computation
// ---------------------------------------------------------------------------

function computeStatus(
  item: GeneratedItem,
  hasValidation: boolean,
  passedIds: Set<string>,
): OverallStatus {
  if (hasValidation) {
    return passedIds.has(item.item_id) ? "pass" : "fail";
  }
  return getOverallStatus(item.pipeline_meta.validators);
}

// ---------------------------------------------------------------------------
// Status filter chip
// ---------------------------------------------------------------------------

const CHIP_CONFIG: Record<
  StatusFilter,
  {
    label: string;
    color: string;
    activeColor: string;
    Icon: typeof CheckCircle2 | null;
  }
> = {
  all: {
    label: "All",
    color: "text-text-secondary",
    activeColor: "bg-white/10 text-text-primary",
    Icon: null,
  },
  pass: {
    label: "Passed",
    color: "text-success/70",
    activeColor: "bg-success/10 text-success",
    Icon: CheckCircle2,
  },
  fail: {
    label: "Failed",
    color: "text-error/70",
    activeColor: "bg-error/10 text-error",
    Icon: XCircle,
  },
  pending: {
    label: "Pending",
    color: "text-text-secondary",
    activeColor: "bg-white/10 text-text-primary",
    Icon: Clock,
  },
};

function StatusChip({
  status,
  count,
  active,
  onClick,
}: {
  status: StatusFilter;
  count: number;
  active: boolean;
  onClick: () => void;
}) {
  const c = CHIP_CONFIG[status];

  return (
    <button
      onClick={onClick}
      className={cn(
        "inline-flex items-center gap-1.5",
        "px-2.5 py-1 rounded-full text-xs font-medium",
        "transition-all duration-150",
        active ? c.activeColor : cn("hover:bg-white/[0.04]", c.color),
      )}
    >
      {c.Icon && <c.Icon className="w-3 h-3" />}
      {c.label}
      <span
        className={cn(
          "ml-0.5 text-[10px]",
          active ? "opacity-80" : "opacity-50",
        )}
      >
        {count}
      </span>
    </button>
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
// Empty state
// ---------------------------------------------------------------------------

function EmptyState({ filter }: { filter: StatusFilter }) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center",
        "py-12 text-text-secondary",
      )}
    >
      <FileText className="w-8 h-8 mb-2 opacity-30" />
      <p className="text-sm">
        {filter === "all"
          ? "No questions generated yet"
          : `No ${filter} questions`}
      </p>
    </div>
  );
}
