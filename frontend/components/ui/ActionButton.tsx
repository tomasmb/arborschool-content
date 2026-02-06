"use client";

import { forwardRef } from "react";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Shared button component with consistent styling across all tabs.
 * Supports primary, secondary, warning, and danger variants.
 */

export type ActionButtonVariant =
  | "primary"
  | "secondary"
  | "warning"
  | "danger"
  | "ghost";

export type ActionButtonSize = "sm" | "md" | "lg";

export interface ActionButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ActionButtonVariant;
  size?: ActionButtonSize;
  icon?: React.ReactNode;
  loading?: boolean;
}

const variantStyles: Record<ActionButtonVariant, string> = {
  primary: [
    "bg-accent text-white",
    "hover:bg-accent/90",
    "border border-accent/50",
  ].join(" "),
  secondary: [
    "bg-surface text-text-primary",
    "hover:bg-white/10",
    "border border-border",
  ].join(" "),
  warning: [
    "bg-warning/10 text-warning",
    "hover:bg-warning/20",
    "border border-warning/20",
  ].join(" "),
  danger: [
    "bg-error/10 text-error",
    "hover:bg-error/20",
    "border border-error/20",
  ].join(" "),
  ghost: [
    "text-text-secondary",
    "hover:text-text-primary hover:bg-white/5",
    "border border-transparent",
  ].join(" "),
};

const sizeStyles: Record<ActionButtonSize, string> = {
  sm: "px-2.5 py-1.5 text-xs gap-1.5",
  md: "px-3 py-2 text-sm gap-2",
  lg: "px-4 py-2.5 text-sm gap-2",
};

export const ActionButton = forwardRef<
  HTMLButtonElement,
  ActionButtonProps
>(function ActionButton(
  {
    variant = "secondary",
    size = "md",
    icon,
    loading = false,
    disabled,
    className,
    children,
    ...props
  },
  ref,
) {
  return (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={cn(
        "inline-flex items-center justify-center",
        "rounded-lg font-medium transition-colors",
        "disabled:opacity-50 disabled:cursor-not-allowed",
        variantStyles[variant],
        sizeStyles[size],
        className,
      )}
      {...props}
    >
      {loading ? (
        <Loader2 className="w-4 h-4 animate-spin" />
      ) : (
        icon
      )}
      {children}
    </button>
  );
});
