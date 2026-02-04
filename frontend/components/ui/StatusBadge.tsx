"use client";

import { CheckCircle2, Circle, XCircle, Clock, Lock, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";

export type StatusType =
  | "not_started"
  | "in_progress"
  | "complete"
  | "failed"
  | "blocked"
  | "warning"
  | "partial";

export interface StatusBadgeProps {
  status: StatusType;
  label?: string;
  /** Show count like "32/45" */
  count?: { current: number; total: number };
  /** Show percentage */
  showPercent?: boolean;
  /** Size variant */
  size?: "sm" | "md" | "lg";
  /** Additional class names */
  className?: string;
}

const statusConfig: Record<
  StatusType,
  {
    icon: React.ElementType;
    color: string;
    bgColor: string;
    borderColor: string;
    label: string;
  }
> = {
  not_started: {
    icon: Circle,
    color: "text-text-secondary",
    bgColor: "bg-gray-500/10",
    borderColor: "border-gray-500/20",
    label: "Not Started",
  },
  in_progress: {
    icon: Clock,
    color: "text-yellow-400",
    bgColor: "bg-yellow-500/10",
    borderColor: "border-yellow-500/20",
    label: "In Progress",
  },
  complete: {
    icon: CheckCircle2,
    color: "text-success",
    bgColor: "bg-success/10",
    borderColor: "border-success/20",
    label: "Complete",
  },
  failed: {
    icon: XCircle,
    color: "text-error",
    bgColor: "bg-error/10",
    borderColor: "border-error/20",
    label: "Failed",
  },
  blocked: {
    icon: Lock,
    color: "text-text-secondary",
    bgColor: "bg-gray-500/10",
    borderColor: "border-gray-500/20",
    label: "Blocked",
  },
  warning: {
    icon: AlertTriangle,
    color: "text-warning",
    bgColor: "bg-warning/10",
    borderColor: "border-warning/20",
    label: "Warning",
  },
  partial: {
    icon: Clock,
    color: "text-accent",
    bgColor: "bg-accent/10",
    borderColor: "border-accent/20",
    label: "Partial",
  },
};

const sizeConfig = {
  sm: {
    icon: "w-3 h-3",
    text: "text-xs",
    padding: "px-1.5 py-0.5",
    gap: "gap-1",
  },
  md: {
    icon: "w-4 h-4",
    text: "text-sm",
    padding: "px-2 py-1",
    gap: "gap-1.5",
  },
  lg: {
    icon: "w-5 h-5",
    text: "text-base",
    padding: "px-3 py-1.5",
    gap: "gap-2",
  },
};

export function StatusBadge({
  status,
  label,
  count,
  showPercent = false,
  size = "md",
  className,
}: StatusBadgeProps) {
  const config = statusConfig[status];
  const sizes = sizeConfig[size];
  const Icon = config.icon;

  const displayLabel = label ?? config.label;
  const percent =
    count && count.total > 0
      ? Math.round((count.current / count.total) * 100)
      : null;

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md border font-medium",
        config.bgColor,
        config.borderColor,
        sizes.padding,
        sizes.gap,
        sizes.text,
        className
      )}
    >
      <Icon className={cn(sizes.icon, config.color)} />
      {displayLabel && <span className={config.color}>{displayLabel}</span>}
      {count && (
        <span className={config.color}>
          {count.current}/{count.total}
          {showPercent && percent !== null && ` (${percent}%)`}
        </span>
      )}
    </span>
  );
}

/**
 * Simple inline status icon for tables.
 * Uses just the icon without label or badge styling.
 */
export interface StatusIconProps {
  status: StatusType;
  size?: "sm" | "md" | "lg";
  className?: string;
}

export function StatusIcon({ status, size = "md", className }: StatusIconProps) {
  const config = statusConfig[status];
  const sizes = sizeConfig[size];
  const Icon = config.icon;

  return <Icon className={cn(sizes.icon, config.color, className)} />;
}

/**
 * Progress ratio display with optional status coloring.
 * Displays like "32/45" with color based on completion.
 */
export interface ProgressRatioProps {
  current: number;
  total: number;
  /** Show as complete (green) when current === total */
  showCompleteStatus?: boolean;
  size?: "sm" | "md" | "lg";
  className?: string;
}

export function ProgressRatio({
  current,
  total,
  showCompleteStatus = true,
  size = "md",
  className,
}: ProgressRatioProps) {
  const isComplete = current === total && total > 0;
  const sizes = sizeConfig[size];

  return (
    <span
      className={cn(
        sizes.text,
        "font-medium",
        showCompleteStatus && isComplete ? "text-success" : "text-text-secondary",
        className
      )}
    >
      {current}/{total}
    </span>
  );
}
