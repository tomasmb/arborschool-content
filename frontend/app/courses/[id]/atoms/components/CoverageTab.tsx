"use client";

import { useEffect, useState } from "react";
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Download,
  BarChart3,
} from "lucide-react";
import { cn, formatEje, getEjeColor } from "@/lib/utils";
import {
  getAtomCoverage,
  type CoverageAnalysisResult,
  type StandardCoverageItem,
} from "@/lib/api";

interface CoverageTabProps {
  subjectId: string;
}

export function CoverageTab({ subjectId }: CoverageTabProps) {
  const [data, setData] = useState<CoverageAnalysisResult | null>(
    null,
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    getAtomCoverage(subjectId)
      .then(setData)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [subjectId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-text-secondary">
          Computing coverage...
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-error">
          Error: {error || "No data"}
        </div>
      </div>
    );
  }

  const handleExport = () => {
    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "atom-coverage-report.json";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <SummaryCard
          label="Standards Covered"
          value={data.standards_fully_covered}
          total={data.total_standards}
          color="text-success"
        />
        <SummaryCard
          label="Partial Coverage"
          value={data.standards_partially_covered}
          total={data.total_standards}
          color="text-amber-500"
        />
        <SummaryCard
          label="Atoms Covered"
          value={
            data.atoms_with_direct_questions +
            data.atoms_with_transitive_coverage
          }
          total={data.total_atoms}
          color="text-accent"
        />
        <SummaryCard
          label="Uncovered Atoms"
          value={data.atoms_without_coverage}
          total={data.total_atoms}
          color="text-error"
        />
      </div>

      {/* Standards Coverage */}
      <div className="bg-surface border border-border rounded-lg">
        <div className="flex items-center justify-between p-6 border-b border-border">
          <div className="flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-accent" />
            <h3 className="font-semibold">Standards Coverage</h3>
          </div>
          <button
            onClick={handleExport}
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg",
              "bg-surface border border-border text-text-secondary",
              "hover:text-text-primary transition-colors",
            )}
          >
            <Download className="w-3.5 h-3.5" />
            Export
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border text-left text-xs text-text-secondary uppercase tracking-wide">
                <th className="px-4 py-3 font-medium">
                  Standard
                </th>
                <th className="px-4 py-3 font-medium">Title</th>
                <th className="px-4 py-3 font-medium text-center">
                  Atoms
                </th>
                <th className="px-4 py-3 font-medium text-center">
                  Status
                </th>
              </tr>
            </thead>
            <tbody>
              {data.standards_coverage.map((sc) => (
                <StandardCoverageRow key={sc.standard_id} item={sc} />
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Question Coverage */}
      <div className="bg-surface border border-border rounded-lg">
        <div className="p-6 border-b border-border">
          <h3 className="font-semibold">
            Question Coverage by Atom
          </h3>
          <p className="text-sm text-text-secondary mt-1">
            {data.atoms_with_direct_questions} atoms have direct
            questions,{" "}
            {data.atoms_with_transitive_coverage} covered
            transitively,{" "}
            {data.atoms_without_coverage} uncovered.
          </p>
        </div>
        <div className="overflow-x-auto max-h-96 overflow-y-auto">
          <table className="w-full">
            <thead className="sticky top-0 bg-surface">
              <tr className="border-b border-border text-left text-xs text-text-secondary uppercase tracking-wide">
                <th className="px-4 py-3 font-medium">Atom</th>
                <th className="px-4 py-3 font-medium">Title</th>
                <th className="px-4 py-3 font-medium text-center">
                  Eje
                </th>
                <th className="px-4 py-3 font-medium text-center">
                  Questions
                </th>
                <th className="px-4 py-3 font-medium text-center">
                  Status
                </th>
              </tr>
            </thead>
            <tbody>
              {data.atom_question_coverage.map((ac) => (
                <tr
                  key={ac.atom_id}
                  className="border-b border-border text-sm"
                >
                  <td className="px-4 py-2 font-mono text-xs text-text-secondary">
                    {ac.atom_id}
                  </td>
                  <td className="px-4 py-2">{ac.titulo}</td>
                  <td className="px-4 py-2 text-center">
                    <span
                      className={cn(
                        "text-xs",
                        getEjeColor(ac.eje),
                      )}
                    >
                      {formatEje(ac.eje).substring(0, 3)}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-center">
                    {ac.direct_questions > 0
                      ? ac.direct_questions
                      : "—"}
                  </td>
                  <td className="px-4 py-2 text-center">
                    <CoverageStatusBadge
                      status={ac.coverage_status}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Overlap Detection */}
      {data.overlap_candidates.length > 0 && (
        <div className="bg-surface border border-border rounded-lg">
          <div className="p-6 border-b border-border">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-amber-500" />
              <h3 className="font-semibold">
                Potential Overlaps ({data.overlap_candidates.length})
              </h3>
            </div>
            <p className="text-sm text-text-secondary mt-1">
              Atom pairs sharing standards with the same type may
              indicate redundancy.
            </p>
          </div>
          <div className="divide-y divide-border">
            {data.overlap_candidates.slice(0, 20).map((o, i) => (
              <div
                key={i}
                className="px-6 py-3 flex items-center gap-4 text-sm"
              >
                <span className="font-mono text-xs text-text-secondary">
                  {o.atom_a}
                </span>
                <span className="text-text-secondary">&harr;</span>
                <span className="font-mono text-xs text-text-secondary">
                  {o.atom_b}
                </span>
                <span className="text-xs text-text-secondary ml-auto">
                  {o.reason}
                </span>
              </div>
            ))}
            {data.overlap_candidates.length > 20 && (
              <div className="px-6 py-3 text-xs text-text-secondary">
                ...and {data.overlap_candidates.length - 20} more
              </div>
            )}
          </div>
        </div>
      )}

      {/* Distribution */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <DistributionCard
          title="By Eje"
          data={data.eje_distribution}
          formatLabel={formatEje}
        />
        <DistributionCard
          title="By Type"
          data={data.type_distribution}
          formatLabel={(v) => v.replace(/_/g, " ")}
        />
      </div>
    </div>
  );
}

// -----------------------------------------------------------------------------
// Sub-components
// -----------------------------------------------------------------------------

function SummaryCard({
  label,
  value,
  total,
  color,
}: {
  label: string;
  value: number;
  total: number;
  color: string;
}) {
  return (
    <div className="bg-surface border border-border rounded-lg p-4 text-center">
      <div className={cn("text-2xl font-bold", color)}>
        {value}
      </div>
      <div className="text-xs text-text-secondary mt-1">
        {label} ({total} total)
      </div>
    </div>
  );
}

function StandardCoverageRow({
  item,
}: {
  item: StandardCoverageItem;
}) {
  return (
    <tr className="border-b border-border text-sm">
      <td className="px-4 py-2 font-mono text-xs text-text-secondary">
        {item.standard_id}
      </td>
      <td className="px-4 py-2 max-w-xs truncate">
        {item.title}
      </td>
      <td className="px-4 py-2 text-center">{item.atom_count}</td>
      <td className="px-4 py-2 text-center">
        <CoverageStatusBadge status={item.coverage_status} />
      </td>
    </tr>
  );
}

function CoverageStatusBadge({
  status,
}: {
  status: string;
}) {
  if (status === "full" || status === "direct") {
    return (
      <span className="inline-flex items-center gap-1 text-xs text-success">
        <CheckCircle2 className="w-3 h-3" />
        {status === "full" ? "Full" : "Direct"}
      </span>
    );
  }
  if (status === "partial" || status === "transitive") {
    return (
      <span className="inline-flex items-center gap-1 text-xs text-amber-500">
        <AlertTriangle className="w-3 h-3" />
        {status === "partial" ? "Partial" : "Transitive"}
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-xs text-error">
      <XCircle className="w-3 h-3" />
      None
    </span>
  );
}

function DistributionCard({
  title,
  data,
  formatLabel,
}: {
  title: string;
  data: Record<string, number>;
  formatLabel: (key: string) => string;
}) {
  const total = Object.values(data).reduce((a, b) => a + b, 0);
  const entries = Object.entries(data).sort(
    ([, a], [, b]) => b - a,
  );

  return (
    <div className="bg-surface border border-border rounded-lg p-6">
      <h4 className="text-sm font-semibold mb-3">{title}</h4>
      <div className="space-y-2">
        {entries.map(([key, count]) => {
          const pct = total > 0 ? (count / total) * 100 : 0;
          return (
            <div key={key}>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-text-secondary capitalize">
                  {formatLabel(key)}
                </span>
                <span className="font-medium">
                  {count} ({pct.toFixed(0)}%)
                </span>
              </div>
              <div className="h-1.5 bg-background rounded-full">
                <div
                  className="h-full bg-accent rounded-full transition-all"
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
