"use client";

import { Clock, RefreshCw, Loader2, RotateCcw, FileText, Trash2 } from "lucide-react";
import { JobStatusBadge } from "./JobStatusBadge";
import { JobStatus } from "@/lib/api";

interface JobsTableProps {
  jobs: JobStatus[];
  onRefresh: () => void;
  onCancel: (jobId: string) => void;
  onResume: (jobId: string, mode: "remaining" | "failed_only") => void;
  onDelete: (jobId: string) => void;
  onViewLogs: (jobId: string) => void;
  resumingJobId: string | null;
}

export function JobsTable({
  jobs,
  onRefresh,
  onCancel,
  onResume,
  onDelete,
  onViewLogs,
  resumingJobId,
}: JobsTableProps) {
  return (
    <div className="bg-surface border border-border rounded-lg p-4 md:p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-medium">Recent Runs</h2>
        <button
          onClick={onRefresh}
          className="p-1 hover:bg-white/10 rounded transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {jobs.length === 0 ? (
        <div className="text-center py-8 text-text-secondary">
          <Clock className="w-8 h-8 mx-auto mb-2 opacity-50" />
          <p>No recent pipeline runs</p>
          <p className="text-sm mt-1">Select a pipeline above to get started</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm min-w-[600px]">
            <thead>
              <tr className="text-left text-text-secondary border-b border-border">
                <th className="pb-2 font-medium">Pipeline</th>
                <th className="pb-2 font-medium">Started</th>
                <th className="pb-2 font-medium">Status</th>
                <th className="pb-2 font-medium">Progress</th>
                <th className="pb-2 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {jobs.map((job) => (
                <tr key={job.job_id} className="hover:bg-white/5">
                  <td className="py-3 font-mono text-xs">{job.pipeline_id}</td>
                  <td className="py-3 text-text-secondary">
                    {job.started_at
                      ? new Date(job.started_at).toLocaleString()
                      : "Pending"}
                  </td>
                  <td className="py-3">
                    <JobStatusBadge status={job.status} />
                  </td>
                  <td className="py-3">
                    {job.total_items > 0 ? (
                      <span className="text-text-secondary">
                        {job.completed_items}/{job.total_items}
                        {job.failed_items > 0 && (
                          <span className="text-error ml-1">
                            ({job.failed_items} failed)
                          </span>
                        )}
                      </span>
                    ) : (
                      <span className="text-text-secondary">-</span>
                    )}
                  </td>
                  <td className="py-3">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => onViewLogs(job.job_id)}
                        className="p-1 hover:bg-white/10 rounded transition-colors"
                        title="View logs"
                      >
                        <FileText className="w-4 h-4 text-text-secondary" />
                      </button>

                      {job.status === "running" && (
                        <button
                          onClick={() => onCancel(job.job_id)}
                          className="text-error hover:underline text-xs"
                        >
                          Cancel
                        </button>
                      )}

                      {(job.status === "failed" || job.status === "cancelled") &&
                        job.can_resume && (
                          <button
                            onClick={() => onResume(job.job_id, "remaining")}
                            disabled={resumingJobId === job.job_id}
                            className="flex items-center gap-1 text-accent hover:underline text-xs disabled:opacity-50"
                            title="Resume job"
                          >
                            {resumingJobId === job.job_id ? (
                              <Loader2 className="w-3 h-3 animate-spin" />
                            ) : (
                              <RotateCcw className="w-3 h-3" />
                            )}
                            Resume
                          </button>
                        )}

                      {job.status === "failed" &&
                        job.can_resume &&
                        job.failed_items > 0 && (
                          <button
                            onClick={() => onResume(job.job_id, "failed_only")}
                            disabled={resumingJobId === job.job_id}
                            className="text-warning hover:underline text-xs disabled:opacity-50"
                          >
                            Retry {job.failed_items} failed
                          </button>
                        )}

                      {job.status !== "running" && job.status !== "pending" && (
                        <button
                          onClick={() => onDelete(job.job_id)}
                          className="p-1 hover:bg-white/10 rounded transition-colors"
                          title="Delete job"
                        >
                          <Trash2 className="w-4 h-4 text-text-secondary hover:text-error" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
