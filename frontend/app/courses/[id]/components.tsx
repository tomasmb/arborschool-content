"use client";

import Link from "next/link";
import {
  CheckCircle2,
  Circle,
  Play,
  RefreshCw,
  AlertTriangle,
  Lock,
} from "lucide-react";

// -----------------------------------------------------------------------------
// Pipeline Card Component
// -----------------------------------------------------------------------------

export interface PipelineCardProps {
  step: number;
  title: string;
  done: boolean;
  description: string;
  detail?: string | null;
  canGenerate?: boolean;
  isBlocked?: boolean;
  blockedReason?: string;
  onGenerate?: () => void;
  linkHref?: string;
  linkText?: string;
  children?: React.ReactNode;
}

export function PipelineCard({
  step,
  title,
  done,
  description,
  detail,
  canGenerate,
  isBlocked,
  blockedReason,
  onGenerate,
  linkHref,
  linkText,
  children,
}: PipelineCardProps) {
  return (
    <div className="bg-surface border border-border rounded-lg p-4">
      <div className="flex items-center gap-3 mb-3">
        {done ? (
          <CheckCircle2 className="w-5 h-5 text-success" />
        ) : (
          <Circle className="w-5 h-5 text-text-secondary" />
        )}
        <h3 className="font-medium">
          {step}. {title}
        </h3>
      </div>

      <p className="text-text-secondary text-sm mb-3">{description}</p>

      {detail && (
        <p className="text-xs text-text-secondary font-mono truncate mb-3">
          {detail}
        </p>
      )}

      {children}

      {/* Action buttons */}
      <div className="mt-4 flex items-center gap-2">
        {canGenerate && onGenerate && (
          <button
            onClick={onGenerate}
            className={[
              "flex items-center gap-2 px-3 py-1.5 bg-accent text-white rounded",
              "text-sm font-medium hover:bg-accent/90 transition-colors",
            ].join(" ")}
          >
            <Play className="w-3 h-3" />
            Generate
          </button>
        )}

        {isBlocked && !done && (
          <span className="flex items-center gap-1.5 text-xs text-text-secondary">
            <Lock className="w-3 h-3" />
            {blockedReason}
          </span>
        )}

        {linkHref && linkText && (
          <Link href={linkHref} className="text-accent text-sm hover:underline">
            {linkText}
          </Link>
        )}
      </div>
    </div>
  );
}

// -----------------------------------------------------------------------------
// Sync Item Component
// -----------------------------------------------------------------------------

export interface SyncItemProps {
  label: string;
  count: number;
  status: "synced" | "pending" | "empty" | "warning";
  warning?: string;
}

export function SyncItem({ label, count, status, warning }: SyncItemProps) {
  const getStatusIcon = () => {
    switch (status) {
      case "synced":
        return <CheckCircle2 className="w-4 h-4 text-success" />;
      case "pending":
        return <RefreshCw className="w-4 h-4 text-warning" />;
      case "warning":
        return <AlertTriangle className="w-4 h-4 text-warning" />;
      default:
        return <Circle className="w-4 h-4 text-text-secondary" />;
    }
  };

  return (
    <div className="flex items-center gap-2">
      {getStatusIcon()}
      <div>
        <p className="text-sm font-medium">{label}</p>
        {warning ? (
          <p className="text-xs text-warning">{warning}</p>
        ) : (
          <p className="text-xs text-text-secondary">{count} items</p>
        )}
      </div>
    </div>
  );
}
