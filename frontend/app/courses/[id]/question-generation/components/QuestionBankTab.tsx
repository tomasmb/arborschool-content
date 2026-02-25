"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Library,
  CheckCircle2,
  XCircle,
  Clock,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { getAllQuestions } from "@/lib/api";
import type {
  QuestionBankResponse,
  QuestionBankItem,
} from "@/lib/api-types-question-gen";
import {
  QuestionPreviewCard,
  type QuestionPreviewItem,
} from "@/components/questions/QuestionPreviewCard";
import {
  FilterBar,
  BankPagination,
  type StatusFilter,
} from "./QuestionBankFilters";

const PAGE_SIZE = 20;

// -----------------------------------------------------------------------------
// Main component
// -----------------------------------------------------------------------------

export function QuestionBankTab() {
  const [data, setData] = useState<QuestionBankResponse | null>(
    null,
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [ejeFilter, setEjeFilter] = useState("all");
  const [diffFilter, setDiffFilter] = useState("all");
  const [statusFilter, setStatusFilter] =
    useState<StatusFilter>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [page, setPage] = useState(0);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getAllQuestions({
        eje: ejeFilter !== "all" ? ejeFilter : undefined,
        difficulty:
          diffFilter !== "all" ? diffFilter : undefined,
        status:
          statusFilter !== "all" ? statusFilter : undefined,
        search: searchQuery || undefined,
        offset: page * PAGE_SIZE,
        limit: PAGE_SIZE,
      });
      setData(result);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to load questions",
      );
    } finally {
      setLoading(false);
    }
  }, [ejeFilter, diffFilter, statusFilter, searchQuery, page]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const resetAndFetch = useCallback(() => {
    setPage(0);
  }, []);

  const totalPages = data
    ? Math.max(1, Math.ceil(data.total / PAGE_SIZE))
    : 1;

  return (
    <div className="space-y-5">
      {/* Summary stats */}
      {data && !loading && (
        <StatusSummaryBar counts={data.status_counts} />
      )}

      {/* Filter bar */}
      <FilterBar
        ejes={data?.filters.ejes ?? []}
        difficulties={data?.filters.difficulties ?? []}
        ejeFilter={ejeFilter}
        diffFilter={diffFilter}
        statusFilter={statusFilter}
        searchQuery={searchQuery}
        onEjeChange={(v) => {
          setEjeFilter(v);
          resetAndFetch();
        }}
        onDiffChange={(v) => {
          setDiffFilter(v);
          resetAndFetch();
        }}
        onStatusChange={(v) => {
          setStatusFilter(v);
          resetAndFetch();
        }}
        onSearchChange={setSearchQuery}
        onSearchSubmit={resetAndFetch}
      />

      {/* Loading / error / content */}
      {loading && (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="w-6 h-6 animate-spin text-accent" />
          <span className="ml-2 text-sm text-text-secondary">
            Loading questions...
          </span>
        </div>
      )}

      {error && (
        <div className="bg-error/10 border border-error/20 rounded-lg p-4 text-sm text-error">
          {error}
        </div>
      )}

      {!loading && !error && data && (
        <>
          {/* Results count */}
          <div className="flex items-center justify-between">
            <span className="text-xs text-text-secondary">
              Showing{" "}
              <span className="font-medium text-text-primary">
                {Math.min(
                  page * PAGE_SIZE + 1,
                  data.total,
                )}
                &ndash;
                {Math.min(
                  (page + 1) * PAGE_SIZE,
                  data.total,
                )}
              </span>{" "}
              of{" "}
              <span className="font-medium text-text-primary">
                {data.total}
              </span>{" "}
              questions
            </span>
          </div>

          {/* Question cards */}
          {data.items.length === 0 ? (
            <EmptyState />
          ) : (
            <div className="space-y-3">
              {data.items.map((item) => (
                <QuestionPreviewCard
                  key={item.item_id}
                  item={bankItemToPreview(item)}
                  showAtomId
                />
              ))}
            </div>
          )}

          {/* Pagination */}
          {data.total > PAGE_SIZE && (
            <BankPagination
              page={page}
              totalPages={totalPages}
              onPageChange={setPage}
            />
          )}
        </>
      )}
    </div>
  );
}

// -----------------------------------------------------------------------------
// Helpers
// -----------------------------------------------------------------------------

function bankItemToPreview(
  item: QuestionBankItem,
): QuestionPreviewItem {
  return {
    item_id: item.item_id,
    atom_id: item.atom_id,
    atom_titulo: item.atom_titulo,
    eje: item.eje,
    qti_xml: item.qti_xml,
    difficulty: item.difficulty,
    context: item.context,
    status: item.status,
    phase: item.phase,
    slot_index: item.slot_index,
  };
}

// -----------------------------------------------------------------------------
// Status summary bar
// -----------------------------------------------------------------------------

function StatusSummaryBar({
  counts,
}: {
  counts: Record<string, number>;
}) {
  const pass = counts.pass ?? 0;
  const fail = counts.fail ?? 0;
  const pending = counts.pending ?? 0;
  const total = pass + fail + pending;
  if (total === 0) return null;

  const pctPass = (pass / total) * 100;
  const pctFail = (fail / total) * 100;

  return (
    <div className="bg-surface border border-border rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Library className="w-4 h-4 text-accent" />
          <span className="text-sm font-semibold">
            Question Bank
          </span>
        </div>
        <span className="text-2xl font-bold">{total}</span>
      </div>

      {/* Stacked bar */}
      <div className="h-2 rounded-full overflow-hidden flex bg-border">
        {pctPass > 0 && (
          <div
            className="bg-success h-full transition-all"
            style={{ width: `${pctPass}%` }}
          />
        )}
        {pctFail > 0 && (
          <div
            className="bg-error h-full transition-all"
            style={{ width: `${pctFail}%` }}
          />
        )}
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 mt-2">
        <LegendItem
          icon={CheckCircle2}
          label="Passed"
          count={pass}
          color="text-success"
        />
        <LegendItem
          icon={XCircle}
          label="Failed"
          count={fail}
          color="text-error"
        />
        <LegendItem
          icon={Clock}
          label="Pending"
          count={pending}
          color="text-text-secondary"
        />
      </div>
    </div>
  );
}

function LegendItem({
  icon: Icon,
  label,
  count,
  color,
}: {
  icon: typeof CheckCircle2;
  label: string;
  count: number;
  color: string;
}) {
  return (
    <div className="flex items-center gap-1.5 text-xs">
      <Icon className={cn("w-3 h-3", color)} />
      <span className="text-text-secondary">{label}</span>
      <span className={cn("font-medium", color)}>{count}</span>
    </div>
  );
}

// -----------------------------------------------------------------------------
// Empty state
// -----------------------------------------------------------------------------

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-text-secondary">
      <Library className="w-8 h-8 mb-2 opacity-30" />
      <p className="text-sm">
        No questions match the current filters
      </p>
    </div>
  );
}
