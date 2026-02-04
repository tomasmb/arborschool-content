"use client";

import { cn } from "@/lib/utils";

export interface ProgressBarProps {
  /** Current value */
  current: number;
  /** Total value */
  total: number;
  /** Show percentage text */
  showPercent?: boolean;
  /** Show ratio text (e.g., "32/45") */
  showRatio?: boolean;
  /** Size variant */
  size?: "sm" | "md" | "lg";
  /** Color variant */
  variant?: "default" | "success" | "warning" | "error" | "accent";
  /** Label to display before the bar */
  label?: string;
  /** Additional class names */
  className?: string;
}

const sizeConfig = {
  sm: { height: "h-1.5", text: "text-xs" },
  md: { height: "h-2", text: "text-sm" },
  lg: { height: "h-3", text: "text-base" },
};

const variantConfig = {
  default: "bg-accent",
  success: "bg-success",
  warning: "bg-warning",
  error: "bg-error",
  accent: "bg-accent",
};

export function ProgressBar({
  current,
  total,
  showPercent = false,
  showRatio = false,
  size = "md",
  variant = "default",
  label,
  className,
}: ProgressBarProps) {
  const percent = total > 0 ? Math.round((current / total) * 100) : 0;
  const sizes = sizeConfig[size];
  const barColor = variantConfig[variant];

  // Auto-color based on completion
  const autoColor =
    percent === 100
      ? "bg-success"
      : percent >= 75
        ? "bg-accent"
        : percent >= 50
          ? "bg-warning"
          : "bg-text-secondary";

  const finalColor = variant === "default" ? autoColor : barColor;

  return (
    <div className={cn("w-full", className)}>
      {(label || showPercent || showRatio) && (
        <div className="flex items-center justify-between mb-1">
          {label && (
            <span className={cn(sizes.text, "text-text-secondary")}>{label}</span>
          )}
          <div className={cn(sizes.text, "text-text-secondary ml-auto")}>
            {showRatio && (
              <span className="mr-2">
                {current}/{total}
              </span>
            )}
            {showPercent && <span>{percent}%</span>}
          </div>
        </div>
      )}
      <div className={cn("w-full bg-border rounded-full overflow-hidden", sizes.height)}>
        <div
          className={cn("h-full rounded-full transition-all duration-300", finalColor)}
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}

/**
 * Compact inline progress bar for tables.
 * Shows a small bar with optional percentage.
 */
export interface InlineProgressProps {
  current: number;
  total: number;
  width?: string;
  className?: string;
}

export function InlineProgress({
  current,
  total,
  width = "w-16",
  className,
}: InlineProgressProps) {
  const percent = total > 0 ? Math.round((current / total) * 100) : 0;
  const isComplete = current === total && total > 0;

  return (
    <div className={cn("flex items-center gap-2", className)}>
      <div className={cn("h-1.5 bg-border rounded-full overflow-hidden", width)}>
        <div
          className={cn(
            "h-full rounded-full transition-all",
            isComplete ? "bg-success" : "bg-accent"
          )}
          style={{ width: `${percent}%` }}
        />
      </div>
      <span className={cn("text-xs", isComplete ? "text-success" : "text-text-secondary")}>
        {percent}%
      </span>
    </div>
  );
}
