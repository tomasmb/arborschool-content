"use client";

import { useEffect, useState, useCallback } from "react";
import { X, ArrowDownLeft, ArrowUpRight, ExternalLink } from "lucide-react";
import { getAtomsGraph, type GraphData, type GraphNode } from "@/lib/api";
import { GraphView } from "./GraphView";
import { cn, formatEje, getEjeColor, getEjeBgColor } from "@/lib/utils";

interface KnowledgeGraphModalProps {
  subjectId: string;
  isOpen: boolean;
  onClose: () => void;
}

interface SelectedAtomData {
  id: string;
  titulo: string;
  eje: string;
  tipo_atomico: string;
  prerequisites: { id: string; titulo: string }[];
  dependents: { id: string; titulo: string }[];
}

/**
 * Modal wrapper for the knowledge graph visualization.
 * Fetches graph data and displays it in a full-screen modal.
 * Now includes a side panel that opens when a node is clicked.
 */
export function KnowledgeGraphModal({
  subjectId,
  isOpen,
  onClose,
}: KnowledgeGraphModalProps) {
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedAtom, setSelectedAtom] = useState<SelectedAtomData | null>(null);

  useEffect(() => {
    if (isOpen && subjectId) {
      setLoading(true);
      setError(null);
      setSelectedAtom(null);
      getAtomsGraph(subjectId)
        .then(setGraphData)
        .catch((err) => setError(err.message))
        .finally(() => setLoading(false));
    }
  }, [isOpen, subjectId]);

  // Handle escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        if (selectedAtom) {
          setSelectedAtom(null);
        } else {
          onClose();
        }
      }
    };
    if (isOpen) {
      document.addEventListener("keydown", handleEscape);
      return () => document.removeEventListener("keydown", handleEscape);
    }
  }, [isOpen, onClose, selectedAtom]);

  // Prevent body scroll when modal is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
      return () => {
        document.body.style.overflow = "";
      };
    }
  }, [isOpen]);

  const handleNodeClick = useCallback(
    (nodeId: string) => {
      if (!graphData) return;

      const node = graphData.nodes.find((n) => n.id === nodeId);
      if (!node) return;

      // Find prerequisites (edges where this node is the target)
      const prereqEdges = graphData.edges.filter((e) => e.target === nodeId);
      const prerequisites = prereqEdges
        .map((e) => {
          const prereqNode = graphData.nodes.find((n) => n.id === e.source);
          return prereqNode
            ? { id: prereqNode.id, titulo: (prereqNode.data.titulo as string) || prereqNode.id }
            : null;
        })
        .filter(Boolean) as { id: string; titulo: string }[];

      // Find dependents (edges where this node is the source)
      const depEdges = graphData.edges.filter((e) => e.source === nodeId);
      const dependents = depEdges
        .map((e) => {
          const depNode = graphData.nodes.find((n) => n.id === e.target);
          return depNode
            ? { id: depNode.id, titulo: (depNode.data.titulo as string) || depNode.id }
            : null;
        })
        .filter(Boolean) as { id: string; titulo: string }[];

      setSelectedAtom({
        id: node.id,
        titulo: (node.data.titulo as string) || node.id,
        eje: (node.data.eje as string) || "unknown",
        tipo_atomico: (node.data.tipo_atomico as string) || "unknown",
        prerequisites,
        dependents,
      });
    },
    [graphData]
  );

  if (!isOpen) return null;

  const stats = graphData?.stats as {
    total_atoms: number;
    atoms_by_eje: Record<string, number>;
    total_edges: number;
    orphan_atoms: number;
  } | undefined;

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
        <div className="flex items-center justify-between px-6 py-4 border-b border-border shrink-0">
          <div>
            <h2 className="text-xl font-semibold">Knowledge Graph</h2>
            <p className="text-sm text-text-secondary mt-0.5">
              {stats && (
                <>
                  {stats.total_atoms} atoms | {stats.total_edges} edges | {stats.orphan_atoms} orphans
                </>
              )}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-white/5 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-text-secondary" />
          </button>
        </div>

        {/* Graph content with side panel */}
        <div className="flex-1 flex overflow-hidden">
          {/* Main graph area */}
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

            {graphData && !loading && stats && (
              <GraphView
                nodes={graphData.nodes}
                edges={graphData.edges}
                stats={stats}
                onNodeClick={handleNodeClick}
              />
            )}
          </div>

          {/* Side panel - shows when an atom is selected */}
          {selectedAtom && (
            <AtomDetailPanel
              atom={selectedAtom}
              onClose={() => setSelectedAtom(null)}
              onSelectAtom={(id) => handleNodeClick(id)}
            />
          )}
        </div>
      </div>
    </div>
  );
}

