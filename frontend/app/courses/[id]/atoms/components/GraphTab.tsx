"use client";

import { Network } from "lucide-react";
import { KnowledgeGraphModal } from "@/components/knowledge-graph";
import { useState } from "react";

interface GraphTabProps {
  subjectId: string;
}

export function GraphTab({ subjectId }: GraphTabProps) {
  const [showGraph, setShowGraph] = useState(false);

  return (
    <div className="space-y-6">
      <div className="bg-surface border border-border rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-2">
          Prerequisites Graph
        </h3>
        <p className="text-sm text-text-secondary mb-6">
          Visualize the knowledge graph showing prerequisite
          relationships between atoms. Atoms are color-coded by
          eje.
        </p>
        <button
          onClick={() => setShowGraph(true)}
          className="flex items-center gap-2 px-5 py-2.5 bg-accent text-white rounded-lg text-sm font-medium hover:bg-accent/90 transition-colors"
        >
          <Network className="w-4 h-4" />
          Open Full Graph
        </button>
      </div>

      <KnowledgeGraphModal
        subjectId={subjectId}
        isOpen={showGraph}
        onClose={() => setShowGraph(false)}
      />
    </div>
  );
}
