"use client";

import { useEffect, useState } from "react";
import { getOverview, type OverviewResponse, type SubjectBrief } from "@/lib/api";
import { SubjectCard } from "@/components/dashboard/SubjectCard";

export default function DashboardPage() {
  const [data, setData] = useState<OverviewResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getOverview()
      .then(setData)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-text-secondary">Loading...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-error">Error: {error}</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Dashboard</h1>
        <p className="text-text-secondary mt-1">
          Content pipeline overview and management
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {data?.subjects.map((subject) => (
          <SubjectCard key={subject.id} subject={subject} />
        ))}

        {/* Placeholder for future subjects */}
        <div className="bg-surface border border-border border-dashed rounded-lg p-6 flex items-center justify-center">
          <div className="text-center">
            <p className="text-text-secondary text-sm">More subjects coming soon</p>
            <p className="text-text-secondary text-xs mt-1">PAES M2, etc.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
