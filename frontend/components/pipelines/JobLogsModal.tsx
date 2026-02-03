"use client";

import { useEffect, useState, useRef } from "react";
import { X, Loader2, RefreshCw, ChevronDown } from "lucide-react";
import { getJobLogs, JobLogsResponse } from "@/lib/api";

interface JobLogsModalProps {
  jobId: string;
  pipelineId: string;
  onClose: () => void;
}

export function JobLogsModal({ jobId, pipelineId, onClose }: JobLogsModalProps) {
  const [logs, setLogs] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [autoScroll, setAutoScroll] = useState(true);
  const [total, setTotal] = useState(0);
  const logsEndRef = useRef<HTMLDivElement>(null);

  const fetchLogs = async () => {
    try {
      const response = await getJobLogs(jobId, 0, 500);
      setLogs(response.logs);
      setTotal(response.total);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load logs");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
    // Poll for new logs every 2 seconds
    const interval = setInterval(fetchLogs, 2000);
    return () => clearInterval(interval);
  }, [jobId]);

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs, autoScroll]);

  // Handle escape key
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleEsc);
    return () => window.removeEventListener("keydown", handleEsc);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-4xl max-h-[80vh] bg-surface border border-border rounded-lg shadow-xl flex flex-col mx-4">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border">
          <div>
            <h2 className="font-semibold">Job Logs</h2>
            <p className="text-sm text-text-secondary">
              {pipelineId} • {jobId}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={fetchLogs}
              className="p-2 hover:bg-white/10 rounded transition-colors"
              title="Refresh logs"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
            <button
              onClick={onClose}
              className="p-2 hover:bg-white/10 rounded transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Logs content */}
        <div className="flex-1 overflow-y-auto p-4 bg-background font-mono text-xs">
          {loading && logs.length === 0 && (
            <div className="flex items-center justify-center h-32">
              <Loader2 className="w-5 h-5 animate-spin text-text-secondary" />
            </div>
          )}

          {error && (
            <div className="text-error p-4 bg-error/10 rounded">
              Error: {error}
            </div>
          )}

          {logs.length === 0 && !loading && !error && (
            <div className="text-text-secondary text-center py-8">
              No logs available
            </div>
          )}

          {logs.map((line, idx) => (
            <div
              key={idx}
              className={`py-0.5 ${
                line.toLowerCase().includes("error")
                  ? "text-error"
                  : line.toLowerCase().includes("warning")
                  ? "text-warning"
                  : line.toLowerCase().includes("success") ||
                    line.toLowerCase().includes("complete")
                  ? "text-success"
                  : "text-text-primary"
              }`}
            >
              <span className="text-text-secondary mr-3 select-none">
                {String(idx + 1).padStart(4, " ")}
              </span>
              {line}
            </div>
          ))}
          <div ref={logsEndRef} />
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-3 border-t border-border text-xs text-text-secondary">
          <span>{total} total lines</span>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={(e) => setAutoScroll(e.target.checked)}
              className="w-3 h-3"
            />
            Auto-scroll
            <ChevronDown className="w-3 h-3" />
          </label>
        </div>
      </div>
    </div>
  );
}
