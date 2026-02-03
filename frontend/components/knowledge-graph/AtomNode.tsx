"use client";

import { memo } from "react";
import { Handle, Position, type NodeProps } from "reactflow";
import { cn } from "@/lib/utils";

interface AtomNodeData {
  label: string;
  eje: string;
  tipo: string;
}

/**
 * Custom node component for atoms in the knowledge graph.
 * Color-coded by eje (axis/topic area).
 */
function AtomNodeComponent({ data, selected }: NodeProps<AtomNodeData>) {
  const ejeColors: Record<string, { bg: string; border: string; text: string }> = {
    numeros: {
      bg: "bg-blue-500/20",
      border: "border-blue-500/50",
      text: "text-blue-400",
    },
    algebra_y_funciones: {
      bg: "bg-purple-500/20",
      border: "border-purple-500/50",
      text: "text-purple-400",
    },
    geometria: {
      bg: "bg-green-500/20",
      border: "border-green-500/50",
      text: "text-green-400",
    },
    probabilidad_y_estadistica: {
      bg: "bg-orange-500/20",
      border: "border-orange-500/50",
      text: "text-orange-400",
    },
  };

  const colors = ejeColors[data.eje] || {
    bg: "bg-gray-500/20",
    border: "border-gray-500/50",
    text: "text-gray-400",
  };

  const tipoLabels: Record<string, string> = {
    concepto: "C",
    procedimiento: "P",
    aplicacion: "A",
    razonamiento: "R",
  };

  return (
    <>
      {/* Input handle (top) for prerequisite edges */}
      <Handle
        type="target"
        position={Position.Top}
        className="!w-2 !h-2 !bg-border !border-0"
      />

      <div
        className={cn(
          "px-3 py-2 rounded-lg border min-w-[140px] max-w-[200px]",
          "transition-all duration-150",
          colors.bg,
          colors.border,
          selected && "ring-2 ring-accent ring-offset-2 ring-offset-background"
        )}
      >
        {/* Type badge */}
        <div className="flex items-center justify-between mb-1">
          <span
            className={cn(
              "text-[10px] font-semibold px-1.5 py-0.5 rounded",
              colors.text,
              colors.bg
            )}
          >
            {tipoLabels[data.tipo] || data.tipo?.charAt(0).toUpperCase()}
          </span>
        </div>

        {/* Label */}
        <p className="text-xs text-text-primary leading-tight line-clamp-2">
          {data.label}
        </p>
      </div>

      {/* Output handle (bottom) for dependent edges */}
      <Handle
        type="source"
        position={Position.Bottom}
        className="!w-2 !h-2 !bg-border !border-0"
      />
    </>
  );
}

export const AtomNode = memo(AtomNodeComponent);
