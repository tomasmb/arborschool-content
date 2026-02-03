"use client";

import { AlertTriangle, RefreshCw, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";

interface ErrorMessageProps {
  title?: string;
  message: string;
  onRetry?: () => void;
  variant?: "error" | "warning";
  className?: string;
}

export function ErrorMessage({
  title,
  message,
  onRetry,
  variant = "error",
  className,
}: ErrorMessageProps) {
  const Icon = variant === "error" ? XCircle : AlertTriangle;
  const colorClass = variant === "error" ? "error" : "warning";

  return (
    <div
      className={cn(
        `bg-${colorClass}/10 border border-${colorClass}/20 rounded-lg p-4`,
        className
      )}
    >
      <div className="flex items-start gap-3">
        <Icon className={`w-5 h-5 text-${colorClass} flex-shrink-0 mt-0.5`} />
        <div className="flex-1">
          {title && (
            <p className={`font-medium text-${colorClass}`}>{title}</p>
          )}
          <p className="text-sm text-text-secondary mt-1">{message}</p>
          {onRetry && (
            <button
              onClick={onRetry}
              className={[
                "mt-3 inline-flex items-center gap-2 px-3 py-1.5 bg-surface",
                "border border-border rounded text-sm hover:bg-white/5 transition-colors"
              ].join(" ")}
            >
              <RefreshCw className="w-3 h-3" />
              Retry
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export function ErrorPage({
  title = "Error",
  message,
  onRetry,
}: {
  title?: string;
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="flex items-center justify-center h-64">
      <ErrorMessage
        title={title}
        message={message}
        onRetry={onRetry}
        className="max-w-md"
      />
    </div>
  );
}
