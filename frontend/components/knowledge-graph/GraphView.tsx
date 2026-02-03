"use client";

import { useCallback, useMemo } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  type NodeTypes,
  MarkerType,
  Panel,
} from "reactflow";
import "reactflow/dist/style.css";

import { AtomNode } from "./AtomNode";
import { formatEje } from "@/lib/utils";

interface GraphStats {
  total_atoms: number;
  atoms_by_eje: Record<string, number>;
  total_edges: number;
  orphan_atoms: number;
}

interface GraphViewProps {
  nodes: Node[];
  edges: Edge[];
  stats: GraphStats;
  onNodeClick?: (nodeId: string) => void;
}

// Register custom node types
const nodeTypes: NodeTypes = {
  atom: AtomNode,
};

// Color map for minimap
const ejeColorMap: Record<string, string> = {
  numeros: "#3b82f6",
  algebra_y_funciones: "#a855f7",
  geometria: "#22c55e",
  probabilidad_y_estadistica: "#f97316",
};

/**
 * React Flow graph visualization for the knowledge graph.
 * Shows atoms as nodes and prerequisites as directed edges.
 */
export function GraphView({ nodes, edges, stats, onNodeClick }: GraphViewProps) {
  // Transform API nodes to React Flow format
  const flowNodes = useMemo(
    () =>
      nodes.map((node) => ({
        ...node,
        type: "atom",
        data: {
          ...node.data,
        },
      })),
    [nodes]
  );

  // Transform API edges to React Flow format with styling
  const flowEdges = useMemo(
    () =>
      edges.map((edge) => ({
        ...edge,
        animated: false,
        style: { stroke: "#404040", strokeWidth: 1.5 },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: "#404040",
          width: 15,
          height: 15,
        },
      })),
    [edges]
  );

  const [nodesState, setNodes, onNodesChange] = useNodesState(flowNodes);
  const [edgesState, setEdges, onEdgesChange] = useEdgesState(flowEdges);

  const handleNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      onNodeClick?.(node.id);
    },
    [onNodeClick]
  );

  // Get node color for minimap
  const getNodeColor = useCallback((node: Node) => {
    const eje = node.data?.eje as string;
    return ejeColorMap[eje] || "#6b7280";
  }, []);

  return (
    <div className="w-full h-full bg-background">
      <ReactFlow
        nodes={nodesState}
        edges={edgesState}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.1}
        maxZoom={2}
        defaultEdgeOptions={{
          type: "smoothstep",
        }}
        proOptions={{ hideAttribution: true }}
      >
        {/* Dark background with dots */}
        <Background color="#262626" gap={20} size={1} />

        {/* Controls (zoom, fit, etc) */}
        <Controls
          className="!bg-surface !border-border !rounded-lg !shadow-none"
          showInteractive={false}
        />

        {/* Minimap for navigation */}
        <MiniMap
          nodeColor={getNodeColor}
          maskColor="rgba(0, 0, 0, 0.8)"
          className="!bg-surface !border-border !rounded-lg"
          pannable
          zoomable
        />

        {/* Stats panel */}
        <Panel position="top-left" className="!m-4">
          <div className="bg-surface/95 backdrop-blur border border-border rounded-lg p-4 min-w-[200px]">
            <h3 className="text-sm font-semibold mb-3 text-text-primary">
              Graph Stats
            </h3>

            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-text-secondary">Total Atoms</span>
                <span className="font-medium">{stats.total_atoms}</span>
              </div>

              <div className="flex justify-between">
                <span className="text-text-secondary">Connections</span>
                <span className="font-medium">{stats.total_edges}</span>
              </div>

              <div className="flex justify-between">
                <span className="text-text-secondary">Orphan Atoms</span>
                <span className="font-medium text-warning">
                  {stats.orphan_atoms}
                </span>
              </div>

              <div className="border-t border-border pt-2 mt-2">
                <p className="text-text-secondary text-xs mb-2">By Eje</p>
                {Object.entries(stats.atoms_by_eje || {}).map(([eje, count]) => (
                  <div key={eje} className="flex justify-between text-xs">
                    <span
                      className="flex items-center gap-1.5"
                      style={{ color: ejeColorMap[eje] }}
                    >
                      <span
                        className="w-2 h-2 rounded-full"
                        style={{ backgroundColor: ejeColorMap[eje] }}
                      />
                      {formatEje(eje)}
                    </span>
                    <span className="text-text-secondary">{count}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </Panel>

        {/* Legend panel */}
        <Panel position="top-right" className="!m-4">
          <div className="bg-surface/95 backdrop-blur border border-border rounded-lg p-3">
            <h4 className="text-xs font-semibold mb-2 text-text-secondary">
              Atom Types
            </h4>
            <div className="space-y-1 text-xs">
              <div className="flex items-center gap-2">
                <span className="w-4 text-center font-semibold text-accent">C</span>
                <span className="text-text-secondary">Concepto</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-4 text-center font-semibold text-accent">P</span>
                <span className="text-text-secondary">Procedimiento</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-4 text-center font-semibold text-accent">A</span>
                <span className="text-text-secondary">Aplicación</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-4 text-center font-semibold text-accent">R</span>
                <span className="text-text-secondary">Razonamiento</span>
              </div>
            </div>
          </div>
        </Panel>
      </ReactFlow>
    </div>
  );
}
