"use client";

import { useState, useCallback, ReactNode } from "react";
import { ChevronRight, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

// -----------------------------------------------------------------------------
// Types
// -----------------------------------------------------------------------------

export interface ExpandableRowProps {
  /** Unique identifier for the row */
  id: string;
  /** Content to render in the main row */
  children: ReactNode;
  /** Content to render in the expanded detail section */
  expandedContent: ReactNode;
  /** Whether the row is initially expanded */
  defaultExpanded?: boolean;
  /** Controlled expanded state */
  expanded?: boolean;
  /** Callback when expanded state changes */
  onExpandedChange?: (expanded: boolean) => void;
  /** Additional class names for the row */
  className?: string;
  /** Additional class names for the expanded content */
  expandedClassName?: string;
  /** Show expand icon on the left */
  showExpandIcon?: boolean;
  /** Animation duration in ms */
  animationDuration?: number;
}

// -----------------------------------------------------------------------------
// Component
// -----------------------------------------------------------------------------

export function ExpandableRow({
  id,
  children,
  expandedContent,
  defaultExpanded = false,
  expanded: controlledExpanded,
  onExpandedChange,
  className,
  expandedClassName,
  showExpandIcon = true,
  animationDuration = 200,
}: ExpandableRowProps) {
  const [internalExpanded, setInternalExpanded] = useState(defaultExpanded);

  const isControlled = controlledExpanded !== undefined;
  const isExpanded = isControlled ? controlledExpanded : internalExpanded;

  const handleToggle = useCallback(() => {
    if (isControlled) {
      onExpandedChange?.(!controlledExpanded);
    } else {
      setInternalExpanded((prev) => !prev);
    }
  }, [isControlled, controlledExpanded, onExpandedChange]);

  return (
    <>
      {/* Main row */}
      <tr
        className={cn(
          "border-b border-border hover:bg-white/5 transition-colors cursor-pointer",
          isExpanded && "bg-white/5",
          className
        )}
        onClick={handleToggle}
      >
        {showExpandIcon && (
          <td className="w-8 px-2">
            <span className="inline-flex items-center justify-center w-5 h-5 rounded hover:bg-white/10">
              {isExpanded ? (
                <ChevronDown className="w-4 h-4 text-text-secondary" />
              ) : (
                <ChevronRight className="w-4 h-4 text-text-secondary" />
              )}
            </span>
          </td>
        )}
        {children}
      </tr>

      {/* Expanded content row */}
      {isExpanded && (
        <tr className="bg-background/50">
          <td
            colSpan={100}
            className={cn("p-0", expandedClassName)}
            style={{
              animation: `expandRow ${animationDuration}ms ease-out`,
            }}
          >
            <div className="p-4 border-b border-border">{expandedContent}</div>
          </td>
        </tr>
      )}

      <style jsx>{`
        @keyframes expandRow {
          from {
            opacity: 0;
            transform: translateY(-10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>
    </>
  );
}

// -----------------------------------------------------------------------------
// Expandable Table - Wrapper for tables with expandable rows
// -----------------------------------------------------------------------------

export interface Column<T> {
  id: string;
  header: string;
  accessor: (item: T) => ReactNode;
  className?: string;
  headerClassName?: string;
}

export interface ExpandableTableProps<T> {
  /** Array of items to display */
  data: T[];
  /** Column definitions */
  columns: Column<T>[];
  /** Get unique key for each row */
  getRowKey: (item: T) => string;
  /** Render expanded content for a row */
  renderExpanded: (item: T) => ReactNode;
  /** IDs of currently expanded rows (controlled mode) */
  expandedIds?: Set<string>;
  /** Callback when expansion changes (controlled mode) */
  onExpandedChange?: (ids: Set<string>) => void;
  /** Allow multiple rows expanded at once */
  allowMultiple?: boolean;
  /** Show expand icon column */
  showExpandIcon?: boolean;
  /** Table class name */
  className?: string;
  /** Empty state message */
  emptyMessage?: string;
}

export function ExpandableTable<T>({
  data,
  columns,
  getRowKey,
  renderExpanded,
  expandedIds: controlledIds,
  onExpandedChange,
  allowMultiple = true,
  showExpandIcon = true,
  className,
  emptyMessage = "No items to display",
}: ExpandableTableProps<T>) {
  const [internalIds, setInternalIds] = useState<Set<string>>(new Set());

  const isControlled = controlledIds !== undefined;
  const expandedIds = isControlled ? controlledIds : internalIds;

  const handleToggle = useCallback(
    (id: string) => {
      const newIds = new Set(expandedIds);

      if (newIds.has(id)) {
        newIds.delete(id);
      } else {
        if (!allowMultiple) {
          newIds.clear();
        }
        newIds.add(id);
      }

      if (isControlled) {
        onExpandedChange?.(newIds);
      } else {
        setInternalIds(newIds);
      }
    },
    [expandedIds, allowMultiple, isControlled, onExpandedChange]
  );

  if (data.length === 0) {
    return (
      <div className="text-center py-8 text-text-secondary">{emptyMessage}</div>
    );
  }

  return (
    <div className={cn("bg-surface border border-border rounded-lg overflow-hidden", className)}>
      <table className="w-full">
        <thead>
          <tr className="border-b border-border text-left text-xs text-text-secondary uppercase tracking-wide">
            {showExpandIcon && <th className="w-8 px-2"></th>}
            {columns.map((col) => (
              <th key={col.id} className={cn("px-4 py-3 font-medium", col.headerClassName)}>
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((item) => {
            const key = getRowKey(item);
            const isExpanded = expandedIds.has(key);

            return (
              <ExpandableRow
                key={key}
                id={key}
                expanded={isExpanded}
                onExpandedChange={() => handleToggle(key)}
                showExpandIcon={showExpandIcon}
                expandedContent={renderExpanded(item)}
              >
                {columns.map((col) => (
                  <td key={col.id} className={cn("px-4 py-3", col.className)}>
                    {col.accessor(item)}
                  </td>
                ))}
              </ExpandableRow>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// -----------------------------------------------------------------------------
// Simple expandable section (not in a table)
// -----------------------------------------------------------------------------

export interface ExpandableSectionProps {
  /** Header content */
  header: ReactNode;
  /** Expanded content */
  children: ReactNode;
  /** Whether initially expanded */
  defaultExpanded?: boolean;
  /** Controlled expanded state */
  expanded?: boolean;
  /** Callback when expanded state changes */
  onExpandedChange?: (expanded: boolean) => void;
  /** Additional class names */
  className?: string;
  /** Header class names */
  headerClassName?: string;
}

export function ExpandableSection({
  header,
  children,
  defaultExpanded = false,
  expanded: controlledExpanded,
  onExpandedChange,
  className,
  headerClassName,
}: ExpandableSectionProps) {
  const [internalExpanded, setInternalExpanded] = useState(defaultExpanded);

  const isControlled = controlledExpanded !== undefined;
  const isExpanded = isControlled ? controlledExpanded : internalExpanded;

  const handleToggle = useCallback(() => {
    if (isControlled) {
      onExpandedChange?.(!controlledExpanded);
    } else {
      setInternalExpanded((prev) => !prev);
    }
  }, [isControlled, controlledExpanded, onExpandedChange]);

  return (
    <div className={cn("border border-border rounded-lg overflow-hidden", className)}>
      <button
        type="button"
        onClick={handleToggle}
        className={cn(
          "w-full flex items-center gap-2 px-4 py-3 text-left",
          "bg-surface hover:bg-white/5 transition-colors",
          headerClassName
        )}
      >
        {isExpanded ? (
          <ChevronDown className="w-4 h-4 text-text-secondary shrink-0" />
        ) : (
          <ChevronRight className="w-4 h-4 text-text-secondary shrink-0" />
        )}
        <div className="flex-1">{header}</div>
      </button>

      {isExpanded && (
        <div
          className="border-t border-border bg-background/50"
          style={{
            animation: "expandSection 200ms ease-out",
          }}
        >
          {children}
        </div>
      )}

      <style jsx>{`
        @keyframes expandSection {
          from {
            opacity: 0;
            max-height: 0;
          }
          to {
            opacity: 1;
            max-height: 1000px;
          }
        }
      `}</style>
    </div>
  );
}
