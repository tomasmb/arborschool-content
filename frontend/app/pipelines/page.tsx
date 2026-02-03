"use client";

import { PlayCircle, Clock, CheckCircle2 } from "lucide-react";

export default function PipelinesPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Pipeline Runner</h1>
        <p className="text-text-secondary mt-1">
          Execute content generation pipelines
        </p>
      </div>

      {/* Pipeline selection placeholder */}
      <div className="bg-surface border border-border rounded-lg p-6">
        <h2 className="font-medium mb-4">Select Pipeline</h2>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[
            {
              id: "standards_gen",
              name: "Standards Generation",
              description: "Generate standards from temario",
              hasAICost: true,
            },
            {
              id: "atoms_gen",
              name: "Atoms Generation",
              description: "Generate atoms from standards",
              hasAICost: true,
            },
            {
              id: "pdf_split",
              name: "PDF Split",
              description: "Split test PDF into questions",
              hasAICost: true,
            },
            {
              id: "pdf_to_qti",
              name: "PDF → QTI",
              description: "Convert PDFs to QTI format",
              hasAICost: true,
            },
            {
              id: "tagging",
              name: "Question Tagging",
              description: "Tag questions with atoms",
              hasAICost: true,
            },
            {
              id: "variant_gen",
              name: "Variant Generation",
              description: "Generate question variants",
              hasAICost: true,
            },
          ].map((pipeline) => (
            <div
              key={pipeline.id}
              className="border border-border rounded-lg p-4 hover:border-accent/50 cursor-pointer transition-colors"
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
              {pipeline.hasAICost && (
                <span className="inline-block mt-3 text-xs px-2 py-0.5 bg-warning/10 text-warning rounded">
                  AI Cost
                </span>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Recent runs placeholder */}
      <div className="bg-surface border border-border rounded-lg p-6">
        <h2 className="font-medium mb-4">Recent Runs</h2>

        <div className="text-center py-8 text-text-secondary">
          <Clock className="w-8 h-8 mx-auto mb-2 opacity-50" />
          <p>No recent pipeline runs</p>
          <p className="text-sm mt-1">Select a pipeline above to get started</p>
        </div>
      </div>
    </div>
  );
}