interface AtomDetailPanelProps {
  atom: SelectedAtomData;
  onClose: () => void;
  onSelectAtom: (id: string) => void;
}

function AtomDetailPanel({ atom, onClose, onSelectAtom }: AtomDetailPanelProps) {
  return (
    <div
      className="w-80 border-l border-border bg-surface flex flex-col shrink-0"
      style={{ animation: "slideIn 200ms ease-out" }}
    >
      {/* Header */}
      <div className="px-4 py-3 border-b border-border flex items-center justify-between">
        <h3 className="font-medium text-sm truncate">{atom.titulo}</h3>
        <button
          onClick={onClose}
          className="p-1 hover:bg-white/10 rounded"
          title="Close panel (Esc)"
        >
          <X className="w-4 h-4 text-text-secondary" />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Basic info */}
        <div>
          <p className="font-mono text-xs text-text-secondary mb-2">{atom.id}</p>
          <div className="flex items-center gap-2">
            <span
              className={cn(
                "text-xs px-2 py-0.5 rounded",
                getEjeBgColor(atom.eje),
                getEjeColor(atom.eje)
              )}
            >
              {formatEje(atom.eje)}
            </span>
            <span className="text-xs text-text-secondary capitalize">
              {atom.tipo_atomico.replace("_", " ")}
            </span>
          </div>
        </div>

        {/* Prerequisites */}
        <div>
          <h4 className="text-xs font-medium text-text-secondary uppercase tracking-wide mb-2 flex items-center gap-1">
            <ArrowDownLeft className="w-3 h-3" />
            Prerequisites ({atom.prerequisites.length})
          </h4>
          {atom.prerequisites.length > 0 ? (
            <ul className="space-y-1">
              {atom.prerequisites.map((prereq) => (
                <li key={prereq.id}>
                  <button
                    onClick={() => onSelectAtom(prereq.id)}
                    className="w-full text-left text-sm hover:bg-white/5 rounded px-2 py-1 flex items-center gap-2"
                  >
                    <span className="text-accent">→</span>
                    <span className="truncate">{prereq.titulo}</span>
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-text-secondary">No prerequisites (foundation)</p>
          )}
        </div>

        {/* Dependents */}
        <div>
          <h4 className="text-xs font-medium text-text-secondary uppercase tracking-wide mb-2 flex items-center gap-1">
            <ArrowUpRight className="w-3 h-3" />
            Dependents ({atom.dependents.length})
          </h4>
          {atom.dependents.length > 0 ? (
            <ul className="space-y-1">
              {atom.dependents.map((dep) => (
                <li key={dep.id}>
                  <button
                    onClick={() => onSelectAtom(dep.id)}
                    className="w-full text-left text-sm hover:bg-white/5 rounded px-2 py-1 flex items-center gap-2"
                  >
                    <span className="text-accent">←</span>
                    <span className="truncate">{dep.titulo}</span>
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-text-secondary">No dependents (leaf)</p>
          )}
        </div>
      </div>

      {/* Footer with action */}
      <div className="px-4 py-3 border-t border-border">
        <button className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-accent/10 text-accent rounded text-sm font-medium hover:bg-accent/20">
          <ExternalLink className="w-4 h-4" />
          View Full Details
        </button>
      </div>

      <style jsx>{`
        @keyframes slideIn {
          from {
            opacity: 0;
            transform: translateX(20px);
          }
          to {
            opacity: 1;
            transform: translateX(0);
          }
        }
      `}</style>
    </div>
  );
}
