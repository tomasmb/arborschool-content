"use client";

import { useEffect, useState, useCallback } from "react";
import {
  X,
  ChevronLeft,
  ChevronRight,
  Download,
  Maximize2,
} from "lucide-react";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// PDFViewerModal — fullscreen modal using the browser's native PDF renderer
// ---------------------------------------------------------------------------

export interface PDFViewerModalProps {
  /** Whether the modal is open */
  isOpen: boolean;
  /** Callback to close the modal */
  onClose: () => void;
  /** URL of the PDF to display */
  pdfUrl: string;
  /** Title to display in the modal header */
  title?: string;
  /** Optional callback for navigation to previous item */
  onPrevious?: () => void;
  /** Optional callback for navigation to next item */
  onNext?: () => void;
  /** Label for previous navigation */
  previousLabel?: string;
  /** Label for next navigation */
  nextLabel?: string;
}

export function PDFViewerModal({
  isOpen,
  onClose,
  pdfUrl,
  title = "PDF Viewer",
  onPrevious,
  onNext,
  previousLabel = "Previous",
  nextLabel = "Next",
}: PDFViewerModalProps) {
  const [loading, setLoading] = useState<boolean>(true);

  // Reset loading state when PDF URL changes
  useEffect(() => {
    setLoading(true);
  }, [pdfUrl]);

  // Keyboard shortcuts
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      switch (e.key) {
        case "Escape":
          onClose();
          break;
        case "ArrowLeft":
          if (e.shiftKey && onPrevious) onPrevious();
          break;
        case "ArrowRight":
          if (e.shiftKey && onNext) onNext();
          break;
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose, onPrevious, onNext]);

  const handleDownload = useCallback(() => {
    const link = document.createElement("a");
    link.href = pdfUrl;
    link.download = title.replace(/\s+/g, "_") + ".pdf";
    link.click();
  }, [pdfUrl, title]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-black/90">
      {/* Header */}
      <div
        className={cn(
          "flex items-center justify-between px-4 py-3",
          "bg-surface border-b border-border",
        )}
      >
        <h2 className="font-semibold text-lg truncate mr-4">{title}</h2>

        <div className="flex items-center gap-2">
          {/* Download */}
          <button
            onClick={handleDownload}
            className={cn(
              "flex items-center gap-2 px-3 py-1.5 rounded text-sm",
              "bg-accent/10 text-accent hover:bg-accent/20",
            )}
          >
            <Download className="w-4 h-4" />
            Download
          </button>

          {/* Close */}
          <button
            onClick={onClose}
            className="p-2 rounded hover:bg-white/10 ml-2"
            title="Close (Esc)"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* PDF Content — browser-native renderer */}
      <div className="flex-1 relative bg-gray-900">
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-text-secondary">Loading PDF...</div>
          </div>
        )}
        <iframe
          src={pdfUrl}
          title={title}
          className="w-full h-full border-0"
          onLoad={() => setLoading(false)}
        />
      </div>

      {/* Footer — item navigation */}
      {(onPrevious || onNext) && (
        <div
          className={cn(
            "flex items-center justify-between px-4 py-3",
            "bg-surface border-t border-border",
          )}
        >
          <div className="flex items-center gap-2">
            {onPrevious && (
              <button
                onClick={onPrevious}
                className={cn(
                  "flex items-center gap-1 px-3 py-1.5 rounded text-sm",
                  "bg-white/5 hover:bg-white/10",
                )}
                title="Previous (Shift+Left)"
              >
                <ChevronLeft className="w-4 h-4" />
                {previousLabel}
              </button>
            )}
            {onNext && (
              <button
                onClick={onNext}
                className={cn(
                  "flex items-center gap-1 px-3 py-1.5 rounded text-sm",
                  "bg-white/5 hover:bg-white/10",
                )}
                title="Next (Shift+Right)"
              >
                {nextLabel}
                <ChevronRight className="w-4 h-4" />
              </button>
            )}
          </div>

          <div className="text-xs text-text-secondary">
            Shift+Arrow navigate items | Esc close
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// PDFPreview — inline preview with optional expand button
// ---------------------------------------------------------------------------

export interface PDFPreviewProps {
  pdfUrl: string;
  title?: string;
  height?: string;
  className?: string;
  onExpand?: () => void;
}

export function PDFPreview({
  pdfUrl,
  title = "PDF Preview",
  height = "h-64",
  className,
  onExpand,
}: PDFPreviewProps) {
  const [loading, setLoading] = useState<boolean>(true);

  return (
    <div className={cn("bg-gray-900 rounded-lg overflow-hidden", height, className)}>
      {/* Header */}
      <div
        className={cn(
          "flex items-center justify-between px-3 py-2",
          "bg-surface/50 border-b border-border",
        )}
      >
        <span className="text-xs text-text-secondary truncate">{title}</span>
        {onExpand && (
          <button
            onClick={onExpand}
            className="p-1 rounded hover:bg-white/10"
            title="Expand"
          >
            <Maximize2 className="w-3 h-3" />
          </button>
        )}
      </div>

      {/* Content — browser-native PDF renderer */}
      <div className="relative" style={{ height: "calc(100% - 36px)" }}>
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-text-secondary text-sm">Loading...</span>
          </div>
        )}
        <iframe
          src={pdfUrl}
          title={title}
          className="w-full h-full border-0"
          onLoad={() => setLoading(false)}
        />
      </div>
    </div>
  );
}
