"use client";

import { Loader2, DollarSign, X } from "lucide-react";
import { PipelineDefinition, PipelineParam, CostEstimate } from "@/lib/api";

interface PipelineFormProps {
  pipeline: PipelineDefinition;
  params: PipelineParam[];
  values: Record<string, string | number | boolean>;
  estimate: CostEstimate | null;
  isEstimating: boolean;
  error: string | null;
  onValueChange: (name: string, value: string | number | boolean) => void;
  onEstimate: () => void;
  onClear: () => void;
}

export function PipelineForm({
  pipeline,
  params,
  values,
  estimate,
  isEstimating,
  error,
  onValueChange,
  onEstimate,
  onClear,
}: PipelineFormProps) {
  return (
    <div className="bg-surface border border-border rounded-lg p-4 md:p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-medium">{pipeline.name} Configuration</h2>
        <button
          onClick={onClear}
          className="p-1 hover:bg-white/10 rounded transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-error/10 border border-error/20 rounded-lg">
          <p className="text-sm text-error">{error}</p>
        </div>
      )}

      <div className="space-y-4">
        {params.map((param) => (
          <div key={param.name}>
            <label className="block text-sm font-medium mb-1">
              {param.label}
              {param.required && <span className="text-error ml-1">*</span>}
            </label>
            {param.type === "select" ? (
              <select
                value={String(values[param.name] || "")}
                onChange={(e) => onValueChange(param.name, e.target.value)}
                className="w-full px-3 py-2 bg-background border border-border rounded-lg text-sm"
              >
                {!param.required && <option value="">-- Select --</option>}
                {param.options?.map((opt) => (
                  <option key={opt} value={opt}>{opt}</option>
                ))}
              </select>
            ) : param.type === "boolean" ? (
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={Boolean(values[param.name])}
                  onChange={(e) => onValueChange(param.name, e.target.checked)}
                  className="w-4 h-4 rounded border-border"
                />
                <span className="text-sm text-text-secondary">
                  {param.description || "Enable"}
                </span>
              </label>
            ) : param.type === "number" ? (
              <input
                type="number"
                value={Number(values[param.name]) || ""}
                onChange={(e) => onValueChange(param.name, Number(e.target.value))}
                className="w-full px-3 py-2 bg-background border border-border rounded-lg text-sm"
              />
            ) : (
              <input
                type="text"
                value={String(values[param.name] || "")}
                onChange={(e) => onValueChange(param.name, e.target.value)}
                placeholder={param.description}
                className="w-full px-3 py-2 bg-background border border-border rounded-lg text-sm"
              />
            )}
            {param.description && param.type !== "boolean" && (
              <p className="text-xs text-text-secondary mt-1">{param.description}</p>
            )}
          </div>
        ))}
      </div>

      {/* Cost estimate display */}
      {estimate && (
        <div className="mt-6 p-4 bg-background border border-border rounded-lg">
          <div className="flex items-center gap-2 mb-3">
            <DollarSign className="w-4 h-4 text-warning" />
            <h3 className="font-medium">Estimated Cost</h3>
          </div>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-text-secondary">Model</p>
              <p className="font-mono">{estimate.model}</p>
            </div>
            <div>
              <p className="text-text-secondary">Cost Range</p>
              <p className="font-mono text-warning">
                ${estimate.estimated_cost_min.toFixed(2)} - $
                {estimate.estimated_cost_max.toFixed(2)}
              </p>
            </div>
            <div>
              <p className="text-text-secondary">Input Tokens</p>
              <p className="font-mono">{estimate.input_tokens.toLocaleString()}</p>
            </div>
            <div>
              <p className="text-text-secondary">Output Tokens</p>
              <p className="font-mono">{estimate.output_tokens.toLocaleString()}</p>
            </div>
          </div>
        </div>
      )}

      {/* Estimate button */}
      <div className="mt-6">
        <button
          onClick={onEstimate}
          disabled={isEstimating}
          className={[
            "flex items-center gap-2 px-4 py-2 bg-surface border border-border",
            "rounded-lg text-sm hover:bg-white/5 transition-colors disabled:opacity-50"
          ].join(" ")}
        >
          {isEstimating ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <DollarSign className="w-4 h-4" />
          )}
          Estimate Cost
        </button>
      </div>
    </div>
  );
}
