"use client";

import { Filter, Search, ImageIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export type StatusFilter = "all" | "pass" | "fail" | "pending";

const STATUS_CHIPS: {
  id: StatusFilter;
  label: string;
  color: string;
  activeColor: string;
}[] = [
  {
    id: "all",
    label: "All",
    color: "text-text-secondary",
    activeColor: "bg-white/10 text-text-primary",
  },
  {
    id: "pass",
    label: "Passed",
    color: "text-success/70",
    activeColor: "bg-success/10 text-success",
  },
  {
    id: "fail",
    label: "Failed",
    color: "text-error/70",
    activeColor: "bg-error/10 text-error",
  },
  {
    id: "pending",
    label: "Pending",
    color: "text-text-secondary",
    activeColor: "bg-white/10 text-text-primary",
  },
];

export interface FilterBarProps {
  ejes: string[];
  difficulties: string[];
  ejeFilter: string;
  diffFilter: string;
  statusFilter: StatusFilter;
  imagesOnly: boolean;
  searchQuery: string;
  onEjeChange: (v: string) => void;
  onDiffChange: (v: string) => void;
  onStatusChange: (v: StatusFilter) => void;
  onImagesOnlyChange: (v: boolean) => void;
  onSearchChange: (v: string) => void;
  onSearchSubmit: () => void;
}

export function FilterBar({
  ejes,
  difficulties,
  ejeFilter,
  diffFilter,
  statusFilter,
  imagesOnly,
  searchQuery,
  onEjeChange,
  onDiffChange,
  onStatusChange,
  onImagesOnlyChange,
  onSearchChange,
  onSearchSubmit,
}: FilterBarProps) {
  return (
    <div
      className={cn(
        "flex flex-wrap items-center gap-3",
        "bg-surface border border-border rounded-lg p-3",
      )}
    >
      <div className="flex items-center gap-1.5">
        {STATUS_CHIPS.map((chip) => (
          <button
            key={chip.id}
            onClick={() => onStatusChange(chip.id)}
            className={cn(
              "px-2.5 py-1 rounded-full text-xs font-medium",
              "transition-all duration-150",
              statusFilter === chip.id
                ? chip.activeColor
                : cn("hover:bg-white/[0.04]", chip.color),
            )}
          >
            {chip.label}
          </button>
        ))}
      </div>

      <div className="w-px h-5 bg-border" />

      <div className="flex items-center gap-2">
        <Filter className="w-3.5 h-3.5 text-text-secondary" />
        <DropdownFilter
          value={ejeFilter}
          onChange={onEjeChange}
          options={ejes}
          allLabel="All ejes"
          formatter={formatEje}
        />
        <DropdownFilter
          value={diffFilter}
          onChange={onDiffChange}
          options={difficulties}
          allLabel="All difficulties"
          formatter={capitalize}
        />
        <button
          onClick={() => onImagesOnlyChange(!imagesOnly)}
          className={cn(
            "inline-flex items-center gap-1 px-2.5 py-1",
            "rounded-full text-xs font-medium",
            "transition-all duration-150",
            imagesOnly
              ? "bg-accent/15 text-accent"
              : "text-text-secondary hover:bg-white/[0.04]",
          )}
        >
          <ImageIcon className="w-3 h-3" />
          Images
        </button>
      </div>

      <div className="flex-1" />

      <div className="relative">
        <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-text-secondary" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && onSearchSubmit()}
          placeholder="Search atom ID..."
          className={cn(
            "bg-surface border border-border rounded-md",
            "pl-8 pr-3 py-1.5 text-xs text-text-primary",
            "placeholder:text-text-secondary/50",
            "focus:outline-none focus:ring-1 focus:ring-accent/50",
            "w-[180px]",
          )}
        />
      </div>
    </div>
  );
}

function DropdownFilter({
  value,
  onChange,
  options,
  allLabel,
  formatter,
}: {
  value: string;
  onChange: (v: string) => void;
  options: string[];
  allLabel: string;
  formatter?: (v: string) => string;
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
          {formatter ? formatter(opt) : opt}
        </option>
      ))}
    </select>
  );
}

function formatEje(eje: string): string {
  return eje
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

export function BankPagination({
  page,
  totalPages,
  onPageChange,
}: {
  page: number;
  totalPages: number;
  onPageChange: (p: number) => void;
}) {
  return (
    <div className="flex items-center justify-center gap-1 py-3">
      <PgBtn
        onClick={() => onPageChange(page - 1)}
        disabled={page === 0}
      >
        Prev
      </PgBtn>
      {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => {
        const p = getPageNum(i, page, totalPages);
        if (p === -1) {
          return (
            <span
              key={`e${i}`}
              className="px-1 text-xs text-text-secondary"
            >
              &hellip;
            </span>
          );
        }
        return (
          <PgBtn
            key={p}
            onClick={() => onPageChange(p)}
            active={p === page}
          >
            {p + 1}
          </PgBtn>
        );
      })}
      <PgBtn
        onClick={() => onPageChange(page + 1)}
        disabled={page >= totalPages - 1}
      >
        Next
      </PgBtn>
    </div>
  );
}

function PgBtn({
  children,
  onClick,
  disabled,
  active,
}: {
  children: React.ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  active?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "min-w-[32px] h-8 px-2 rounded text-xs font-medium",
        "transition-all duration-150",
        active
          ? "bg-accent text-white shadow-sm shadow-accent/20"
          : disabled
            ? "text-text-secondary/30 cursor-not-allowed"
            : "text-text-secondary hover:bg-white/[0.06]"
              + " hover:text-text-primary",
      )}
    >
      {children}
    </button>
  );
}

function getPageNum(
  idx: number,
  current: number,
  total: number,
): number {
  if (total <= 7) return idx;
  if (idx === 0) return 0;
  if (idx === 6) return total - 1;
  if (current <= 2) return idx;
  if (current >= total - 3) return total - 6 + idx;
  if (idx === 1 && current > 3) return -1;
  if (idx === 5 && current < total - 4) return -1;
  return current - 3 + idx;
}
