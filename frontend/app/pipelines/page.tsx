"use client";

import { useEffect, useState, useCallback } from "react";
import {
  PlayCircle,
  Clock,
  Loader2,
  AlertTriangle,
  RefreshCw,
  X,
  DollarSign,
} from "lucide-react";
import { JobStatusBadge } from "@/components/pipelines/JobStatusBadge";
import {
  getPipelines,
  getPipelineDetails,
  estimatePipelineCost,
  getConfirmationToken,
  runPipeline,
  getJobs,
  cancelJob,
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

  // Fetch pipelines on mount
  useEffect(() => {
    getPipelines()
      .then(setPipelines)
      .catch(console.error)
      .finally(() => setIsLoadingPipelines(false));
  }, []);

  // Fetch jobs and poll for running jobs
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
    const interval = setInterval(fetchJobs, 5000); // Poll every 5 seconds
    return () => clearInterval(interval);
  }, [fetchJobs]);

  // Handle pipeline selection
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

      setFormState((prev) => ({
        ...prev,
        params: details.params,
        values: defaultValues,
      }));
    } catch (error) {
      setFormState((prev) => ({
        ...prev,
        error: error instanceof Error ? error.message : "Failed to load pipeline details",
      }));
    }
  };

  // Handle form value change
  const handleValueChange = (name: string, value: string | number | boolean) => {
    setFormState((prev) => ({
      ...prev,
      values: { ...prev.values, [name]: value },
      estimate: null, // Clear estimate when params change
      confirmationToken: null,
    }));
  };

  // Estimate cost
  const handleEstimate = async () => {
    if (!formState.pipelineId) return;

    setFormState((prev) => ({ ...prev, isEstimating: true, error: null }));

    try {
      const estimate = await estimatePipelineCost(formState.pipelineId, formState.values);
      const tokenResponse = await getConfirmationToken(formState.pipelineId, formState.values);

      setFormState((prev) => ({
        ...prev,
        estimate,
        confirmationToken: tokenResponse.confirmation_token,
        isEstimating: false,
      }));
    } catch (error) {
      setFormState((prev) => ({
        ...prev,
        isEstimating: false,
        error: error instanceof Error ? error.message : "Failed to estimate cost",
      }));
    }
  };

  // Run pipeline
  const handleRun = async () => {
    if (!formState.pipelineId || !formState.confirmationToken) return;

    setFormState((prev) => ({ ...prev, isRunning: true, error: null }));
    setShowConfirmModal(false);

    try {
      await runPipeline(
        formState.pipelineId,
        formState.values,
        formState.confirmationToken
      );
      setFormState(initialFormState);
      fetchJobs(); // Refresh jobs list
    } catch (error) {
      setFormState((prev) => ({
        ...prev,
        isRunning: false,
        error: error instanceof Error ? error.message : "Failed to start pipeline",
      }));
    }
  };

  // Cancel job
  const handleCancelJob = async (jobId: string) => {
    try {
      await cancelJob(jobId);
      fetchJobs();
    } catch (error) {
      console.error("Failed to cancel job:", error);
    }
  };

  // Clear form
  const clearForm = () => {
    setFormState(initialFormState);
  };

  const selectedPipeline = pipelines.find((p) => p.id === formState.pipelineId);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Pipeline Runner</h1>
        <p className="text-text-secondary mt-1">
          Execute content generation pipelines
        </p>
      </div>

      {/* Pipeline selection */}
      <div className="bg-surface border border-border rounded-lg p-6">
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
                    <p className="text-text-secondary text-sm mt-1">
                      {pipeline.description}
                    </p>
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

      {/* Pipeline configuration form */}
      {selectedPipeline && (
        <div className="bg-surface border border-border rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-medium">{selectedPipeline.name} Configuration</h2>
            <button
              onClick={clearForm}
              className="p-1 hover:bg-white/10 rounded transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {formState.error && (
            <div className="mb-4 p-3 bg-error/10 border border-error/20 rounded-lg flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 text-error flex-shrink-0 mt-0.5" />
              <p className="text-sm text-error">{formState.error}</p>
            </div>
          )}

          <div className="space-y-4">
            {formState.params.map((param) => (
              <div key={param.name}>
                <label className="block text-sm font-medium mb-1">
                  {param.label}
                  {param.required && <span className="text-error ml-1">*</span>}
                </label>
                {param.type === "select" ? (
                  <select
                    value={String(formState.values[param.name] || "")}
                    onChange={(e) => handleValueChange(param.name, e.target.value)}
                    className="w-full px-3 py-2 bg-background border border-border rounded-lg text-sm focus:outline-none focus:border-accent"
                  >
                    {!param.required && <option value="">-- Select --</option>}
                    {param.options?.map((opt) => (
                      <option key={opt} value={opt}>
                        {opt}
                      </option>
                    ))}
                  </select>
                ) : param.type === "boolean" ? (
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={Boolean(formState.values[param.name])}
                      onChange={(e) => handleValueChange(param.name, e.target.checked)}
                      className="w-4 h-4 rounded border-border"
                    />
                    <span className="text-sm text-text-secondary">
                      {param.description || "Enable"}
                    </span>
                  </label>
                ) : param.type === "number" ? (
                  <input
                    type="number"
                    value={Number(formState.values[param.name]) || ""}
                    onChange={(e) => handleValueChange(param.name, Number(e.target.value))}
                    className="w-full px-3 py-2 bg-background border border-border rounded-lg text-sm focus:outline-none focus:border-accent"
                  />
                ) : (
                  <input
                    type="text"
                    value={String(formState.values[param.name] || "")}
                    onChange={(e) => handleValueChange(param.name, e.target.value)}
                    placeholder={param.description}
                    className="w-full px-3 py-2 bg-background border border-border rounded-lg text-sm focus:outline-none focus:border-accent"
                  />
                )}
                {param.description && param.type !== "boolean" && (
                  <p className="text-xs text-text-secondary mt-1">{param.description}</p>
                )}
              </div>
            ))}
          </div>

          {/* Cost estimate section */}
          {formState.estimate && (
            <div className="mt-6 p-4 bg-background border border-border rounded-lg">
              <div className="flex items-center gap-2 mb-3">
                <DollarSign className="w-4 h-4 text-warning" />
                <h3 className="font-medium">Estimated Cost</h3>
              </div>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-text-secondary">Model</p>
                  <p className="font-mono">{formState.estimate.model}</p>
                </div>
                <div>
                  <p className="text-text-secondary">Cost Range</p>
                  <p className="font-mono text-warning">
                    ${formState.estimate.estimated_cost_min.toFixed(2)} - $
                    {formState.estimate.estimated_cost_max.toFixed(2)}
                  </p>
                </div>
                <div>
                  <p className="text-text-secondary">Input Tokens</p>
                  <p className="font-mono">
                    {formState.estimate.input_tokens.toLocaleString()}
                  </p>
                </div>
                <div>
                  <p className="text-text-secondary">Output Tokens</p>
                  <p className="font-mono">
                    {formState.estimate.output_tokens.toLocaleString()}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Action buttons */}
          <div className="mt-6 flex gap-3">
            <button
              onClick={handleEstimate}
              disabled={formState.isEstimating}
              className={`flex items-center gap-2 px-4 py-2 bg-surface border border-border
                rounded-lg text-sm hover:bg-white/5 transition-colors disabled:opacity-50`}
            >
              {formState.isEstimating ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <DollarSign className="w-4 h-4" />
              )}
              Estimate Cost
            </button>
            <button
              onClick={() => setShowConfirmModal(true)}
              disabled={!formState.estimate || formState.isRunning}
              className={`flex items-center gap-2 px-4 py-2 bg-accent text-white rounded-lg
                text-sm hover:bg-accent/90 transition-colors disabled:opacity-50
                disabled:cursor-not-allowed`}
            >
              {formState.isRunning ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <PlayCircle className="w-4 h-4" />
              )}
              Run Pipeline
            </button>
          </div>
        </div>
      )}

      {/* Recent runs */}
      <div className="bg-surface border border-border rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-medium">Recent Runs</h2>
          <button
            onClick={fetchJobs}
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
            <table className="w-full text-sm">
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
                      {job.status === "running" && (
                        <button
                          onClick={() => handleCancelJob(job.job_id)}
                          className="text-error hover:underline text-xs"
                        >
                          Cancel
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Confirmation Modal */}
      {showConfirmModal && formState.estimate && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-surface border border-border rounded-lg p-6 max-w-md w-full mx-4">
            <div className="flex items-center gap-3 mb-4">
              <AlertTriangle className="w-6 h-6 text-warning" />
              <h3 className="text-lg font-semibold">Confirm Pipeline Execution</h3>
            </div>

            <p className="text-text-secondary mb-4">
              This will run <strong>{selectedPipeline?.name}</strong> with an estimated
              cost of{" "}
              <strong className="text-warning">
                ${formState.estimate.estimated_cost_min.toFixed(2)} - $
                {formState.estimate.estimated_cost_max.toFixed(2)}
              </strong>
              .
            </p>

            <p className="text-sm text-text-secondary mb-6">
              Do you want to proceed?
            </p>

            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowConfirmModal(false)}
                className="px-4 py-2 bg-surface border border-border rounded-lg text-sm hover:bg-white/5 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleRun}
                disabled={formState.isRunning}
                className="px-4 py-2 bg-accent text-white rounded-lg text-sm hover:bg-accent/90 transition-colors disabled:opacity-50"
              >
                {formState.isRunning ? (
                  <Loader2 className="w-4 h-4 animate-spin inline mr-2" />
                ) : null}
                Yes, Run Pipeline
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
