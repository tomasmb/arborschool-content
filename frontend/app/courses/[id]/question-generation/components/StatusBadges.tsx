"use client";

import {
  AlertTriangle,
  CheckCircle2,
  Circle,
  Image,
  ImageOff,
  MessageSquare,
  Share2,
} from "lucide-react";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Image status badge
// ---------------------------------------------------------------------------

const IMAGE_STATUS_CONFIG: Record<
  string,
  { label: string; cls: string; Icon: typeof Circle }
> = {
  not_enriched: {
    label: "Not enriched",
    cls: "text-text-secondary bg-white/5",
    Icon: Circle,
  },
  no_images: {
    label: "No images",
    cls: "text-text-secondary bg-white/5",
    Icon: Circle,
  },
  images_supported: {
    label: "Images OK",
    cls: "text-success bg-success/10",
    Icon: Image,
  },
  images_unsupported: {
    label: "Unsupported",
    cls: "text-error bg-error/10",
    Icon: ImageOff,
  },
};

export function ImageStatusBadge({
  status,
}: {
  status: string;
}) {
  const config = IMAGE_STATUS_CONFIG[status] ?? IMAGE_STATUS_CONFIG.not_enriched;
  const { label, cls, Icon } = config;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 px-2 py-0.5",
        "rounded text-[11px] font-medium whitespace-nowrap",
        cls,
      )}
      title={`Image status: ${label}`}
    >
      <Icon className="w-3 h-3" />
      {label}
    </span>
  );
}


// ---------------------------------------------------------------------------
// Question coverage badge
// ---------------------------------------------------------------------------

const COVERAGE_CONFIG: Record<
  string,
  { label: string; cls: string; Icon: typeof Circle }
> = {
  direct: {
    label: "Direct",
    cls: "text-success bg-success/10",
    Icon: MessageSquare,
  },
  transitive: {
    label: "Transitive",
    cls: "text-warning bg-warning/10",
    Icon: Share2,
  },
  none: {
    label: "No questions",
    cls: "text-error bg-error/10",
    Icon: AlertTriangle,
  },
};

export function CoverageBadge({
  coverage,
  directCount,
}: {
  coverage: string;
  directCount: number;
}) {
  const config = COVERAGE_CONFIG[coverage] ?? COVERAGE_CONFIG.none;
  const { cls, Icon } = config;

  let label = config.label;
  if (coverage === "direct" && directCount > 0) {
    label = `${directCount} direct`;
  }

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 px-2 py-0.5",
        "rounded text-[11px] font-medium whitespace-nowrap",
        cls,
      )}
      title={
        coverage === "none"
          ? "No PAES questions associated (direct or transitive)"
          : `Coverage: ${label}`
      }
    >
      <Icon className="w-3 h-3" />
      {label}
    </span>
  );
}


// ---------------------------------------------------------------------------
// Blocked overlay tooltip
// ---------------------------------------------------------------------------

export function BlockedOverlay() {
  return (
    <div className="flex items-center gap-1.5 text-xs text-error/80">
      <AlertTriangle className="w-3.5 h-3.5" />
      <span>Blocked — no PAES questions associated</span>
    </div>
  );
}
