"use client";

import { useEffect, useState, useCallback } from "react";
import {
  PlayCircle,
  Loader2,
  AlertTriangle,
} from "lucide-react";
import { JobLogsModal } from "@/components/pipelines/JobLogsModal";
import { PipelineForm } from "@/components/pipelines/PipelineForm";
import { JobsTable } from "@/components/pipelines/JobsTable";
import {
  getPipelines,
  getPipelineDetails,
  estimatePipelineCost,
  getConfirmationToken,
  runPipeline,
  getJobs,
  cancelJob,
  resumeJob,
  deleteJob,
  PipelineDefinition,
  PipelineParam,
  CostEstimate,
  JobStatus,
} from "@/lib/api";

type PipelineFormState = {
  pipelineId: string | null;
  params: PipelineParam[];
  values: Record<string, string | number | boolean>;
  estimate: CostEstimate | null;
  confirmationToken: string | null;
  isEstimating: boolean;
  isRunning: boolean;
  error: string | null;
};

const initialFormState: PipelineFormState = {
  pipelineId: null, params: [], values: {}, estimate: null,
  confirmationToken: null, isEstimating: false, isRunning: false, error: null,
};

export default function PipelinesPage() {
  const [pipelines, setPipelines] = useState<PipelineDefinition[]>([]);
  const [jobs, setJobs] = useState<JobStatus[]>([]);
  const [formState, setFormState] = useState<PipelineFormState>(initialFormState);
  const [isLoadingPipelines, setIsLoadingPipelines] = useState(true);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [logsJobId, setLogsJobId] = useState<string | null>(null);
  const [resumingJobId, setResumingJobId] = useState<string | null>(null);

  useEffect(() => {
    getPipelines()
      .then(setPipelines)
      .catch(console.error)
      .finally(() => setIsLoadingPipelines(false));
  }, []);

  const fetchJobs = useCallback(async () => {
    try {
      const response = await getJobs(20);
      setJobs(response.jobs);
    } catch (error) {
      console.error("Failed to fetch jobs:", error);
    }
  }, []);

  useEffect(() => {
    fetchJobs();
    const interval = setInterval(fetchJobs, 5000);
    return () => clearInterval(interval);
  }, [fetchJobs]);

  const selectPipeline = async (pipelineId: string) => {
    setFormState({ ...initialFormState, pipelineId });
    try {
      const details = await getPipelineDetails(pipelineId);
      const defaultValues: Record<string, string | number | boolean> = {};
      details.params.forEach((p) => {
        if (p.default !== null && p.default !== undefined) {
          defaultValues[p.name] = p.default;
        } else if (p.type === "select" && p.options?.length) {
          defaultValues[p.name] = p.options[0];
        } else if (p.type === "boolean") {
          defaultValues[p.name] = false;
        } else if (p.type === "number") {
          defaultValues[p.name] = 0;
        } else {
          defaultValues[p.name] = "";
        }
      });
      setFormState((prev) => ({ ...prev, params: details.params, values: defaultValues }));
    } catch (error) {
      setFormState((prev) => ({
        ...prev, error: error instanceof Error ? error.message : "Failed to load pipeline",
      }));
    }
  };

  const handleValueChange = (name: string, value: string | number | boolean) => {
    setFormState((prev) => ({
      ...prev, values: { ...prev.values, [name]: value },
      estimate: null, confirmationToken: null,
    }));
  };

  const handleEstimate = async () => {
    if (!formState.pipelineId) return;
    setFormState((prev) => ({ ...prev, isEstimating: true, error: null }));
    try {
      const estimate = await estimatePipelineCost(formState.pipelineId, formState.values);
      const tokenResponse = await getConfirmationToken(formState.pipelineId, formState.values);
      setFormState((prev) => ({
        ...prev, estimate, confirmationToken: tokenResponse.confirmation_token, isEstimating: false,
      }));
    } catch (error) {
      setFormState((prev) => ({
        ...prev, isEstimating: false,
        error: error instanceof Error ? error.message : "Failed to estimate cost",
      }));
    }
  };

  const handleRun = async () => {
    if (!formState.pipelineId || !formState.confirmationToken) return;
    setFormState((prev) => ({ ...prev, isRunning: true, error: null }));
    setShowConfirmModal(false);
    try {
      await runPipeline(formState.pipelineId, formState.values, formState.confirmationToken);
      setFormState(initialFormState);
      fetchJobs();
    } catch (error) {
      setFormState((prev) => ({
        ...prev, isRunning: false,
        error: error instanceof Error ? error.message : "Failed to start pipeline",
      }));
    }
  };

  const handleCancelJob = async (jobId: string) => {
    try { await cancelJob(jobId); fetchJobs(); }
    catch (error) { console.error("Failed to cancel job:", error); }
  };

  const handleResumeJob = async (jobId: string, mode: "remaining" | "failed_only") => {
    setResumingJobId(jobId);
    try { await resumeJob(jobId, mode); fetchJobs(); }
    catch (error) { console.error("Failed to resume job:", error); }
    finally { setResumingJobId(null); }
  };

  const handleDeleteJob = async (jobId: string) => {
    if (!confirm("Are you sure you want to delete this job record?")) return;
    try { await deleteJob(jobId); fetchJobs(); }
    catch (error) { console.error("Failed to delete job:", error); }
  };

  const selectedPipeline = pipelines.find((p) => p.id === formState.pipelineId);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Pipeline Runner</h1>
        <p className="text-text-secondary mt-1">Execute content generation pipelines</p>
      </div>

      {/* Pipeline selection */}
      <div className="bg-surface border border-border rounded-lg p-4 md:p-6">
        <h2 className="font-medium mb-4">Select Pipeline</h2>
        {isLoadingPipelines ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 animate-spin text-text-secondary" />
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {pipelines.map((pipeline) => (
              <div
                key={pipeline.id}
                onClick={() => selectPipeline(pipeline.id)}
                className={`border rounded-lg p-4 cursor-pointer transition-colors ${
                  formState.pipelineId === pipeline.id
                    ? "border-accent bg-accent/10"
                    : "border-border hover:border-accent/50"
                }`}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-medium">{pipeline.name}</h3>
                    <p className="text-text-secondary text-sm mt-1">{pipeline.description}</p>
                  </div>
                  <PlayCircle className="w-5 h-5 text-text-secondary" />
                </div>
                {pipeline.has_ai_cost && (
                  <span className="inline-block mt-3 text-xs px-2 py-0.5 bg-warning/10 text-warning rounded">
                    AI Cost
                  </span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Pipeline form */}
      {selectedPipeline && (
        <div className="space-y-4">
          <PipelineForm
            pipeline={selectedPipeline}
            params={formState.params}
            values={formState.values}
            estimate={formState.estimate}
            isEstimating={formState.isEstimating}
            error={formState.error}
            onValueChange={handleValueChange}
            onEstimate={handleEstimate}
            onClear={() => setFormState(initialFormState)}
          />

          {/* Run button */}
          {formState.estimate && (
            <button
              onClick={() => setShowConfirmModal(true)}
              disabled={formState.isRunning}
              className={[
                "flex items-center gap-2 px-4 py-2 bg-accent text-white rounded-lg",
                "text-sm hover:bg-accent/90 transition-colors disabled:opacity-50"
              ].join(" ")}
            >
              {formState.isRunning ? <Loader2 className="w-4 h-4 animate-spin" /> : <PlayCircle className="w-4 h-4" />}
              Run Pipeline
            </button>
          )}
        </div>
      )}

      {/* Jobs table */}
      <JobsTable
        jobs={jobs}
        onRefresh={fetchJobs}
        onCancel={handleCancelJob}
        onResume={handleResumeJob}
        onDelete={handleDeleteJob}
        onViewLogs={setLogsJobId}
        resumingJobId={resumingJobId}
      />

      {/* Confirmation Modal */}
      {showConfirmModal && formState.estimate && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-surface border border-border rounded-lg p-6 max-w-md w-full mx-4">
            <div className="flex items-center gap-3 mb-4">
              <AlertTriangle className="w-6 h-6 text-warning" />
              <h3 className="text-lg font-semibold">Confirm Pipeline Execution</h3>
            </div>
            <p className="text-text-secondary mb-4">
              This will run <strong>{selectedPipeline?.name}</strong> with an estimated cost of{" "}
              <strong className="text-warning">
                ${formState.estimate.estimated_cost_min.toFixed(2)} - ${formState.estimate.estimated_cost_max.toFixed(2)}
              </strong>.
            </p>
            <p className="text-sm text-text-secondary mb-6">Do you want to proceed?</p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowConfirmModal(false)}
                className="px-4 py-2 bg-surface border border-border rounded-lg text-sm hover:bg-white/5"
              >
                Cancel
              </button>
              <button
                onClick={handleRun}
                disabled={formState.isRunning}
                className="px-4 py-2 bg-accent text-white rounded-lg text-sm hover:bg-accent/90 disabled:opacity-50"
              >
                {formState.isRunning && <Loader2 className="w-4 h-4 animate-spin inline mr-2" />}
                Yes, Run Pipeline
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Job Logs Modal */}
      {logsJobId && (
        <JobLogsModal
          jobId={logsJobId}
          pipelineId={jobs.find((j) => j.job_id === logsJobId)?.pipeline_id || ""}
          onClose={() => setLogsJobId(null)}
        />
      )}
    </div>
  );
}
