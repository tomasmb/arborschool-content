"use client";

import { ArrowRight, CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { ActionButton } from "./ActionButton";

/**
 * Contextual banner that guides the user to the next workflow step.
 * Shows when a phase is complete and another action is available.
 */

export interface StepBannerProps {
  /** "complete" shows a success message, "action" shows a CTA */
  variant: "complete" | "action";
  /** Short message describing the state */
  message: string;
  /** CTA button label (only for "action" variant) */
  actionLabel?: string;
  /** CTA handler */
  onAction?: () => void;
  className?: string;
}

export function StepBanner({
  variant,
  message,
  actionLabel,
  onAction,
  className,
}: StepBannerProps) {
  const isComplete = variant === "complete";

  return (
    <div
      className={cn(
        "flex items-center justify-between gap-4 px-4 py-3 rounded-lg",
        isComplete
          ? "bg-success/10 border border-success/20"
          : "bg-accent/10 border border-accent/20",
        className,
      )}
    >
      <div className="flex items-center gap-2 text-sm">
        {isComplete && (
          <CheckCircle2 className="w-4 h-4 text-success shrink-0" />
        )}
        <span className={isComplete ? "text-success" : "text-accent"}>
          {message}
        </span>
      </div>

      {actionLabel && onAction && (
        <ActionButton
          variant="primary"
          size="sm"
          icon={<ArrowRight className="w-3.5 h-3.5" />}
          onClick={onAction}
        >
          {actionLabel}
        </ActionButton>
      )}
    </div>
  );
}
