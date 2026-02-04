"use client";

import { useState, useCallback, useEffect } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import {
  X,
  ZoomIn,
  ZoomOut,
  ChevronLeft,
  ChevronRight,
  Download,
  Maximize2,
} from "lucide-react";
import { cn } from "@/lib/utils";

// Set up PDF.js worker using CDN (reliable with Next.js)
pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.mjs`;

import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";

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

const ZOOM_LEVELS = [0.5, 0.75, 1, 1.25, 1.5, 2];
const DEFAULT_ZOOM_INDEX = 2; // 100%

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
  const [numPages, setNumPages] = useState<number>(0);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [zoomIndex, setZoomIndex] = useState<number>(DEFAULT_ZOOM_INDEX);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const zoom = ZOOM_LEVELS[zoomIndex];

  // Reset state when PDF changes
  useEffect(() => {
    setCurrentPage(1);
    setZoomIndex(DEFAULT_ZOOM_INDEX);
    setLoading(true);
    setError(null);
  }, [pdfUrl]);

  // Handle keyboard navigation
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      switch (e.key) {
        case "Escape":
          onClose();
          break;
        case "ArrowLeft":
          if (e.shiftKey && onPrevious) {
            onPrevious();
          } else if (currentPage > 1) {
            setCurrentPage((p) => p - 1);
          }
          break;
        case "ArrowRight":
          if (e.shiftKey && onNext) {
            onNext();
          } else if (currentPage < numPages) {
            setCurrentPage((p) => p + 1);
          }
          break;
        case "+":
        case "=":
          handleZoomIn();
          break;
        case "-":
          handleZoomOut();
          break;
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose, onPrevious, onNext, currentPage, numPages]);

  const onDocumentLoadSuccess = useCallback(({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
    setLoading(false);
    setError(null);
  }, []);

  const onDocumentLoadError = useCallback((err: Error) => {
    setError(err.message || "Failed to load PDF");
    setLoading(false);
  }, []);

  const handleZoomIn = () => {
    setZoomIndex((i) => Math.min(i + 1, ZOOM_LEVELS.length - 1));
  };

  const handleZoomOut = () => {
    setZoomIndex((i) => Math.max(i - 1, 0));
  };

  const handleDownload = () => {
    const link = document.createElement("a");
    link.href = pdfUrl;
    link.download = title.replace(/\s+/g, "_") + ".pdf";
    link.click();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-black/90">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-surface border-b border-border">
        <h2 className="font-semibold text-lg">{title}</h2>

        <div className="flex items-center gap-2">
          {/* Zoom controls */}
          <div className="flex items-center gap-1 mr-4">
            <button
              onClick={handleZoomOut}
              disabled={zoomIndex === 0}
              className="p-1.5 rounded hover:bg-white/10 disabled:opacity-50"
              title="Zoom out (-)"
            >
              <ZoomOut className="w-4 h-4" />
            </button>
            <span className="text-sm w-16 text-center">{Math.round(zoom * 100)}%</span>
            <button
              onClick={handleZoomIn}
              disabled={zoomIndex === ZOOM_LEVELS.length - 1}
              className="p-1.5 rounded hover:bg-white/10 disabled:opacity-50"
              title="Zoom in (+)"
            >
              <ZoomIn className="w-4 h-4" />
            </button>
          </div>

          {/* Download */}
          <button
            onClick={handleDownload}
            className="flex items-center gap-2 px-3 py-1.5 rounded bg-accent/10 text-accent hover:bg-accent/20 text-sm"
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

      {/* PDF Content */}
      <div className="flex-1 overflow-auto flex items-start justify-center p-4 bg-gray-900">
        {loading && (
          <div className="flex items-center justify-center h-full">
            <div className="text-text-secondary">Loading PDF...</div>
          </div>
        )}

        {error && (
          <div className="flex items-center justify-center h-full">
            <div className="text-error">Error: {error}</div>
          </div>
        )}

        <Document
          file={pdfUrl}
          onLoadSuccess={onDocumentLoadSuccess}
          onLoadError={onDocumentLoadError}
          loading={null}
          className="flex flex-col items-center"
        >
          <Page
            pageNumber={currentPage}
            scale={zoom}
            renderTextLayer
            renderAnnotationLayer
            className="shadow-xl"
          />
        </Document>
      </div>

      {/* Footer - Page navigation */}
      <div className="flex items-center justify-between px-4 py-3 bg-surface border-t border-border">
        {/* Item navigation */}
        <div className="flex items-center gap-2">
          {onPrevious && (
            <button
              onClick={onPrevious}
              className="flex items-center gap-1 px-3 py-1.5 rounded bg-white/5 hover:bg-white/10 text-sm"
              title="Previous (Shift+←)"
            >
              <ChevronLeft className="w-4 h-4" />
              {previousLabel}
            </button>
          )}
          {onNext && (
            <button
              onClick={onNext}
              className="flex items-center gap-1 px-3 py-1.5 rounded bg-white/5 hover:bg-white/10 text-sm"
              title="Next (Shift+→)"
            >
              {nextLabel}
              <ChevronRight className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Page navigation */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setCurrentPage((p) => Math.max(p - 1, 1))}
            disabled={currentPage === 1}
            className="p-1.5 rounded hover:bg-white/10 disabled:opacity-50"
            title="Previous page (←)"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>

          <span className="text-sm">
            Page{" "}
            <input
              type="number"
              value={currentPage}
              onChange={(e) => {
                const page = parseInt(e.target.value);
                if (page >= 1 && page <= numPages) {
                  setCurrentPage(page);
                }
              }}
              className="w-12 px-1 py-0.5 rounded bg-white/10 text-center text-sm mx-1"
              min={1}
              max={numPages}
            />{" "}
            of {numPages}
          </span>

          <button
            onClick={() => setCurrentPage((p) => Math.min(p + 1, numPages))}
            disabled={currentPage === numPages}
            className="p-1.5 rounded hover:bg-white/10 disabled:opacity-50"
            title="Next page (→)"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>

        {/* Keyboard hint */}
        <div className="text-xs text-text-secondary">
          ← → pages | +/- zoom | Esc close
        </div>
      </div>
    </div>
  );
}

/**
 * Inline PDF preview component for embedding in pages.
 * Shows a smaller preview that can be expanded to full modal.
 */
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
  const [numPages, setNumPages] = useState<number>(0);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const onDocumentLoadSuccess = useCallback(({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
    setLoading(false);
  }, []);

  const onDocumentLoadError = useCallback((err: Error) => {
    setError(err.message || "Failed to load PDF");
    setLoading(false);
  }, []);

  return (
    <div className={cn("bg-gray-900 rounded-lg overflow-hidden", height, className)}>
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 bg-surface/50 border-b border-border">
        <span className="text-xs text-text-secondary">{title}</span>
        <div className="flex items-center gap-2">
          {numPages > 1 && (
            <div className="flex items-center gap-1 text-xs">
              <button
                onClick={() => setCurrentPage((p) => Math.max(p - 1, 1))}
                disabled={currentPage === 1}
                className="p-0.5 rounded hover:bg-white/10 disabled:opacity-50"
              >
                <ChevronLeft className="w-3 h-3" />
              </button>
              <span>
                {currentPage}/{numPages}
              </span>
              <button
                onClick={() => setCurrentPage((p) => Math.min(p + 1, numPages))}
                disabled={currentPage === numPages}
                className="p-0.5 rounded hover:bg-white/10 disabled:opacity-50"
              >
                <ChevronRight className="w-3 h-3" />
              </button>
            </div>
          )}
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
      </div>

      {/* Content */}
      <div className="flex items-center justify-center overflow-auto" style={{ height: "calc(100% - 36px)" }}>
        {loading && <div className="text-text-secondary text-sm">Loading...</div>}
        {error && <div className="text-error text-sm">Error: {error}</div>}

        <Document
          file={pdfUrl}
          onLoadSuccess={onDocumentLoadSuccess}
          onLoadError={onDocumentLoadError}
          loading={null}
        >
          <Page pageNumber={currentPage} width={280} renderTextLayer={false} renderAnnotationLayer={false} />
        </Document>
      </div>
    </div>
  );
}
