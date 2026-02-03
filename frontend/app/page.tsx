"use client";

import { useEffect, useState, useCallback } from "react";
import { getOverview, type OverviewResponse } from "@/lib/api";
import { SubjectCard } from "@/components/dashboard/SubjectCard";
import { LoadingPage } from "@/components/ui/LoadingSpinner";
import { ErrorPage } from "@/components/ui/ErrorMessage";

export default function DashboardPage() {
  const [data, setData] = useState<OverviewResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getOverview();
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  if (loading) {
    return <LoadingPage text="Loading dashboard..." />;
  }

  if (error) {
    return (
      <ErrorPage
        title="Failed to load dashboard"
        message={error}
        onRetry={fetchData}
      />
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
