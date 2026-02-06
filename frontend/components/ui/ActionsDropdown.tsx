"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { MoreHorizontal } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Dropdown menu for secondary / power-user actions.
 * Keeps the main UI clean by hiding re-run and less common actions.
 */

export interface DropdownAction {
  id: string;
  label: string;
  icon?: React.ReactNode;
  onClick: () => void;
  disabled?: boolean;
  /** Visual emphasis for destructive actions */
  danger?: boolean;
}

export interface ActionsDropdownProps {
  /** Menu items to render */
  actions: DropdownAction[];
  /** Trigger label (defaults to icon-only) */
  label?: string;
  /** Additional class for the trigger button */
  className?: string;
}

export function ActionsDropdown({
  actions,
  label,
  className,
}: ActionsDropdownProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const close = useCallback(() => setOpen(false), []);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        close();
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open, close]);

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") close();
    }
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [open, close]);

  const visibleActions = actions.filter((a) => !a.disabled);
  if (visibleActions.length === 0) return null;

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        className={cn(
          "inline-flex items-center gap-1.5 px-2.5 py-2",
          "rounded-lg text-sm font-medium transition-colors",
          "text-text-secondary hover:text-text-primary",
          "hover:bg-white/5 border border-border",
          className,
        )}
        aria-expanded={open}
        aria-haspopup="menu"
      >
        <MoreHorizontal className="w-4 h-4" />
        {label && <span>{label}</span>}
      </button>

      {open && (
        <div
          role="menu"
          className={cn(
            "absolute right-0 top-full mt-1 z-50",
            "min-w-[180px] py-1",
            "bg-surface border border-border rounded-lg shadow-xl",
            "animate-in fade-in slide-in-from-top-1 duration-150",
          )}
        >
          {actions.map((action) => (
            <button
              key={action.id}
              role="menuitem"
              disabled={action.disabled}
              onClick={() => {
                action.onClick();
                close();
              }}
              className={cn(
                "w-full flex items-center gap-2 px-3 py-2 text-sm",
                "transition-colors text-left",
                "disabled:opacity-40 disabled:cursor-not-allowed",
                action.danger
                  ? "text-error hover:bg-error/10"
                  : "text-text-primary hover:bg-white/5",
              )}
            >
              {action.icon}
              {action.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
