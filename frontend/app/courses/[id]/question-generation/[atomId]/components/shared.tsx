"use client";

import { useState, useCallback, type ReactNode } from "react";
import {
  ChevronDown,
  ChevronRight,
  ChevronLeft,
  ChevronsLeft,
  ChevronsRight,
  Check,
  CheckCircle2,
  Clock,
  Copy,
  XCircle,
  type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type {
  GeneratedItem,
  PlanSlot,
  ValidatorStatuses,
} from "@/lib/api-types-question-gen";

// ---------------------------------------------------------------------------
// Collapsible section wrapper
// ---------------------------------------------------------------------------

interface CollapsibleSectionProps {
  icon: LucideIcon;
  title: string;
  subtitle?: string;
  defaultExpanded?: boolean;
  children: ReactNode;
  headerRight?: ReactNode;
}

export function CollapsibleSection({
  icon: Icon,
  title,
  subtitle,
  defaultExpanded = false,
  children,
  headerRight,
}: CollapsibleSectionProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  return (
    <div className="bg-surface border border-border rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className={cn(
          "w-full px-4 py-3 flex items-center justify-between",
          "hover:bg-white/[0.03] transition-colors",
        )}
      >
        <div className="flex items-center gap-2">
          <Icon className="w-4 h-4 text-accent" />
          <h2 className="text-sm font-semibold">{title}</h2>
          {subtitle && (
            <span className="text-xs text-text-secondary">
              {subtitle}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {headerRight}
          {expanded ? (
            <ChevronDown className="w-4 h-4 text-text-secondary" />
          ) : (
            <ChevronRight className="w-4 h-4 text-text-secondary" />
          )}
        </div>
      </button>
      {expanded && children}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Pro Pagination (page pills, page-size selector, range display)
// ---------------------------------------------------------------------------

const PAGE_SIZE_OPTIONS = [10, 25, 50];

interface ProPaginationProps {
  page: number;
  totalPages: number;
  totalItems: number;
  pageSize: number;
  onPageChange: (page: number) => void;
  onPageSizeChange: (size: number) => void;
}

export function ProPagination({
  page,
  totalPages,
  totalItems,
  pageSize,
  onPageChange,
  onPageSizeChange,
}: ProPaginationProps) {
  const start = page * pageSize + 1;
  const end = Math.min((page + 1) * pageSize, totalItems);
  const pageRange = getPageRange(page, totalPages);

  return (
    <div
      className={cn(
        "flex items-center justify-between flex-wrap gap-3",
        "py-3 px-1 border-t border-border",
      )}
    >
      {/* Left: showing X–Y of Z */}
      <div className="text-xs text-text-secondary">
        Showing{" "}
        <span className="font-medium text-text-primary">
          {start}&ndash;{end}
        </span>{" "}
        of{" "}
        <span className="font-medium text-text-primary">
          {totalItems}
        </span>
      </div>

      {/* Center: page pills */}
      <div className="flex items-center gap-0.5">
        <PageBtn
          onClick={() => onPageChange(0)}
          disabled={page === 0}
          aria-label="First page"
        >
          <ChevronsLeft className="w-3.5 h-3.5" />
        </PageBtn>
        <PageBtn
          onClick={() => onPageChange(page - 1)}
          disabled={page === 0}
          aria-label="Previous page"
        >
          <ChevronLeft className="w-3.5 h-3.5" />
        </PageBtn>

        {pageRange.map((p, i) =>
          p === "ellipsis" ? (
            <span
              key={`e-${i}`}
              className="px-1 text-xs text-text-secondary select-none"
            >
              &hellip;
            </span>
          ) : (
            <PageBtn
              key={p}
              onClick={() => onPageChange(p)}
              active={p === page}
            >
              {p + 1}
            </PageBtn>
          ),
        )}

        <PageBtn
          onClick={() => onPageChange(page + 1)}
          disabled={page >= totalPages - 1}
          aria-label="Next page"
        >
          <ChevronRight className="w-3.5 h-3.5" />
        </PageBtn>
        <PageBtn
          onClick={() => onPageChange(totalPages - 1)}
          disabled={page >= totalPages - 1}
          aria-label="Last page"
        >
          <ChevronsRight className="w-3.5 h-3.5" />
        </PageBtn>
      </div>

      {/* Right: per-page selector */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-text-secondary">Per page</span>
        <select
          value={pageSize}
          onChange={(e) => onPageSizeChange(Number(e.target.value))}
          className={cn(
            "bg-surface border border-border rounded px-2 py-1",
            "text-xs text-text-primary",
            "focus:outline-none focus:ring-1 focus:ring-accent/50",
          )}
        >
          {PAGE_SIZE_OPTIONS.map((size) => (
            <option key={size} value={size}>{size}</option>
          ))}
        </select>
      </div>
    </div>
  );
}

function PageBtn({
  children,
  onClick,
  disabled,
  active,
  ...rest
}: {
  children: ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  active?: boolean;
} & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "min-w-[28px] h-7 px-1.5 rounded text-xs font-medium",
        "transition-all duration-150",
        active
          ? "bg-accent text-white shadow-sm shadow-accent/20"
          : disabled
            ? "text-text-secondary/30 cursor-not-allowed"
            : "text-text-secondary hover:bg-white/[0.06]" +
              " hover:text-text-primary",
      )}
      {...rest}
    >
      {children}
    </button>
  );
}

/** Compute page range with ellipsis for large ranges. */
function getPageRange(
  current: number,
  total: number,
): (number | "ellipsis")[] {
  if (total <= 7) {
    return Array.from({ length: total }, (_, i) => i);
  }
  const pages: (number | "ellipsis")[] = [0];
  if (current > 2) pages.push("ellipsis");

  const lo = Math.max(1, current - 1);
  const hi = Math.min(total - 2, current + 1);
  for (let i = lo; i <= hi; i++) pages.push(i);

  if (current < total - 3) pages.push("ellipsis");
  pages.push(total - 1);
  return pages;
}

// ---------------------------------------------------------------------------
// Copy button (with success feedback)
// ---------------------------------------------------------------------------

interface CopyButtonProps {
  text: string;
  label?: string;
  className?: string;
}

export function CopyButton({
  text,
  label = "Copy",
  className,
}: CopyButtonProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [text]);

  return (
    <button
      onClick={handleCopy}
      className={cn(
        "inline-flex items-center gap-1.5 px-2.5 py-1",
        "rounded-md border border-border text-xs",
        "transition-all duration-150",
        copied
          ? "bg-success/10 text-success border-success/30"
          : "text-text-secondary hover:text-text-primary" +
            " hover:bg-white/[0.06]",
        className,
      )}
    >
      {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
      {copied ? "Copied!" : label}
    </button>
  );
}

// ---------------------------------------------------------------------------
// Validation status helpers
// ---------------------------------------------------------------------------

export type OverallStatus = "pass" | "fail" | "pending";

/** Compute overall item status from validator statuses. */
export function getOverallStatus(
  validators: ValidatorStatuses,
): OverallStatus {
  const values = Object.values(validators) as string[];
  if (values.some((v) => v === "fail")) return "fail";
  if (values.every((v) => v === "pending")) return "pending";
  return "pass";
}

// ---------------------------------------------------------------------------
// Formatting helpers
// ---------------------------------------------------------------------------

/** Format "ALGEBRA.TRADUCCION" -> "Traduccion" */
export function formatTag(tag: string): string {
  const parts = tag.split(".");
  const last = parts[parts.length - 1];
  return last.charAt(0) + last.slice(1).toLowerCase();
}

/** Format "pure_math" -> "Pure math" */
export function formatContext(ctx: string): string {
  return ctx
    .replace(/_/g, " ")
    .replace(/^\w/, (c) => c.toUpperCase());
}

// ---------------------------------------------------------------------------
// Metadata row (label: value pair)
// ---------------------------------------------------------------------------

export function MetaRow({
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
      <span className={cn("text-xs", mono && "font-mono")}>
        {value}
      </span>
    </div>
  );
}

const SECTION_LABEL = cn(
  "text-[11px] font-semibold uppercase tracking-wide",
  "text-text-secondary mb-2",
);

export function PlanSpec({
  meta,
  planSlot,
}: {
  meta: GeneratedItem["pipeline_meta"];
  planSlot: PlanSlot | null;
}) {
  return (
    <div>
      <h3 className={SECTION_LABEL}>Plan Spec</h3>
      <div className="space-y-2">
        <MetaRow
          label="Component"
          value={formatTag(meta.component_tag)}
        />
        <MetaRow
          label="Skeleton"
          value={meta.operation_skeleton_ast}
          mono
        />
        <MetaRow
          label="Context"
          value={formatContext(meta.surface_context)}
        />
        <MetaRow
          label="Numbers"
          value={formatContext(meta.numbers_profile)}
        />
        {meta.target_exemplar_id && (
          <MetaRow
            label="Exemplar"
            value={meta.target_exemplar_id}
          />
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
    </div>
  );
}

export function ValidatorBreakdown({
  validators,
}: {
  validators: ValidatorStatuses;
}) {
  return (
    <div className="pt-3 border-t border-border">
      <h3 className={SECTION_LABEL}>Validators</h3>
      <div className="space-y-1.5">
        {(Object.entries(validators) as [string, string][]).map(
          ([key, value]) => {
            const Icon =
              value === "pass"
                ? CheckCircle2
                : value === "fail"
                  ? XCircle
                  : Clock;
            const color =
              value === "pass"
                ? "text-success"
                : value === "fail"
                  ? "text-error"
                  : "text-text-secondary/40";
            return (
              <div
                key={key}
                className="flex items-center justify-between"
              >
                <span className="text-xs text-text-secondary">
                  {key.replace(/_/g, " ")}
                </span>
                <div className="flex items-center gap-1.5">
                  <Icon className={cn("w-3 h-3", color)} />
                  <span
                    className={cn(
                      "text-[10px] font-medium",
                      color,
                    )}
                  >
                    {value}
                  </span>
                </div>
              </div>
            );
          },
        )}
      </div>
    </div>
  );
}

export function XmlViewer({ xml }: { xml: string }) {
  return (
    <div className="border-t border-border">
      <div
        className={cn(
          "px-4 py-2 flex items-center justify-between",
          "bg-white/[0.01]",
        )}
      >
        <h3 className={cn(SECTION_LABEL, "mb-0")}>Raw QTI XML</h3>
        <CopyButton text={xml} label="Copy" />
      </div>
      <div className="max-h-[400px] overflow-auto">
        <pre
          className={cn(
            "px-4 py-3 text-[11px] font-mono",
            "text-text-secondary leading-relaxed",
            "whitespace-pre-wrap break-all",
          )}
        >
          {xml}
        </pre>
      </div>
    </div>
  );
}
