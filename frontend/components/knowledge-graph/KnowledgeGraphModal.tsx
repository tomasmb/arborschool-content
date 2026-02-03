"use client";

import { useEffect, useState } from "react";
import { X } from "lucide-react";
import { getAtomsGraph, type GraphData } from "@/lib/api";
import { GraphView } from "./GraphView";

interface KnowledgeGraphModalProps {
  subjectId: string;
  isOpen: boolean;
  onClose: () => void;
}

/**
 * Modal wrapper for the knowledge graph visualization.
 * Fetches graph data and displays it in a full-screen modal.
 */
export function KnowledgeGraphModal({
  subjectId,
  isOpen,
  onClose,
}: KnowledgeGraphModalProps) {
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && subjectId) {
      setLoading(true);
      setError(null);
      getAtomsGraph(subjectId)
        .then(setGraphData)
        .catch((err) => setError(err.message))
        .finally(() => setLoading(false));
    }
  }, [isOpen, subjectId]);

  // Handle escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    if (isOpen) {
      document.addEventListener("keydown", handleEscape);
      return () => document.removeEventListener("keydown", handleEscape);
    }
  }, [isOpen, onClose]);

  // Prevent body scroll when modal is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
      return () => {
        document.body.style.overflow = "";
      };
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleNodeClick = (nodeId: string) => {
    // TODO: Could open atom detail panel or navigate
    console.log("Clicked atom:", nodeId);
  };

  return (
    <div className="fixed inset-0 z-50">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/80 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal content */}
      <div className="absolute inset-4 bg-background border border-border rounded-xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div>
            <h2 className="text-xl font-semibold">Knowledge Graph</h2>
            <p className="text-sm text-text-secondary mt-0.5">
              Atom prerequisites and dependencies
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-white/5 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-text-secondary" />
          </button>
        </div>

        {/* Graph content */}
        <div className="flex-1 relative">
          {loading && (
            <div className="absolute inset-0 flex items-center justify-center bg-background">
              <div className="text-text-secondary">Loading graph...</div>
            </div>
          )}

          {error && (
            <div className="absolute inset-0 flex items-center justify-center bg-background">
              <div className="text-error">Error: {error}</div>
            </div>
          )}

          {graphData && !loading && (
            <GraphView
              nodes={graphData.nodes}
              edges={graphData.edges}
              stats={graphData.stats as {
                total_atoms: number;
                atoms_by_eje: Record<string, number>;
                total_edges: number;
                orphan_atoms: number;
              }}
              onNodeClick={handleNodeClick}
            />
          )}
        </div>
      </div>
    </div>
  );
}
